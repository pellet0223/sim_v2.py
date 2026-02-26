import tkinter as tk
from tkinter import ttk, scrolledtext
import random
import math

# --- ユーティリティ関数 ---
def roll_dice(sides): return random.randint(1, sides)
def roll_1d100(): return random.randint(1, 100)

class Unit:
    def __init__(self, name, size_name, category, morale, agility, armor, hp, hit_fail, atk_gen, atk_spec, atk_reck, traits):
        self.name = name
        self.category = category
        self.initial_size = {"大隊": 600, "中隊": 100, "小隊": 20, "個人": 1}[size_name]
        self.agility, self.armor, self.max_hp = agility, armor, hp
        self.hit_fail_rate = hit_fail
        self.traits = traits
        self.personnel_hp = [hp] * self.initial_size
        self.personnel_status = [0] * self.initial_size # 0:生存, 1:気絶1T, 2:気絶2T, -1:死亡
        self.morale = morale
        self.is_routed = False
        self.atk_dice = {"通常攻撃": atk_gen, "特殊攻撃": atk_spec, "無謀な攻撃": atk_reck}
        self.turn_deaths = 0

    def is_alive(self):
        if self.morale == "/": return any(s != -1 for s in self.personnel_status)
        return not self.is_routed and any(s != -1 for s in self.personnel_status)

    def get_active_count(self): return sum(1 for s in self.personnel_status if s == 0)
    def get_faint_count(self): return sum(1 for s in self.personnel_status if s in (1, 2))
    def get_dead_count(self): return sum(1 for s in self.personnel_status if s == -1)

    def take_damage(self, raw_damage):
        if not self.is_alive(): return False
        
        # 失敗判定: 1D100ロールしその数値以上が出れば失敗
        if roll_1d100() >= self.hit_fail_rate: return False 

        actual_dmg = min(max(0, raw_damage - self.armor), self.max_hp)
        targets = [i for i, s in enumerate(self.personnel_status) if s >= 0]
        if not targets: return False
        idx = random.choice(targets)
        
        old_hp = self.personnel_hp[idx]
        self.personnel_hp[idx] -= actual_dmg
        
        # 最初に0に到達する時のみ1で耐える
        if old_hp > 0 and self.personnel_hp[idx] <= 0: self.personnel_hp[idx] = 1
        
        # HP半分以下で気絶、0で死亡
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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("戦術シミュレーター (GitHubクラウド版)")
        self.root.geometry("950x700")
        self.root.configure(bg="#2b2b2b")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#2b2b2b")
        self.style.configure("TLabel", background="#2b2b2b", foreground="white")
        self.style.configure("TButton", font=("Meiryo", 10, "bold"))

        # ★ ここに部隊データをどんどん追加できます ★
        self.presets = {
            "第13革命パルチザン": ["大隊", "最前衛部隊", 200, 0, 0, 10, 60, "1D2", "1D2", "1D5", ["革命万歳"]],
            "第22歩兵大隊": ["大隊", "最前衛部隊", 100, 20, 0, 10, 30, "1D2", "1D2", "1D3", ["皇帝陛下万歳"]]
        }
        
        self.setup_ui()

    def setup_ui(self):
        select_frame = ttk.Frame(self.root, padding=10)
        select_frame.pack(fill="x")

        ttk.Label(select_frame, text="攻撃側:").grid(row=0, column=0, padx=5)
        self.combo_a = ttk.Combobox(select_frame, values=list(self.presets.keys()), state="readonly")
        self.combo_a.set(list(self.presets.keys())[0])
        self.combo_a.grid(row=0, column=1, padx=5)

        ttk.Label(select_frame, text="防衛側:").grid(row=0, column=2, padx=5)
        self.combo_b = ttk.Combobox(select_frame, values=list(self.presets.keys()), state="readonly")
        self.combo_b.set(list(self.presets.keys())[1])
        self.combo_b.grid(row=0, column=3, padx=5)

        self.log_area = scrolledtext.ScrolledText(self.root, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, padx=10, pady=5)

        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="戦闘開始 / リセット", command=self.start_battle).pack(side="left", padx=5)
        self.next_btn = ttk.Button(btn_frame, text="ターンを進める", command=self.run_turn, state="disabled")
        self.next_btn.pack(side="left", padx=5)

    def start_battle(self):
        p_a = self.presets[self.combo_a.get()]
        p_b = self.presets[self.combo_b.get()]
        self.unit_a = Unit(self.combo_a.get(), *p_a)
        self.unit_b = Unit(self.combo_b.get(), *p_b)
        self.turn = 1
        self.log_area.delete(1.0, tk.END)
        self.log_area.insert(tk.END, f">>> 戦闘開始: {self.unit_a.name} VS {self.unit_b.name}\n")
        self.next_btn.state(['!disabled'])

    def run_turn(self):
        self.log_area.insert(tk.END, f"\n--- TURN {self.turn} ---\n")
        
        for side in ["A", "B"]:
            atk, dfn = (self.unit_a, self.unit_b) if side == "A" else (self.unit_b, self.unit_a)
            if not atk.is_alive(): continue
            
            roll = roll_dice(6)
            atk_type = "通常攻撃" if 2<=roll<=5 else ("特殊攻撃" if roll==1 else "無謀な攻撃")
            d_num, d_side = map(int, atk.atk_dice[atk_type].split('D'))
            
            hits = 0
            dfn.turn_deaths = 0
            for _ in range(atk.get_active_count()):
                dmg = sum(roll_dice(d_side) for _ in range(d_num))
                if atk_type == "無謀な攻撃":
                    r = 0.4 if "革命万歳" in atk.traits else 0.3
                    if dfn.take_damage(dmg - math.floor(dmg*r)): hits += 1
                    atk.take_damage(math.floor(dmg*r))
                else:
                    if dfn.take_damage(dmg): hits += 1
            
            self.log_area.insert(tk.END, f"[{atk.name}] {atk_type}(出目:{roll}) | 命中:{hits} | 敵損害:{dfn.turn_deaths}\n")

        for u in [self.unit_a, self.unit_b]:
            for i in range(u.initial_size):
                if u.personnel_status[i] == 1: u.personnel_status[i] = 2
                elif u.personnel_status[i] == 2: u.personnel_status[i] = -1

        status_a = "敗走" if self.unit_a.is_routed else ("全滅" if self.unit_a.get_dead_count()>=self.unit_a.initial_size else "戦闘中")
        status_b = "敗走" if self.unit_b.is_routed else ("全滅" if self.unit_b.get_dead_count()>=self.unit_b.initial_size else "戦闘中")

        self.log_area.insert(tk.END, f"STATUS: {self.unit_a.name}(生存{self.unit_a.get_active_count()}/{status_a}) VS {self.unit_b.name}(生存{self.unit_b.get_active_count()}/{status_b})\n")
        self.log_area.see(tk.END)
        self.turn += 1
        
        if not (self.unit_a.is_alive() and self.unit_b.is_alive()):
            self.log_area.insert(tk.END, "\n*** 戦闘終了 ***\n")
            self.next_btn.state(['disabled'])

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
