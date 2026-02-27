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
    "後方支援中隊": {"size":"中隊", "cat":"後援部隊", "morale":80, "agi":10, "arm":1, "hp":15, "fail":40, "gen":"1D3", "spc":"1D4", "reck":"1D6", "traits":[]},
    "特殊暗殺小隊": {"size":"小隊", "cat":"特殊部隊", "morale":150, "agi":50, "arm":0, "hp":20, "fail":10, "gen":"2D6", "spc":"3D6", "reck":"1D10", "traits":[]}
}

FLAVOR_TEXTS = {
    "通常攻撃": ["が陣形を維持し、組織的な一斉射撃を放った！", "が標準的な戦術で敵陣に迫る！", "が前線を押し上げ、猛烈な弾幕を展開した！"],
    "特殊攻撃": ["が戦場の死角を突き、非情な奇襲攻撃を仕掛けた！", "が特殊装備を展開し、予測不能な殲滅戦術を実行！", "の精鋭部隊が敵の防衛線を鮮やかに突破！"],
    "無謀な攻撃": ["が被害を度外視した狂気の特攻を敢行！！", "が血走った眼で敵陣へ玉砕覚悟の突撃を仕掛ける！！", "が死の恐怖を忘れ、捨て身の肉弾戦に突入！！"]
}

# --- クラス定義 ---
class Unit:
    def __init__(self, name, preset, team):
        self.name = f"{team}: {name}"
        self.base_name = name
        self.team = team
        self.category = preset["cat"]
        self.initial_size = {"大隊": 600, "中隊": 100, "小隊": 20, "個人": 1}[preset["size"]]
        self.morale = preset["morale"]
        self.start_morale = preset["morale"]
        self.agility, self.armor, self.max_hp = preset["agi"], preset["arm"], preset["hp"]
        self.hit_fail_rate = preset["fail"]
        self.atk_dice = {"通常攻撃": preset["gen"], "特殊攻撃": preset["spc"], "無謀な攻撃": preset["reck"]}
        self.traits = preset["traits"]
        
        self.personnel_hp = [self.max_hp] * self.initial_size
        self.personnel_status = [0] * self.initial_size # 0:生存, 1:気絶1T, 2:気絶2T, -1:死亡
        self.is_routed = False
        self.just_routed = False # ログ出力用フラグ
        self.turn_deaths = 0

    def is_alive(self):
        if self.morale == "/": return any(s != -1 for s in self.personnel_status)
        return not self.is_routed and any(s != -1 for s in self.personnel_status)

    def get_active_count(self): return sum(1 for s in self.personnel_status if s == 0)
    def get_faint_count(self): return sum(1 for s in self.personnel_status if s in (1, 2))
    def get_dead_count(self): return sum(1 for s in self.personnel_status if s == -1)

    def take_damage(self, raw_damage):
        if not self.is_alive(): return False
        if roll_1d100() <= self.hit_fail_rate: return False 
        
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
            
            # 士気減少と敗走処理の厳密化
            if self.morale != "/" and not self.is_routed:
                threshold = 49 if "皇帝陛下万歳" in self.traits else 45
                if roll_1d100() <= threshold:
                    self.morale -= 1
                    if self.morale <= 0:
                        self.is_routed = True
                        self.just_routed = True
                        # 敗走時：気絶者は全員死亡状態へ移行
                        for i in range(self.initial_size):
                            if self.personnel_status[i] in (1, 2):
                                self.personnel_status[i] = -1
        return True

# --- UIアプリケーション ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("【TACTICAL COMMAND DUAL】 モダンUI版")
        self.root.geometry("1200x800")
        self.root.configure(bg="#0d1117") # GitHub風ダークモダン
        
        # テーマ設定
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#0d1117")
        self.style.configure("TLabel", background="#0d1117", foreground="#c9d1d9", font=("Meiryo", 10))
        self.style.configure("TButton", font=("Meiryo", 10, "bold"), background="#238636", foreground="white", borderwidth=0)
        self.style.map("TButton", background=[('active', '#2ea043')])
        self.style.configure("Header.TLabel", font=("Meiryo", 12, "bold"), foreground="#58a6ff")
        
        # Treeviewのモダン化
        self.style.configure("Treeview", background="#161b22", fieldbackground="#161b22", foreground="#c9d1d9", borderwidth=0, font=("Meiryo", 9))
        self.style.configure("Treeview.Heading", background="#21262d", foreground="#c9d1d9", font=("Meiryo", 9, "bold"))
        self.style.map('Treeview', background=[('selected', '#1f6feb')])

        self.teams = {"A": [], "B": []}
        self.turn = 1
        self.is_battling = False
        self.create_widgets()

    def create_widgets(self):
        # メインコンテナ
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#30363d", sashwidth=2)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # --- 上部パネル（編成＆リスト＆詳細） ---
        top_frame = ttk.Frame(main_pane)
        main_pane.add(top_frame, minsize=350)
        
        # 左側：編成＆リスト
        roster_frame = ttk.Frame(top_frame)
        roster_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 編成コントロール
        ctrl_frame = ttk.Frame(roster_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        self.combo_unit = ttk.Combobox(ctrl_frame, values=list(PRESETS.keys()), state="readonly", width=20)
        self.combo_unit.set(list(PRESETS.keys())[0])
        self.combo_unit.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(ctrl_frame, text="配備数:").pack(side=tk.LEFT)
        self.spin_count = ttk.Spinbox(ctrl_frame, from_=1, to=10, width=3)
        self.spin_count.set(1)
        self.spin_count.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(ctrl_frame, text="◀ 攻撃(A)", command=lambda: self.add_units("A")).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="防衛(B) ▶", command=lambda: self.add_units("B")).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="リセット", command=self.reset_roster).pack(side=tk.LEFT, padx=15)

        # リスト表示エリア
        list_frame = ttk.Frame(roster_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        cols = ("Name", "Alive", "Morale", "Agi")
        self.tree_a = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        self.tree_b = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        
        for tree in (self.tree_a, self.tree_b):
            tree.heading("Name", text="部隊名")
            tree.heading("Alive", text="生存(気絶)")
            tree.heading("Morale", text="士気")
            tree.heading("Agi", text="機動")
            tree.column("Name", width=140)
            tree.column("Alive", width=80, anchor="center")
            tree.column("Morale", width=80, anchor="center")
            tree.column("Agi", width=50, anchor="center")
            tree.bind('<<TreeviewSelect>>', self.show_unit_details)

        self.tree_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        self.tree_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)

        # 右側：詳細ステータスパネル
        detail_frame = ttk.Frame(top_frame, width=250)
        detail_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        detail_frame.pack_propagate(False) # 幅固定
        
        ttk.Label(detail_frame, text="◆ ユニット詳細解析 ◆", style="Header.TLabel").pack(pady=5)
        self.lbl_details = tk.Label(detail_frame, text="部隊を選択してください\n...", bg="#161b22", fg="#8b949e", font=("Meiryo", 10), justify=tk.LEFT, anchor="nw", padx=10, pady=10)
        self.lbl_details.pack(fill=tk.BOTH, expand=True)

        # --- 下部パネル（アクション＆ログ） ---
        bottom_frame = ttk.Frame(main_pane)
        main_pane.add(bottom_frame, minsize=350)
        
        act_frame = ttk.Frame(bottom_frame)
        act_frame.pack(fill=tk.X, pady=5)
        
        self.btn_start = ttk.Button(act_frame, text="▶ 戦闘開始", command=self.start_battle)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_next = ttk.Button(act_frame, text="⏭ 次のターン", command=self.run_turn, state="disabled")
        self.btn_next.pack(side=tk.LEFT, padx=5)
        self.btn_auto = ttk.Button(act_frame, text="⏩ 決着まで自動化", command=self.run_auto, state="disabled")
        self.btn_auto.pack(side=tk.LEFT, padx=5)
        
        # ログエリア（リッチテキスト化）
        self.log_area = scrolledtext.ScrolledText(bottom_frame, bg="#0d1117", font=("Meiryo", 10), spacing1=2, spacing3=2)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ログの色設定
        self.log_area.tag_config("sys", foreground="#8b949e")
        self.log_area.tag_config("turn", foreground="#58a6ff", font=("Meiryo", 11, "bold"))
        self.log_area.tag_config("atk_normal", foreground="#d2a8ff")
        self.log_area.tag_config("atk_special", foreground="#79c0ff", font=("Meiryo", 10, "bold"))
        self.log_area.tag_config("atk_reckless", foreground="#ff7b72", font=("Meiryo", 10, "bold"))
        self.log_area.tag_config("dmg", foreground="#ffa657")
        self.log_area.tag_config("route", foreground="#ff7b72", font=("Meiryo", 12, "bold"), background="#490202")
        self.log_area.tag_config("win", foreground="#3fb950", font=("Meiryo", 14, "bold"))

        self.log_msg("SYSTEM: ダッシュボード起動完了。部隊を配備してください。", "sys")

    def log_msg(self, text, tag=None):
        self.log_area.insert(tk.END, text + "\n", tag)
        self.log_area.see(tk.END)

    def add_units(self, team):
        if self.is_battling:
            messagebox.showwarning("エラー", "戦闘中は増援できません！")
            return
        unit_key = self.combo_unit.get()
        for _ in range(int(self.spin_count.get())):
            self.teams[team].append(Unit(unit_key, PRESETS[unit_key], team))
        self.update_trees()

    def reset_roster(self):
        self.teams = {"A": [], "B": []}
        self.is_battling = False
        self.turn = 1
        self.update_trees()
        self.log_area.delete(1.0, tk.END)
        self.log_msg("SYSTEM: 配備をクリアしました。", "sys")
        self.btn_start.state(['!disabled'])
        self.btn_next.state(['disabled'])
        self.btn_auto.state(['disabled'])
        self.lbl_details.config(text="部隊を選択してください\n...")

    def update_trees(self):
        for tree in [self.tree_a, self.tree_b]:
            for row in tree.get_children(): tree.delete(row)
            
        for team_key, tree in [("A", self.tree_a), ("B", self.tree_b)]:
            for i, u in enumerate(self.teams[team_key]):
                st = "敗走" if u.is_routed else ("全滅" if u.get_dead_count() >= u.initial_size else "戦闘中")
                morale_txt = f"{u.morale}" if u.morale != "/" else "無限"
                alive_txt = f"{u.get_active_count()} ({u.get_faint_count()})"
                # 行にIDを付与して後で参照できるようにする
                tree.insert("", tk.END, iid=f"{team_key}_{i}", values=(u.base_name, alive_txt, f"{morale_txt}/{st}", u.agility))

    def show_unit_details(self, event):
        tree = event.widget
        selection = tree.selection()
        if not selection: return
        
        item_id = selection[0]
        team_key, idx = item_id.split("_")
        u = self.teams[team_key][int(idx)]
        
        traits_str = ", ".join(u.traits) if u.traits else "なし"
        morale_str = "無限 (全滅まで抗戦)" if u.morale == "/" else f"{u.morale} / {u.start_morale}"
        
        details = f"""【部隊名】 {u.base_name}
【所属軍】 {u.team}軍
【カテゴリー】 {u.category}

=== ステータス ===
機動力　: {u.agility}
装甲　　: {u.armor}
各員最大HP: {u.max_hp}
命中失敗率: {u.hit_fail_rate}%
士気　　: {morale_str}

=== 人員状況 (計{u.initial_size}名) ===
行動可能: {u.get_active_count()} 名
気絶状態: {u.get_faint_count()} 名
死亡者　: {u.get_dead_count()} 名

=== 攻撃ダイス ===
通常攻撃: {u.atk_dice['通常攻撃']}
特殊攻撃: {u.atk_dice['特殊攻撃']}
無謀攻撃: {u.atk_dice['無謀な攻撃']}

=== 特性 ===
{traits_str}
"""
        self.lbl_details.config(text=details, fg="#58a6ff")

    def get_target(self, attacker, enemy_team):
        r = roll_1d100()
        cat = "特殊部隊" if r==1 else ("最後衛部隊" if r==2 else ("後援部隊" if 3<=r<=13 else "最前衛部隊"))
        
        enemies = [u for u in self.teams[enemy_team] if u.is_alive()]
        if not enemies: return None
        if cat == "最後衛部隊" and any(u.category == "最前衛部隊" for u in enemies):
            return self.get_target(attacker, enemy_team)
            
        possible = [u for u in enemies if u.category == cat]
        if not possible: return random.choice(enemies)
        
        possible.sort(key=lambda x: x.agility)
        return random.choice([u for u in possible if u.agility == possible[0].agility])

    def start_battle(self):
        if not self.teams["A"] or not self.teams["B"]:
            messagebox.showerror("エラー", "両軍に部隊を配備せよ！")
            return
        self.is_battling = True
        self.turn = 1
        self.btn_start.state(['disabled'])
        self.btn_next.state(['!disabled'])
        self.btn_auto.state(['!disabled'])
        self.log_msg("\n=======================================", "sys")
        self.log_msg("      🚨 MISSION START 🚨", "win")
        self.log_msg("=======================================", "sys")

    def run_turn(self):
        self.log_msg(f"\n▼ TURN {self.turn} 開始 ▼", "turn")
        
        for cat in ["特殊部隊", "最後衛部隊", "最前衛部隊", "後援部隊"]:
            for side in ["A", "B"]:
                enemy_side = "B" if side == "A" else "A"
                
                for atk_unit in self.teams[side]:
                    if atk_unit.category == cat and atk_unit.is_alive():
                        target = self.get_target(atk_unit, enemy_side)
                        if not target: continue
                        
                        roll = roll_dice(6)
                        atk_type = "通常攻撃" if 2<=roll<=5 else ("特殊攻撃" if roll==1 else "無謀な攻撃")
                        tag_color = {"通常攻撃": "atk_normal", "特殊攻撃": "atk_special", "無謀な攻撃": "atk_reckless"}[atk_type]
                        flavor = random.choice(FLAVOR_TEXTS[atk_type])
                        
                        self.log_msg(f"[{atk_unit.name}] {flavor}", tag_color)
                        
                        d_num, d_side = map(int, atk_unit.atk_dice[atk_type].split('D'))
                        hits = 0
                        target.turn_deaths = 0
                        atk_unit.turn_deaths = 0
                        active_men = atk_unit.get_active_count()
                        
                        for _ in range(active_men):
                            dmg = sum(roll_dice(d_side) for _ in range(d_num))
                            if atk_type == "無謀な攻撃":
                                r = 0.4 if "革命万歳" in atk_unit.traits else 0.3
                                if target.take_damage(dmg - math.floor(dmg*r)): hits += 1
                                atk_unit.take_damage(math.floor(dmg*r))
                            else:
                                if target.take_damage(dmg): hits += 1
                                
                        result_msg = f"  └ 標的: [{target.name}] | 有効打: {hits}/{active_men}発 | 敵死傷: {target.turn_deaths}名"
                        if atk_type == "無謀な攻撃":
                            result_msg += f" | 自軍犠牲: {atk_unit.turn_deaths}名"
                        self.log_msg(result_msg, "dmg")

                        # 敗走チェック
                        if target.just_routed:
                            self.log_msg(f"  ⚠️ 【部隊崩壊】[{target.name}] は戦意を喪失し、戦線から敗走した！！", "route")
                            target.just_routed = False
                        if atk_unit.just_routed:
                            self.log_msg(f"  ⚠️ 【部隊崩壊】[{atk_unit.name}] は自滅による戦意喪失で敗走した！！", "route")
                            atk_unit.just_routed = False

        # ターン終了時の気絶進行
        for side in self.teams.values():
            for u in side:
                for i in range(u.initial_size):
                    if u.personnel_status[i] == 1: u.personnel_status[i] = 2
                    elif u.personnel_status[i] == 2: u.personnel_status[i] = -1

        self.update_trees()
        self.turn += 1
        
        a_alive = any(u.is_alive() for u in self.teams["A"])
        b_alive = any(u.is_alive() for u in self.teams["B"])
        
        if not (a_alive and b_alive):
            winner = "攻撃軍(A)" if a_alive else "防衛軍(B)"
            if not a_alive and not b_alive: winner = "引き分け（両軍全滅）"
            self.log_msg("\n=======================================", "sys")
            self.log_msg(f"  🎖️ 戦闘終了！ 勝者: {winner}", "win")
            self.log_msg("=======================================", "sys")
            self.btn_next.state(['disabled'])
            self.btn_auto.state(['disabled'])
            return False
        return True

    def run_auto(self):
        while self.run_turn(): pass

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
