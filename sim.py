import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import random
import math

# --- ユーティリティ・データ ---
def roll_dice(sides): return random.randint(1, sides)
def roll_1d100(): return random.randint(1, 100)

PRESETS = {
    "第13革命パルチザン大隊": {"size":"大隊", "cat":"最前衛部隊", "morale":200, "agi":0, "arm":0, "hp":10, "fail":60, "gen":"1D2", "spc":"1D2", "reck":"1D5", "traits":["革命万歳"]},
    "第22歩兵大隊": {"size":"大隊", "cat":"最前衛部隊", "morale":100, "agi":20, "arm":0, "hp":10, "fail":30, "gen":"1D2", "spc":"1D2", "reck":"1D3", "traits":["皇帝陛下万歳"]},
    "後方支援部隊(テスト)": {"size":"中隊", "cat":"後援部隊", "morale":80, "agi":10, "arm":1, "hp":15, "fail":40, "gen":"1D3", "spc":"1D4", "reck":"1D6", "traits":[]},
    "特殊暗殺部隊(テスト)": {"size":"小隊", "cat":"特殊部隊", "morale":150, "agi":50, "arm":0, "hp":20, "fail":10, "gen":"2D6", "spc":"3D6", "reck":"1D10", "traits":[]}
}

# --- クラス定義 ---
class Unit:
    def __init__(self, name, preset, team):
        self.name = f"{team}軍: {name}"
        self.base_name = name
        self.team = team
        self.category = preset["cat"]
        self.initial_size = {"大隊": 600, "中隊": 100, "小隊": 20, "個人": 1}[preset["size"]]
        self.morale = preset["morale"]
        self.agility, self.armor, self.max_hp = preset["agi"], preset["arm"], preset["hp"]
        self.hit_fail_rate = preset["fail"]
        self.atk_dice = {"通常攻撃": preset["gen"], "特殊攻撃": preset["spc"], "無謀な攻撃": preset["reck"]}
        self.traits = preset["traits"]
        
        self.personnel_hp = [self.max_hp] * self.initial_size
        self.personnel_status = [0] * self.initial_size # 0:生存, 1:気絶1T, 2:気絶2T, -1:死亡
        self.is_routed = False
        self.turn_deaths = 0

    def is_alive(self):
        if self.morale == "/": return any(s != -1 for s in self.personnel_status)
        return not self.is_routed and any(s != -1 for s in self.personnel_status)

    def get_active_count(self): return sum(1 for s in self.personnel_status if s == 0)
    def get_dead_count(self): return sum(1 for s in self.personnel_status if s == -1)

    def take_damage(self, raw_damage):
        if not self.is_alive(): return False
        if roll_1d100() >= self.hit_fail_rate: return False 
        actual_dmg = min(max(0, raw_damage - self.armor), self.max_hp)
        targets = [i for i, s in enumerate(self.personnel_status) if s >= 0]
        if not targets: return False
        
        idx = random.choice(targets)
        old_hp = self.personnel_hp[idx]
        self.personnel_hp[idx] -= actual_dmg
        
        if old_hp > 0 and self.personnel_hp[idx] <= 0: self.personnel_hp[idx] = 1
        if self.personnel_hp[idx] <= self.max_hp / 2 and self.personnel_status[idx] == 0:
            self.personnel_status[idx] = 1
        elif self.personnel_hp[idx] <= 0:
            self.personnel_status[idx] = -1
            self.turn_deaths += 1
            if self.morale != "/":
                threshold = 49 if "皇帝陛下万歳" in self.traits else 45
                if roll_1d100() <= threshold:
                    self.morale -= 1
                    if self.morale <= 0: self.is_routed = True
        return True

# --- UIアプリケーション ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("【TACTICAL COMMAND DUAL】 本格戦術シミュレーター")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e2e")
        
        # UIテーマ設定
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#1e1e2e")
        self.style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Meiryo", 10))
        self.style.configure("TButton", font=("Meiryo", 10, "bold"), background="#89b4fa", foreground="#11111b")
        self.style.configure("Header.TLabel", font=("Meiryo", 14, "bold"), foreground="#f38ba8")
        
        self.teams = {"攻撃(A)": [], "防衛(B)": []}
        self.turn = 1
        self.is_battling = False
        
        self.create_widgets()

    def create_widgets(self):
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#1e1e2e", sashwidth=5)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === 上部：部隊編成パネル ===
        setup_frame = ttk.Frame(main_pane)
        main_pane.add(setup_frame, minsize=250)
        
        # 編成コントロール
        ctrl_frame = ttk.Frame(setup_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(ctrl_frame, text="▼ 部隊を配備 ▼", style="Header.TLabel").pack(side=tk.TOP, pady=5)
        
        input_frame = ttk.Frame(ctrl_frame)
        input_frame.pack(side=tk.TOP)
        
        self.combo_unit = ttk.Combobox(input_frame, values=list(PRESETS.keys()), state="readonly", width=25)
        self.combo_unit.set(list(PRESETS.keys())[0])
        self.combo_unit.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(input_frame, text="配備数:").pack(side=tk.LEFT)
        self.spin_count = ttk.Spinbox(input_frame, from_=1, to=10, width=5)
        self.spin_count.set(1)
        self.spin_count.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(input_frame, text="◀ 攻撃(A)に追加", command=lambda: self.add_units("攻撃(A)")).pack(side=tk.LEFT, padx=10)
        ttk.Button(input_frame, text="防衛(B)に追加 ▶", command=lambda: self.add_units("防衛(B)")).pack(side=tk.LEFT, padx=10)
        ttk.Button(input_frame, text="リセット", command=self.reset_roster).pack(side=tk.LEFT, padx=20)

        # リスト表示エリア
        list_frame = ttk.Frame(setup_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # A軍リスト
        self.tree_a = ttk.Treeview(list_frame, columns=("Type", "Size", "Morale"), show="headings", height=6)
        self.tree_a.heading("Type", text="攻撃側(A) 部隊名")
        self.tree_a.heading("Size", text="生存")
        self.tree_a.heading("Morale", text="士気/状態")
        self.tree_a.column("Size", width=80, anchor="center")
        self.tree_a.column("Morale", width=120, anchor="center")
        self.tree_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # B軍リスト
        self.tree_b = ttk.Treeview(list_frame, columns=("Type", "Size", "Morale"), show="headings", height=6)
        self.tree_b.heading("Type", text="防衛側(B) 部隊名")
        self.tree_b.heading("Size", text="生存")
        self.tree_b.heading("Morale", text="士気/状態")
        self.tree_b.column("Size", width=80, anchor="center")
        self.tree_b.column("Morale", width=120, anchor="center")
        self.tree_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # === 下部：戦場ログパネル ===
        battle_frame = ttk.Frame(main_pane)
        main_pane.add(battle_frame, minsize=300)
        
        # アクションボタン
        act_frame = ttk.Frame(battle_frame)
        act_frame.pack(fill=tk.X, pady=5)
        
        self.btn_start = ttk.Button(act_frame, text="⚔️ 戦闘開始！", command=self.start_battle)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_next = ttk.Button(act_frame, text="⏭ 次のターン", command=self.run_turn, state="disabled")
        self.btn_next.pack(side=tk.LEFT, padx=5)

        self.btn_auto = ttk.Button(act_frame, text="⏩ 決着まで自動実行", command=self.run_auto, state="disabled")
        self.btn_auto.pack(side=tk.LEFT, padx=5)
        
        # ログ
        self.log_area = scrolledtext.ScrolledText(battle_frame, bg="#11111b", fg="#a6e3a1", font=("Consolas", 11))
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_area.insert(tk.END, "司令官、部隊を配備して「戦闘開始」を押してください。\n")

    def add_units(self, team_name):
        if self.is_battling:
            messagebox.showwarning("警告", "戦闘中は部隊を追加できません！リセットしてください。")
            return
            
        unit_key = self.combo_unit.get()
        count = int(self.spin_count.get())
        
        for _ in range(count):
            new_unit = Unit(unit_key, PRESETS[unit_key], team_name)
            self.teams[team_name].append(new_unit)
            
        self.update_trees()

    def reset_roster(self):
        self.teams = {"攻撃(A)": [], "防衛(B)": []}
        self.is_battling = False
        self.turn = 1
        self.update_trees()
        self.log_area.delete(1.0, tk.END)
        self.log_area.insert(tk.END, "--- 配備をリセットしました ---\n")
        self.btn_start.state(['!disabled'])
        self.btn_next.state(['disabled'])
        self.btn_auto.state(['disabled'])

    def update_trees(self):
        for tree in [self.tree_a, self.tree_b]:
            for row in tree.get_children(): tree.delete(row)
            
        for u in self.teams["攻撃(A)"]:
            st = "敗走" if u.is_routed else ("全滅" if u.get_dead_count() >= u.initial_size else "戦闘中")
            self.tree_a.insert("", tk.END, values=(u.name, f"{u.get_active_count()}/{u.initial_size}", f"{u.morale} ({st})"))
            
        for u in self.teams["防衛(B)"]:
            st = "敗走" if u.is_routed else ("全滅" if u.get_dead_count() >= u.initial_size else "戦闘中")
            self.tree_b.insert("", tk.END, values=(u.name, f"{u.get_active_count()}/{u.initial_size}", f"{u.morale} ({st})"))

    def get_target(self, attacker, enemy_team_name):
        r = roll_1d100()
        cat = "特殊部隊" if r==1 else ("最後衛部隊" if r==2 else ("後援部隊" if 3<=r<=13 else "最前衛部隊"))
        
        enemies = [u for u in self.teams[enemy_team_name] if u.is_alive()]
        if not enemies: return None
        
        if cat == "最後衛部隊" and any(u.category == "最前衛部隊" for u in enemies):
            return self.get_target(attacker, enemy_team_name)
            
        possible = [u for u in enemies if u.category == cat]
        if not possible: return random.choice(enemies)
        
        possible.sort(key=lambda x: x.agility)
        return random.choice([u for u in possible if u.agility == possible[0].agility])

    def start_battle(self):
        if not self.teams["攻撃(A)"] or not self.teams["防衛(B)"]:
            messagebox.showerror("エラー", "両軍に最低1つの部隊を配備してください！")
            return
            
        self.is_battling = True
        self.turn = 1
        self.btn_start.state(['disabled'])
        self.btn_next.state(['!disabled'])
        self.btn_auto.state(['!disabled'])
        self.log_area.insert(tk.END, "\n====================================\n")
        self.log_area.insert(tk.END, "      🚨 戦闘開始 🚨\n")
        self.log_area.insert(tk.END, "====================================\n")
        self.log_area.see(tk.END)

    def run_turn(self):
        self.log_area.insert(tk.END, f"\n--- ターン {self.turn} ---\n")
        
        for cat in ["特殊部隊", "最後衛部隊", "最前衛部隊", "後援部隊"]:
            for side in ["攻撃(A)", "防衛(B)"]:
                enemy_side = "防衛(B)" if side == "攻撃(A)" else "攻撃(A)"
                
                for attacker in self.teams[side]:
                    if attacker.category == cat and attacker.is_alive():
                        target = self.get_target(attacker, enemy_side)
                        if not target: continue
                        
                        roll = roll_dice(6)
                        atk_type = "通常攻撃" if 2<=roll<=5 else ("特殊攻撃" if roll==1 else "無謀な攻撃")
                        d_num, d_side = map(int, attacker.atk_dice[atk_type].split('D'))
                        
                        hits = 0
                        target.turn_deaths = 0
                        active_men = attacker.get_active_count()
                        
                        for _ in range(active_men):
                            dmg = sum(roll_dice(d_side) for _ in range(d_num))
                            if atk_type == "無謀な攻撃":
                                r = 0.4 if "革命万歳" in attacker.traits else 0.3
                                if target.take_damage(dmg - math.floor(dmg*r)): hits += 1
                                attacker.take_damage(math.floor(dmg*r))
                            else:
                                if target.take_damage(dmg): hits += 1
                                
                        self.log_area.insert(tk.END, f"[{attacker.name}] -> [{target.name}]\n")
                        self.log_area.insert(tk.END, f"  └ {atk_type} | 命中:{hits}/{active_men} | 敵損害:{target.turn_deaths}人\n")

        # 気絶進行
        for side in self.teams.values():
            for u in side:
                for i in range(u.initial_size):
                    if u.personnel_status[i] == 1: u.personnel_status[i] = 2
                    elif u.personnel_status[i] == 2: u.personnel_status[i] = -1

        self.update_trees()
        self.log_area.see(tk.END)
        self.turn += 1
        
        a_alive = any(u.is_alive() for u in self.teams["攻撃(A)"])
        b_alive = any(u.is_alive() for u in self.teams["防衛(B)"])
        
        if not (a_alive and b_alive):
            winner = "攻撃軍(A)" if a_alive else "防衛軍(B)"
            if not a_alive and not b_alive: winner = "引き分け（両軍全滅）"
            self.log_area.insert(tk.END, "\n====================================\n")
            self.log_area.insert(tk.END, f"  🎖️ 戦闘終了！ 勝者: {winner}\n")
            self.log_area.insert(tk.END, "====================================\n")
            self.log_area.see(tk.END)
            self.btn_next.state(['disabled'])
            self.btn_auto.state(['disabled'])
            return False
        return True

    def run_auto(self):
        while self.run_turn():
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
