import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import subprocess
import tempfile
import os
import shlex
import shutil
from datetime import datetime
from enum import Enum

# Script settings
DEFAULT_INJECTOR_SCRIPT = "injector.py"
DEFAULT_INJECTOR_CMD = 'python3 "{injector}" inject --sav "{sav}" --course "{course}" --slot "{slot}" --out "{out}"'

# ---------- Custom Dialog for Pokémon ----------

class PokemonDialog(tk.Toplevel):
    def __init__(self, parent, title, initial=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("340x360")
        self.result = None
        initial = initial or {}

        self.species = tk.StringVar(value=initial.get("species", POKEMON_SPECIES_LIST[0] if POKEMON_SPECIES_LIST else ""))
        self.min_lv = tk.StringVar(value=str(initial.get("min_level", 1)))
        self.max_lv = tk.StringVar(value=str(initial.get("max_level", 1)))
        self.rate = tk.StringVar(value=str(initial.get("rate", 10)))
        self.steps = tk.StringVar(value=str(initial.get("steps", 0)))
        self.held_item = tk.StringVar(value=initial.get("held_item", ""))
        self.move1 = tk.StringVar(value=initial.get("move1", ""))
        self.move2 = tk.StringVar(value=initial.get("move2", ""))
        self.move3 = tk.StringVar(value=initial.get("move3", ""))
        self.move4 = tk.StringVar(value=initial.get("move4", ""))

        frame = tk.Frame(self, padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Species:", self.species, POKEMON_SPECIES_LIST),
            ("Min Level:", self.min_lv, None),
            ("Max Level:", self.max_lv, None),
            ("Rate (%):", self.rate, None),
            ("Required Steps:", self.steps, None),
            ("Held Item (Optional):", self.held_item, ITEM_LIST),
            ("Move 1 (Optional):", self.move1, MOVE_LIST),
            ("Move 2 (Optional):", self.move2, MOVE_LIST),
            ("Move 3 (Optional):", self.move3, MOVE_LIST),
            ("Move 4 (Optional):", self.move4, MOVE_LIST),
        ]

        for i, (label_text, var, options) in enumerate(fields):
            tk.Label(frame, text=label_text).grid(row=i, column=0, sticky="e", pady=3, padx=(0, 5))
            
            if options is not None:
                cb = ttk.Combobox(frame, textvariable=var, values=options, width=18, state="readonly")
                cb.grid(row=i, column=1, sticky="w", pady=3)
            else:
                tk.Entry(frame, textvariable=var, width=21).grid(row=i, column=1, sticky="w", pady=3)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=self.on_ok, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=8).pack(side=tk.LEFT, padx=5)

        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def on_ok(self):
        try:
            self.result = {
                "species": self.species.get().strip(),
                "min_level": int(self.min_lv.get()),
                "max_level": int(self.max_lv.get()),
                "rate": int(self.rate.get()),
                "steps": int(self.steps.get()),
                "held_item": self.held_item.get().strip(),
                "move1": self.move1.get().strip(),
                "move2": self.move2.get().strip(),
                "move3": self.move3.get().strip(),
                "move4": self.move4.get().strip()
            }
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Min Level, Max Level, Rate, and Required Steps must be whole numbers.", parent=self)

# ---------- Custom Dialog for Items ----------

class ItemDialog(tk.Toplevel):
    def __init__(self, parent, title, initial=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x160")
        self.result = None
        initial = initial or {}

        default_item = ITEM_LIST[1] if len(ITEM_LIST) > 1 else (ITEM_LIST[0] if ITEM_LIST else "")
        self.name = tk.StringVar(value=initial.get("name", default_item))
        self.rate = tk.StringVar(value=str(initial.get("rate", 10)))
        self.steps = tk.StringVar(value=str(initial.get("steps", 0)))

        frame = tk.Frame(self, padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Item Name:").grid(row=0, column=0, sticky="e", pady=3, padx=(0, 5))
        cb = ttk.Combobox(frame, textvariable=self.name, values=ITEM_LIST, width=18, state="readonly")
        cb.grid(row=0, column=1, sticky="w", pady=3)

        tk.Label(frame, text="Rate (%):").grid(row=1, column=0, sticky="e", pady=3, padx=(0, 5))
        tk.Entry(frame, textvariable=self.rate, width=21).grid(row=1, column=1, sticky="w", pady=3)

        tk.Label(frame, text="Required Steps:").grid(row=2, column=0, sticky="e", pady=3, padx=(0, 5))
        tk.Entry(frame, textvariable=self.steps, width=21).grid(row=2, column=1, sticky="w", pady=3)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=self.on_ok, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=8).pack(side=tk.LEFT, padx=5)

        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def on_ok(self):
        try:
            self.result = {
                "name": self.name.get().strip(),
                "rate": int(self.rate.get()),
                "steps": int(self.steps.get())
            }
            if not self.result["name"]:
                messagebox.showerror("Invalid Input", "Please select an item.", parent=self)
                return
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Rate and Required Steps must be whole numbers.", parent=self)

# ---------- Main App ----------

class CourseEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokéwalker Course Editor")

        self.course = {
            "name": "",
            "background": "",
            "pokemon": [],
            "items": []
        }
        self.current_file = None
        self.injector_path = DEFAULT_INJECTOR_SCRIPT
        self.last_sav_path = ""

        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self.root, padx=5, pady=5)
        top.pack(fill=tk.X)

        tk.Label(top, text="Course Name:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(top, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky="w")

        tk.Label(top, text="Background:").grid(row=1, column=0, sticky="w")
        self.bg_var = tk.StringVar()
        if BACKGROUNDS:
            self.bg_var.set(BACKGROUNDS[0])
        self.bg_dropdown = tk.OptionMenu(top, self.bg_var, *BACKGROUNDS)
        self.bg_dropdown.config(width=20)
        self.bg_dropdown.grid(row=1, column=1, sticky="w")

        tk.Label(top, text="Injector:").grid(row=2, column=0, sticky="w")
        self.injector_var = tk.StringVar(value=self.injector_path)
        tk.Entry(top, textvariable=self.injector_var, width=40).grid(row=2, column=1, sticky="w")
        tk.Button(top, text="Browse", command=self.browse_injector).grid(row=2, column=2, padx=4)

        tk.Label(top, text="Target Slot:").grid(row=3, column=0, sticky="w")
        self.slot_var = tk.StringVar()
        if COURSE_SLOTS:
            self.slot_var.set(COURSE_SLOTS[0])
        self.slot_dropdown = tk.OptionMenu(top, self.slot_var, *COURSE_SLOTS)
        self.slot_dropdown.config(width=25)
        self.slot_dropdown.grid(row=3, column=1, sticky="w")

        mid = tk.Frame(self.root, padx=5, pady=5)
        mid.pack(fill=tk.BOTH, expand=True)

        poke_frame = tk.LabelFrame(mid, text="Pokémon Slots", padx=5, pady=5)
        poke_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.poke_list = tk.Listbox(poke_frame, height=12)
        self.poke_list.pack(fill=tk.BOTH, expand=True)

        poke_btns = tk.Frame(poke_frame)
        poke_btns.pack(fill=tk.X, pady=3)

        tk.Button(poke_btns, text="Add", command=self.add_pokemon).pack(side=tk.LEFT, padx=2)
        tk.Button(poke_btns, text="Edit", command=self.edit_pokemon).pack(side=tk.LEFT, padx=2)
        tk.Button(poke_btns, text="Remove", command=self.remove_pokemon).pack(side=tk.LEFT, padx=2)

        item_frame = tk.LabelFrame(mid, text="Item Slots", padx=5, pady=5)
        item_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.item_list = tk.Listbox(item_frame, height=12)
        self.item_list.pack(fill=tk.BOTH, expand=True)

        item_btns = tk.Frame(item_frame)
        item_btns.pack(fill=tk.X, pady=3)

        tk.Button(item_btns, text="Add", command=self.add_item).pack(side=tk.LEFT, padx=2)
        tk.Button(item_btns, text="Edit", command=self.edit_item).pack(side=tk.LEFT, padx=2)
        tk.Button(item_btns, text="Remove", command=self.remove_item).pack(side=tk.LEFT, padx=2)

        bottom = tk.Frame(self.root, padx=5, pady=5)
        bottom.pack(fill=tk.X)

        tk.Button(bottom, text="New", command=self.new_course).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Open...", command=self.open_course).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Save", command=self.save_course).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Save As...", command=self.save_course_as).pack(side=tk.LEFT, padx=2)

        tk.Button(bottom, text="INJECT", command=self.inject_dialog, bg="#2e8b57", fg="white").pack(side=tk.LEFT, padx=8)

        tk.Button(bottom, text="Quit", command=self.root.quit).pack(side=tk.RIGHT, padx=2)
        tk.Button(bottom, text="Help", command=self.show_help).pack(side=tk.RIGHT, padx=2)

    def show_help(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("Help Documentation")
        help_win.geometry("550x450")
        
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, width=60, height=20)
        text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        help_text = """Pokéwalker Course Editor - Help Documentation

========================================
1. Getting Started
========================================
- Use "New" to create a fresh course layout.
- Use "Open..." to load an existing JSON course file.
- "Save" and "Save As..." will store your current configuration for future use.

========================================
2. Adding Pokémon and Items
========================================
- Click "Add" under the respective panels to open the input prompt.
- Select your desired Species or Item from the dropdown menus.
- Provide the min/max levels, encounter rate, and required step threshold.
- Steps: This is the number of steps required on the Pokéwalker before this Pokémon or Item becomes available.
- Held Items & Moves: You can specify custom moves and a held item for the Pokémon using the dropdowns. Leave these blank to use the game's default configurations.

========================================
3. Injecting into a Save File
========================================
1. Select a Target Slot (0-26) from the dropdown list.
2. Click the green INJECT button.
3. You will be prompted to select your HG/SS .sav file.
4. A backup of your save will automatically be created. The injector will run, and if successful, your original .sav file will be updated immediately.

========================================
4. Troubleshooting
========================================
- If the injector fails or times out, check the error output window that pops up. Your save file will remain unharmed.
- Ensure you have Python installed and the injector script has all its necessary dependencies.
- Verify your save file is not currently open in an emulator.
"""
        
        text_area.insert(tk.INSERT, help_text)
        text_area.configure(state='disabled')

    def create_backup(self, sav_path):
        if not sav_path:
            raise ValueError("No save path provided for backup.")

        dirpath, fname = os.path.split(sav_path)
        name, ext = os.path.splitext(fname)

        backup_name = f"{name}_BACKUP{ext}"
        backup_path = os.path.join(dirpath, backup_name)

        if os.path.exists(backup_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{name}_BACKUP_{ts}{ext}"
            backup_path = os.path.join(dirpath, backup_name)

        shutil.copy2(sav_path, backup_path)
        return backup_path

    def browse_injector(self):
        path = filedialog.askopenfilename(
            title="Select injector script",
            filetypes=[("Python Scripts", "*.py"), ("Executables", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.injector_var.set(path)
            self.injector_path = path

    def inject_dialog(self):
        self.update_course_from_ui()

        injector = self.injector_var.get().strip()
        if not injector:
            messagebox.showwarning("Injector not set", "Please set the injector path first (Browse).")
            return

        sav_path = filedialog.askopenfilename(
            title="Select HG/SS .sav to inject into",
            filetypes=[("Save files", "*.sav"), ("All files", "*.*")]
        )
        if not sav_path:
            return

        try:
            backup_path = self.create_backup(sav_path)
        except Exception as e:
            resp = messagebox.askyesno(
                "Backup failed",
                f"Failed to create backup:\n{e}\n\nDo you want to continue without a backup?"
            )
            if not resp:
                return

        try:
            tmp_json_fd, tmp_json_path = tempfile.mkstemp(prefix="pw_course_", suffix=".json")
            os.close(tmp_json_fd)
            with open(tmp_json_path, "w", encoding="utf-8") as f:
                json.dump(self.course, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write temporary course file:\n{e}")
            return

        try:
            tmp_out_fd, tmp_out_path = tempfile.mkstemp(prefix="pw_out_", suffix=".sav")
            os.close(tmp_out_fd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create temp output file:\n{e}")
            os.remove(tmp_json_path)
            return

        cmd_template = DEFAULT_INJECTOR_CMD

        raw_slot_string = self.slot_var.get()
        target_slot = raw_slot_string.split("-")[0].strip()

        if not target_slot:
            target_slot = "0"

        cmd = cmd_template.format(
            injector=injector,
            sav=sav_path,
            course=tmp_json_path,
            out=tmp_out_path, 
            slot=target_slot
        )

        try:
            if os.name == "nt":
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            else:
                proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=300)

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            rc = proc.returncode

            try:
                os.remove(tmp_json_path)
            except Exception:
                pass

            if rc == 0:
                shutil.copy2(tmp_out_path, sav_path)
                
                original_name = os.path.basename(sav_path)
                backup_name = os.path.basename(backup_path)
                
                msg = f"Injection successful!\n\nReplaced original file: {original_name}\nBackup saved as: {backup_name}"
                if stdout:
                    msg += f"\n\nOutput:\n{stdout}"
                messagebox.showinfo("Success", msg)
            else:
                msg = f"Injector returned error code {rc}.\nYour original .sav file was NOT altered."
                if stderr:
                    msg += f"\n\nError output:\n{stderr}"
                if stdout:
                    msg += f"\n\nStdout:\n{stdout}"
                messagebox.showerror("Injector failed", msg)

        except subprocess.TimeoutExpired:
            try:
                os.remove(tmp_json_path)
            except Exception:
                pass
            messagebox.showerror("Timeout", "Injector timed out. Your original .sav file was not altered.")
        except FileNotFoundError:
            try:
                os.remove(tmp_json_path)
            except Exception:
                pass
            messagebox.showerror("Not found", f"Injector not found. Make sure the script is in the same folder as this program.")
        except Exception as e:
            try:
                os.remove(tmp_json_path)
            except Exception:
                pass
            messagebox.showerror("Error", f"Failed to run injector:\n{e}")
        finally:
            try:
                if os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
            except Exception:
                pass

    def new_course(self):
        if not self.confirm_discard_changes():
            return
        self.course = {
            "name": "",
            "background": "",
            "pokemon": [],
            "items": []
        }
        self.current_file = None
        self.refresh_ui()

    def open_course(self):
        if not self.confirm_discard_changes():
            return
        path = filedialog.askopenfilename(
            title="Open Course JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON:\n{e}")
            return

        self.course = {
            "name": data.get("name", ""),
            "background": data.get("background", data.get("bg", "")),
            "pokemon": data.get("pokemon", []),
            "items": data.get("items", [])
        }
        self.current_file = path
        self.refresh_ui()

    def save_course(self):
        if self.current_file is None:
            self.save_course_as()
            return
        self.update_course_from_ui()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(self.course, f, indent=2)
            messagebox.showinfo("Saved", f"Saved to {self.current_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON:\n{e}")

    def save_course_as(self):
        self.update_course_from_ui()
        path = filedialog.asksaveasfilename(
            title="Save Course JSON As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.course, f, indent=2)
            self.current_file = path
            messagebox.showinfo("Saved", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON:\n{e}")

    def confirm_discard_changes(self):
        return messagebox.askyesno("Confirm", "Discard current changes?")

    def refresh_ui(self):
        self.name_var.set(self.course.get("name", ""))
        self.bg_var.set(self.course.get("background", ""))

        self.poke_list.delete(0, tk.END)
        for p in self.course.get("pokemon", []):
            species = p.get("species", "???")
            min_lv = p.get("min_level", "?")
            max_lv = p.get("max_level", "?")
            rate = p.get("rate", "?")
            steps = p.get("steps", 0)
            item = p.get("held_item", "")
            
            display_str = f"{species} Lv{min_lv}-{max_lv} ({rate}%) - [{steps} Steps]"
            if item:
                display_str += f" [@ {item}]"
                
            self.poke_list.insert(tk.END, display_str)

        self.item_list.delete(0, tk.END)
        for it in self.course.get("items", []):
            name = it.get("name", "???")
            rate = it.get("rate", "?")
            steps = it.get("steps", 0)
            self.item_list.insert(tk.END, f"{name} ({rate}%) - [{steps} Steps]")

    def update_course_from_ui(self):
        self.course["name"] = self.name_var.get()
        self.course["background"] = self.bg_var.get()

    def add_pokemon(self):
        p = self.prompt_pokemon()
        if p:
            self.course.setdefault("pokemon", []).append(p)
            self.refresh_ui()

    def edit_pokemon(self):
        idx = self.poke_list.curselection()
        if not idx:
            return
        i = idx[0]
        current = self.course["pokemon"][i]
        p = self.prompt_pokemon(current)
        if p:
            self.course["pokemon"][i] = p
            self.refresh_ui()

    def remove_pokemon(self):
        idx = self.poke_list.curselection()
        if not idx:
            return
        i = idx[0]
        del self.course["pokemon"][i]
        self.refresh_ui()

    def prompt_pokemon(self, initial=None):
        dialog = PokemonDialog(self.root, "Edit Pokémon", initial)
        return dialog.result

    def add_item(self):
        it = self.prompt_item()
        if it:
            self.course.setdefault("items", []).append(it)
            self.refresh_ui()

    def edit_item(self):
        idx = self.item_list.curselection()
        if not idx:
            return
        i = idx[0]
        current = self.course["items"][i]
        it = self.prompt_item(current)
        if it:
            self.course["items"][i] = it
            self.refresh_ui()

    def remove_item(self):
        idx = self.item_list.curselection()
        if not idx:
            return
        i = idx[0]
        del self.course["items"][i]
        self.refresh_ui()

    def prompt_item(self, initial=None):
        dialog = ItemDialog(self.root, "Edit Item", initial)
        return dialog.result


# ==========================================
# DATA & ENUMS 
# ==========================================

class Species(Enum):
    NONE = 0
    BULBASAUR = 1
    IVYSAUR = 2
    VENUSAUR = 3
    CHARMANDER = 4
    CHARMELEON = 5
    CHARIZARD = 6
    SQUIRTLE = 7
    WARTORTLE = 8
    BLASTOISE = 9
    CATERPIE = 10
    METAPOD = 11
    BUTTERFREE = 12
    WEEDLE = 13
    KAKUNA = 14
    BEEDRILL = 15
    PIDGEY = 16
    PIDGEOTTO = 17
    PIDGEOT = 18
    RATTATA = 19
    RATICATE = 20
    SPEAROW = 21
    FEAROW = 22
    EKANS = 23
    ARBOK = 24
    PIKACHU = 25
    RAICHU = 26
    SANDSHREW = 27
    SANDSLASH = 28
    NIDORANF = 29
    NIDORINA = 30
    NIDOQUEEN = 31
    NIDORANM = 32
    NIDORINO = 33
    NIDOKING = 34
    CLEFAIRY = 35
    CLEFABLE = 36
    VULPIX = 37
    NINETALES = 38
    JIGGLYPUFF = 39
    WIGGLYTUFF = 40
    ZUBAT = 41
    GOLBAT = 42
    ODDISH = 43
    GLOOM = 44
    VILEPLUME = 45
    PARAS = 46
    PARASECT = 47
    VENONAT = 48
    VENOMOTH = 49
    DIGLETT = 50
    DUGTRIO = 51
    MEOWTH = 52
    PERSIAN = 53
    PSYDUCK = 54
    GOLDUCK = 55
    MANKEY = 56
    PRIMEAPE = 57
    GROWLITHE = 58
    ARCANINE = 59
    POLIWAG = 60
    POLIWHIRL = 61
    POLIWRATH = 62
    ABRA = 63
    KADABRA = 64
    ALAKAZAM = 65
    MACHOP = 66
    MACHOKE = 67
    MACHAMP = 68
    BELLSPROUT = 69
    WEEPINBELL = 70
    VICTREEBEL = 71
    TENTACOOL = 72
    TENTACRUEL = 73
    GEODUDE = 74
    GRAVELER = 75
    GOLEM = 76
    PONYTA = 77
    RAPIDASH = 78
    SLOWPOKE = 79
    SLOWBRO = 80
    MAGNEMITE = 81
    MAGNETON = 82
    FARFETCHD = 83
    DODUO = 84
    DODRIO = 85
    SEEL = 86
    DEWGONG = 87
    GRIMER = 88
    MUK = 89
    SHELLDER = 90
    CLOYSTER = 91
    GASTLY = 92
    HAUNTER = 93
    GENGAR = 94
    ONIX = 95
    DROWZEE = 96
    HYPNO = 97
    KRABBY = 98
    KINGLER = 99
    VOLTORB = 100
    ELECTRODE = 101
    EXEGGCUTE = 102
    EXEGGUTOR = 103
    CUBONE = 104
    MAROWAK = 105
    HITMONLEE = 106
    HITMONCHAN = 107
    LICKITUNG = 108
    KOFFING = 109
    WEEZING = 110
    RHYHORN = 111
    RHYDON = 112
    CHANSEY = 113
    TANGELA = 114
    KANGASKHAN = 115
    HORSEA = 116
    SEADRA = 117
    GOLDEEN = 118
    SEAKING = 119
    STARYU = 120
    STARMIE = 121
    MRMIME = 122
    SCYTHER = 123
    JYNX = 124
    ELECTABUZZ = 125
    MAGMAR = 126
    PINSIR = 127
    TAUROS = 128
    MAGIKARP = 129
    GYARADOS = 130
    LAPRAS = 131
    DITTO = 132
    EEVEE = 133
    VAPOREON = 134
    JOLTEON = 135
    FLAREON = 136
    PORYGON = 137
    OMANYTE = 138
    OMASTAR = 139
    KABUTO = 140
    KABUTOPS = 141
    AERODACTYL = 142
    SNORLAX = 143
    ARTICUNO = 144
    ZAPDOS = 145
    MOLTRES = 146
    DRATINI = 147
    DRAGONAIR = 148
    DRAGONITE = 149
    MEWTWO = 150
    MEW = 151
    CHIKORITA = 152
    BAYLEEF = 153
    MEGANIUM = 154
    CYNDAQUIL = 155
    QUILAVA = 156
    TYPHLOSION = 157
    TOTODILE = 158
    CROCONAW = 159
    FERALIGATR = 160
    SENTRET = 161
    FURRET = 162
    HOOTHOOT = 163
    NOCTOWL = 164
    LEDYBA = 165
    LEDIAN = 166
    SPINARAK = 167
    ARIADOS = 168
    CROBAT = 169
    CHINCHOU = 170
    LANTURN = 171
    PICHU = 172
    CLEFFA = 173
    IGGLYBUFF = 174
    TOGEPI = 175
    TOGETIC = 176
    NATU = 177
    XATU = 178
    MAREEP = 179
    FLAAFFY = 180
    AMPHAROS = 181
    BELLOSSOM = 182
    MARILL = 183
    AZUMARILL = 184
    SUDOWOODO = 185
    POLITOED = 186
    HOPPIP = 187
    SKIPLOOM = 188
    JUMPLUFF = 189
    AIPOM = 190
    SUNKERN = 191
    SUNFLORA = 192
    YANMA = 193
    WOOPER = 194
    QUAGSIRE = 195
    ESPEON = 196
    UMBREON = 197
    MURKROW = 198
    SLOWKING = 199
    MISDREAVUS = 200
    UNOWN = 201
    WOBBUFFET = 202
    GIRAFARIG = 203
    PINECO = 204
    FORRETRESS = 205
    DUNSPARCE = 206
    GLIGAR = 207
    STEELIX = 208
    SNUBBULL = 209
    GRANBULL = 210
    QWILFISH = 211
    SCIZOR = 212
    SHUCKLE = 213
    HERACROSS = 214
    SNEASEL = 215
    TEDDIURSA = 216
    URSARING = 217
    SLUGMA = 218
    MAGCARGO = 219
    SWINUB = 220
    PILOSWINE = 221
    CORSOLA = 222
    REMORAID = 223
    OCTILLERY = 224
    DELIBIRD = 225
    MANTINE = 226
    SKARMORY = 227
    HOUNDOUR = 228
    HOUNDOOM = 229
    KINGDRA = 230
    PHANPY = 231
    DONPHAN = 232
    PORYGON2 = 233
    STANTLER = 234
    SMEARGLE = 235
    TYROGUE = 236
    HITMONTOP = 237
    SMOOCHUM = 238
    ELEKID = 239
    MAGBY = 240
    MILTANK = 241
    BLISSEY = 242
    RAIKOU = 243
    ENTEI = 244
    SUICUNE = 245
    LARVITAR = 246
    PUPITAR = 247
    TYRANITAR = 248
    LUGIA = 249
    HOOH = 250
    CELEBI = 251
    TREECKO = 252
    GROVYLE = 253
    SCEPTILE = 254
    TORCHIC = 255
    COMBUSKEN = 256
    BLAZIKEN = 257
    MUDKIP = 258
    MARSHTOMP = 259
    SWAMPERT = 260
    POOCHYENA = 261
    MIGHTYENA = 262
    ZIGZAGOON = 263
    LINOONE = 264
    WURMPLE = 265
    SILCOON = 266
    BEAUTIFLY = 267
    CASCOON = 268
    DUSTOX = 269
    LOTAD = 270
    LOMBRE = 271
    LUDICOLO = 272
    SEEDOT = 273
    NUZLEAF = 274
    SHIFTRY = 275
    TAILLOW = 276
    SWELLOW = 277
    WINGULL = 278
    PELIPPER = 279
    RALTS = 280
    KIRLIA = 281
    GARDEVOIR = 282
    SURSKIT = 283
    MASQUERAIN = 284
    SHROOMISH = 285
    BRELOOM = 286
    SLAKOTH = 287
    VIGOROTH = 288
    SLAKING = 289
    NINCADA = 290
    NINJASK = 291
    SHEDINJA = 292
    WHISMUR = 293
    LOUDRED = 294
    EXPLOUD = 295
    MAKUHITA = 296
    HARIYAMA = 297
    AZURILL = 298
    NOSEPASS = 299
    SKITTY = 300
    DELCATTY = 301
    SABLEYE = 302
    MAWILE = 303
    ARON = 304
    LAIRON = 305
    AGGRON = 306
    MEDITITE = 307
    MEDICHAM = 308
    ELECTRIKE = 309
    MANECTRIC = 310
    PLUSLE = 311
    MINUN = 312
    VOLBEAT = 313
    ILLUMISE = 314
    ROSELIA = 315
    GULPIN = 316
    SWALOT = 317
    CARVANHA = 318
    SHARPEDO = 319
    WAILMER = 320
    WAILORD = 321
    NUMEL = 322
    CAMERUPT = 323
    TORKOAL = 324
    SPOINK = 325
    GRUMPIG = 326
    SPINDA = 327
    TRAPINCH = 328
    VIBRAVA = 329
    FLYGON = 330
    CACNEA = 331
    CACTURNE = 332
    SWABLU = 333
    ALTARIA = 334
    ZANGOOSE = 335
    SEVIPER = 336
    LUNATONE = 337
    SOLROCK = 338
    BARBOACH = 339
    WHISCASH = 340
    CORPHISH = 341
    CRAWDAUNT = 342
    BALTOY = 343
    CLAYDOL = 344
    LILEEP = 345
    CRADILY = 346
    ANORITH = 347
    ARMALDO = 348
    FEEBAS = 349
    MILOTIC = 350
    CASTFORM = 351
    KECLEON = 352
    SHUPPET = 353
    BANETTE = 354
    DUSKULL = 355
    DUSCLOPS = 356
    TROPIUS = 357
    CHIMECHO = 358
    ABSOL = 359
    WYNAUT = 360
    SNORUNT = 361
    GLALIE = 362
    SPHEAL = 363
    SEALEO = 364
    WALREIN = 365
    CLAMPERL = 366
    HUNTAIL = 367
    GOREBYSS = 368
    RELICANTH = 369
    LUVDISC = 370
    BAGON = 371
    SHELGON = 372
    SALAMENCE = 373
    BELDUM = 374
    METANG = 375
    METAGROSS = 376
    REGIROCK = 377
    REGICE = 378
    REGISTEEL = 379
    LATIAS = 380
    LATIOS = 381
    KYOGRE = 382
    GROUDON = 383
    RAYQUAZA = 384
    JIRACHI = 385
    DEOXYS = 386
    TURTWIG = 387
    GROTLE = 388
    TORTERRA = 389
    CHIMCHAR = 390
    MONFERNO = 391
    INFERNAPE = 392
    PIPLUP = 393
    PRINPLUP = 394
    EMPOLEON = 395
    STARLY = 396
    STARAVIA = 397
    STARAPTOR = 398
    BIDOOF = 399
    BIBAREL = 400
    KRICKETOT = 401
    KRICKETUNE = 402
    SHINX = 403
    LUXIO = 404
    LUXRAY = 405
    BUDEW = 406
    ROSERADE = 407
    CRANIDOS = 408
    RAMPARDOS = 409
    SHIELDON = 410
    BASTIODON = 411
    BURMY = 412
    WORMADAM = 413
    MOTHIM = 414
    COMBEE = 415
    VESPIQUEN = 416
    PACHIRISU = 417
    BUIZEL = 418
    FLOATZEL = 419
    CHERUBI = 420
    CHERRIM = 421
    SHELLOS = 422
    GASTRODON = 423
    AMBIPOM = 424
    DRIFLOON = 425
    DRIFBLIM = 426
    BUNEARY = 427
    LOPUNNY = 428
    MISMAGIUS = 429
    HONCHKROW = 430
    GLAMEOW = 431
    PURUGLY = 432
    CHINGLING = 433
    STUNKY = 434
    SKUNTANK = 435
    BRONZOR = 436
    BRONZONG = 437
    BONSLY = 438
    MIMEJR = 439
    HAPPINY = 440
    CHATOT = 441
    SPIRITOMB = 442
    GIBLE = 443
    GABITE = 444
    GARCHOMP = 445
    MUNCHLAX = 446
    RIOLU = 447
    LUCARIO = 448
    HIPPOPOTAS = 449
    HIPPOWDON = 450
    SKORUPI = 451
    DRAPION = 452
    CROAGUNK = 453
    TOXICROAK = 454
    CARNIVINE = 455
    FINNEON = 456
    LUMINEON = 457
    MANTYKE = 458
    SNOVER = 459
    ABOMASNOW = 460
    WEAVILE = 461
    MAGNEZONE = 462
    LICKILICKY = 463
    RHYPERIOR = 464
    TANGROWTH = 465
    ELECTIVIRE = 466
    MAGMORTAR = 467
    TOGEKISS = 468
    YANMEGA = 469
    LEAFEON = 470
    GLACEON = 471
    GLISCOR = 472
    MAMOSWINE = 473
    PORYGONZ = 474
    GALLADE = 475
    PROBOPASS = 476
    DUSKNOIR = 477
    FROSLASS = 478
    ROTOM = 479
    UXIE = 480
    MESPRIT = 481
    AZELF = 482
    DIALGA = 483
    PALKIA = 484
    HEATRAN = 485
    REGIGIGAS = 486
    GIRATINA = 487
    CRESSELIA = 488
    PHIONE = 489
    MANAPHY = 490
    DARKRAI = 491
    SHAYMIN = 492
    ARCEUS = 493

class Move(Enum):
    NONE = 0
    POUND = 1
    KARATECHOP = 2
    DOUBLESLAP = 3
    COMETPUNCH = 4
    MEGAPUNCH = 5
    PAYDAY = 6
    FIREPUNCH = 7
    ICEPUNCH = 8
    THUNDERPUNCH = 9
    SCRATCH = 10
    VISEGRIP = 11
    GUILLOTINE = 12
    RAZORWIND = 13
    SWORDSDANCE = 14
    CUT = 15
    GUST = 16
    WINGATTACK = 17
    WHIRLWIND = 18
    FLY = 19
    BIND = 20
    SLAM = 21
    VINEWHIP = 22
    STOMP = 23
    DOUBLEKICK = 24
    MEGAKICK = 25
    JUMPKICK = 26
    ROLLINGKICK = 27
    SANDATTACK = 28
    HEADBUTT = 29
    HORNATTACK = 30
    FURYATTACK = 31
    HORNDRILL = 32
    TACKLE = 33
    BODYSLAM = 34
    WRAP = 35
    TAKEDOWN = 36
    THRASH = 37
    DOUBLEEDGE = 38
    TAILWHIP = 39
    POISONSTING = 40
    TWINEEDLE = 41
    PINMISSILE = 42
    LEER = 43
    BITE = 44
    GROWL = 45
    ROAR = 46
    SING = 47
    SUPERSONIC = 48
    SONICBOOM = 49
    DISABLE = 50
    ACID = 51
    EMBER = 52
    FLAMETHROWER = 53
    MIST = 54
    WATERGUN = 55
    HYDROPUMP = 56
    SURF = 57
    ICEBEAM = 58
    BLIZZARD = 59
    PSYBEAM = 60
    BUBBLEBEAM = 61
    AURORABEAM = 62
    HYPERBEAM = 63
    PECK = 64
    DRILLPECK = 65
    SUBMISSION = 66
    LOWKICK = 67
    COUNTER = 68
    SEISMICTOSS = 69
    STRENGTH = 70
    ABSORB = 71
    MEGADRAIN = 72
    LEECHSEED = 73
    GROWTH = 74
    RAZORLEAF = 75
    SOLARBEAM = 76
    POISONPOWDER = 77
    STUNSPORE = 78
    SLEEPPOWDER = 79
    PETALDANCE = 80
    STRINGSHOT = 81
    DRAGONRAGE = 82
    FIRESPIN = 83
    THUNDERSHOCK = 84
    THUNDERBOLT = 85
    THUNDERWAVE = 86
    THUNDER = 87
    ROCKTHROW = 88
    EARTHQUAKE = 89
    FISSURE = 90
    DIG = 91
    TOXIC = 92
    CONFUSION = 93
    PSYCHIC = 94
    HYPNOSIS = 95
    MEDITATE = 96
    AGILITY = 97
    QUICKATTACK = 98
    RAGE = 99
    TELEPORT = 100
    NIGHTSHADE = 101
    MIMIC = 102
    SCREECH = 103
    DOUBLETEAM = 104
    RECOVER = 105
    HARDEN = 106
    MINIMIZE = 107
    SMOKESCREEN = 108
    CONFUSERAY = 109
    WITHDRAW = 110
    DEFENSECURL = 111
    BARRIER = 112
    LIGHTSCREEN = 113
    HAZE = 114
    REFLECT = 115
    FOCUSENERGY = 116
    BIDE = 117
    METRONOME = 118
    MIRRORMOVE = 119
    SELFDESTRUCT = 120
    EGGBOMB = 121
    LICK = 122
    SMOG = 123
    SLUDGE = 124
    BONECLUB = 125
    FIREBLAST = 126
    WATERFALL = 127
    CLAMP = 128
    SWIFT = 129
    SKULLBASH = 130
    SPIKECANNON = 131
    CONSTRICT = 132
    AMNESIA = 133
    KINESIS = 134
    SOFTBOILED = 135
    HIGHJUMPKICK = 136
    GLARE = 137
    DREAMEATER = 138
    POISONGAS = 139
    BARRAGE = 140
    LEECHLIFE = 141
    LOVELYKISS = 142
    SKYATTACK = 143
    TRANSFORM = 144
    BUBBLE = 145
    DIZZYPUNCH = 146
    SPORE = 147
    FLASH = 148
    PSYWAVE = 149
    SPLASH = 150
    ACIDARMOR = 151
    CRABHAMMER = 152
    EXPLOSION = 153
    FURYSWIPES = 154
    BONEMERANG = 155
    REST = 156
    ROCKSLIDE = 157
    HYPERFANG = 158
    SHARPEN = 159
    CONVERSION = 160
    TRIATTACK = 161
    SUPERFANG = 162
    SLASH = 163
    SUBSTITUTE = 164
    STRUGGLE = 165
    SKETCH = 166
    TRIPLEKICK = 167
    THIEF = 168
    SPIDERWEB = 169
    MINDREADER = 170
    NIGHTMARE = 171
    FLAMEWHEEL = 172
    SNORE = 173
    CURSE = 174
    FLAIL = 175
    CONVERSION2 = 176
    AEROBLAST = 177
    COTTONSPORE = 178
    REVERSAL = 179
    SPITE = 180
    POWDERSNOW = 181
    PROTECT = 182
    MACHPUNCH = 183
    SCARYFACE = 184
    FEINTATTACK = 185
    SWEETKISS = 186
    BELLYDRUM = 187
    SLUDGEBOMB = 188
    MUDSLAP = 189
    OCTAZOOKA = 190
    SPIKES = 191
    ZAPCANNON = 192
    FORESIGHT = 193
    DESTINYBOND = 194
    PERISHSONG = 195
    ICYWIND = 196
    DETECT = 197
    BONERUSH = 198
    LOCKON = 199
    OUTRAGE = 200
    SANDSTORM = 201
    GIGADRAIN = 202
    ENDURE = 203
    CHARM = 204
    ROLLOUT = 205
    FALSESWIPE = 206
    SWAGGER = 207
    MILKDRINK = 208
    SPARK = 209
    FURYCUTTER = 210
    STEELWING = 211
    MEANLOOK = 212
    ATTRACT = 213
    SLEEPTALK = 214
    HEALBELL = 215
    RETURN = 216
    PRESENT = 217
    FRUSTRATION = 218
    SAFEGUARD = 219
    PAINSPLIT = 220
    SACREDFIRE = 221
    MAGNITUDE = 222
    DYNAMICPUNCH = 223
    MEGAHORN = 224
    DRAGONBREATH = 225
    BATONPASS = 226
    ENCORE = 227
    PURSUIT = 228
    RAPIDSPIN = 229
    SWEETSCENT = 230
    IRONTAIL = 231
    METALCLAW = 232
    VITALTHROW = 233
    MORNINGSUN = 234
    SYNTHESIS = 235
    MOONLIGHT = 236
    HIDDENPOWER = 237
    CROSSCHOP = 238
    TWISTER = 239
    RAINDANCE = 240
    SUNNYDAY = 241
    CRUNCH = 242
    MIRRORCOAT = 243
    PSYCHUP = 244
    EXTREMESPEED = 245
    ANCIENTPOWER = 246
    SHADOWBALL = 247
    FUTURESIGHT = 248
    ROCKSMASH = 249
    WHIRLPOOL = 250
    BEATUP = 251
    FAKEOUT = 252
    UPROAR = 253
    STOCKPILE = 254
    SPITUP = 255
    SWALLOW = 256
    HEATWAVE = 257
    HAIL = 258
    TORMENT = 259
    FLATTER = 260
    WILLOWISP = 261
    MEMENTO = 262
    FACADE = 263
    FOCUSPUNCH = 264
    SMELLINGSALTS = 265
    FOLLOWME = 266
    NATUREPOWER = 267
    CHARGE = 268
    TAUNT = 269
    HELPINGHAND = 270
    TRICK = 271
    ROLEPLAY = 272
    WISH = 273
    ASSIST = 274
    INGRAIN = 275
    SUPERPOWER = 276
    MAGICCOAT = 277
    RECYCLE = 278
    REVENGE = 279
    BRICKBREAK = 280
    YAWN = 281
    KNOCKOFF = 282
    ENDEAVOR = 283
    ERUPTION = 284
    SKILLSWAP = 285
    IMPRISON = 286
    REFRESH = 287
    GRUDGE = 288
    SNATCH = 289
    SECRETPOWER = 290
    DIVE = 291
    ARMTHRUST = 292
    CAMOUFLAGE = 293
    TAILGLOW = 294
    LUSTERPURGE = 295
    MISTBALL = 296
    FEATHERDANCE = 297
    TEETERDANCE = 298
    BLAZEKICK = 299
    MUDSPORT = 300
    ICEBALL = 301
    NEEDLEARM = 302
    SLACKOFF = 303
    HYPERVOICE = 304
    POISONFANG = 305
    CRUSHCLAW = 306
    BLASTBURN = 307
    HYDROCANNON = 308
    METEORMASH = 309
    ASTONISH = 310
    WEATHERBALL = 311
    AROMATHERAPY = 312
    FAKETEARS = 313
    AIRCUTTER = 314
    OVERHEAT = 315
    ODORSLEUTH = 316
    ROCKTOMB = 317
    SILVERWIND = 318
    METALSOUND = 319
    GRASSWHISTLE = 320
    TICKLE = 321
    COSMICPOWER = 322
    WATERSPOUT = 323
    SIGNALBEAM = 324
    SHADOWPUNCH = 325
    EXTRASENSORY = 326
    SKYUPPERCUT = 327
    SANDTOMB = 328
    SHEERCOLD = 329
    MUDDYWATER = 330
    BULLETSEED = 331
    AERIALACE = 332
    ICICLESPEAR = 333
    IRONDEFENSE = 334
    BLOCK = 335
    HOWL = 336
    DRAGONCLAW = 337
    FRENZYPLANT = 338
    BULKUP = 339
    BOUNCE = 340
    MUDSHOT = 341
    POISONTAIL = 342
    COVET = 343
    VOLTTACKLE = 344
    MAGICALLEAF = 345
    WATERSPORT = 346
    CALMMIND = 347
    LEAFBLADE = 348
    DRAGONDANCE = 349
    ROCKBLAST = 350
    SHOCKWAVE = 351
    WATERPULSE = 352
    DOOMDESIRE = 353
    PSYCHOBOOST = 354
    ROOST = 355
    GRAVITY = 356
    MIRACLEEYE = 357
    WAKEUPSLAP = 358
    HAMMERARM = 359
    GYROBALL = 360
    HEALINGWISH = 361
    BRINE = 362
    NATURALGIFT = 363
    FEINT = 364
    PLUCK = 365
    TAILWIND = 366
    ACUPRESSURE = 367
    METALBURST = 368
    UTURN = 369
    CLOSECOMBAT = 370
    PAYBACK = 371
    ASSURANCE = 372
    EMBARGO = 373
    FLING = 374
    PSYCHOSHIFT = 375
    TRUMPCARD = 376
    HEALBLOCK = 377
    WRINGOUT = 378
    POWERTRICK = 379
    GASTROACID = 380
    LUCKYCHANT = 381
    MEFIRST = 382
    COPYCAT = 383
    POWERSWAP = 384
    GUARDSWAP = 385
    PUNISHMENT = 386
    LASTRESORT = 387
    WORRYSEED = 388
    SUCKERPUNCH = 389
    TOXICSPIKES = 390
    HEARTSWAP = 391
    AQUARING = 392
    MAGNETRISE = 393
    FLAREBLITZ = 394
    FORCEPALM = 395
    AURASPHERE = 396
    ROCKPOLISH = 397
    POISONJAB = 398
    DARKPULSE = 399
    NIGHTSLASH = 400
    AQUATAIL = 401
    SEEDBOMB = 402
    AIRSLASH = 403
    XSCISSOR = 404
    BUGBUZZ = 405
    DRAGONPULSE = 406
    DRAGONRUSH = 407
    POWERGEM = 408
    DRAINPUNCH = 409
    VACUUMWAVE = 410
    FOCUSBLAST = 411
    ENERGYBALL = 412
    BRAVEBIRD = 413
    EARTHPOWER = 414
    SWITCHEROO = 415
    GIGAIMPACT = 416
    NASTYPLOT = 417
    BULLETPUNCH = 418
    AVALANCHE = 419
    ICESHARD = 420
    SHADOWCLAW = 421
    THUNDERFANG = 422
    ICEFANG = 423
    FIREFANG = 424
    SHADOWSNEAK = 425
    MUDBOMB = 426
    PSYCHOCUT = 427
    ZENHEADBUTT = 428
    MIRRORSHOT = 429
    FLASHCANNON = 430
    ROCKCLIMB = 431
    DEFOG = 432
    TRICKROOM = 433
    DRACOMETEOR = 434
    DISCHARGE = 435
    LAVAPLUME = 436
    LEAFSTORM = 437
    POWERWHIP = 438
    ROCKWRECKER = 439
    CROSSPOISON = 440
    GUNKSHOT = 441
    IRONHEAD = 442
    MAGNETBOMB = 443
    STONEEDGE = 444
    CAPTIVATE = 445
    STEALTHROCK = 446
    GRASSKNOT = 447
    CHATTER = 448
    JUDGMENT = 449
    BUGBITE = 450
    CHARGEBEAM = 451
    WOODHAMMER = 452
    AQUAJET = 453
    ATTACKORDER = 454
    DEFENDORDER = 455
    HEALORDER = 456
    HEADSMASH = 457
    DOUBLEHIT = 458
    ROAROFTIME = 459
    SPACIALREND = 460
    LUNARDANCE = 461
    CRUSHGRIP = 462
    MAGMASTORM = 463
    DARKVOID = 464
    SEEDFLARE = 465
    OMINOUSWIND = 466
    SHADOWFORCE = 467

# Convert Enums to lists for the Dropdowns
POKEMON_SPECIES_LIST = [s.name for s in Species]
MOVE_LIST = [m.name for m in Move]

# Raw string lists
ITEM_LIST = [
    "", "None", "Master Ball", "Ultra Ball", "Great Ball", "Poké Ball", "Safari Ball", 
    "Net Ball", "Dive Ball", "Nest Ball", "Repeat Ball", "Timer Ball", "Luxury Ball", 
    "Premier Ball", "Dusk Ball", "Heal Ball", "Quick Ball", "Cherish Ball", "Potion", 
    "Antidote", "Burn Heal", "Ice Heal", "Awakening", "Paralyze Heal", "Full Restore", 
    "Max Potion", "Hyper Potion", "Super Potion", "Full Heal", "Revive", "Max Revive", 
    "Fresh Water", "Soda Pop", "Lemonade", "Moomoo Milk", "Energy Powder", "Energy Root", 
    "Heal Powder", "Revival Herb", "Ether", "Max Ether", "Elixir", "Max Elixir", 
    "Lava Cookie", "Berry Juice", "Sacred Ash", "HP Up", "Protein", "Iron", "Carbos", 
    "Calcium", "Rare Candy", "PP Up", "Zinc", "PP Max", "Old Gateau", "Guard Spec.", 
    "Dire Hit", "X Attack", "X Defense", "X Speed", "X Accuracy", "X Sp. Atk", 
    "X Sp. Def", "Poké Doll", "Fluffy Tail", "Blue Flute", "Yellow Flute", "Red Flute", 
    "Black Flute", "White Flute", "Shoal Salt", "Shoal Shell", "Red Shard", "Blue Shard", 
    "Yellow Shard", "Green Shard", "Super Repel", "Max Repel", "Escape Rope", "Repel", 
    "Sun Stone", "Moon Stone", "Fire Stone", "Thunder Stone", "Water Stone", "Leaf Stone", 
    "Tiny Mushroom", "Big Mushroom", "Pearl", "Big Pearl", "Stardust", "Star Piece", 
    "Nugget", "Heart Scale", "Honey", "Growth Mulch", "Damp Mulch", "Stable Mulch", 
    "Gooey Mulch", "Root Fossil", "Claw Fossil", "Helix Fossil", "Dome Fossil", 
    "Old Amber", "Armor Fossil", "Skull Fossil", "Rare Bone", "Shiny Stone", "Dusk Stone", 
    "Dawn Stone", "Oval Stone", "Odd Keystone", "Griseous Orb", "Tea", "???", 
    "Autograph", "Douse Drive", "Shock Drive", "Burn Drive", "Chill Drive", "???", 
    "Pokémon Box Link", "Medicine Pocket", "TM Case", "Candy Jar", "Power-Up Pocket", 
    "Clothing Trunk", "Catching Pocket", "Battle Pocket", "???", "???", "???", "???", 
    "???", "Sweet Heart", "Adamant Orb", "Lustrous Orb", "Greet Mail", "Favored Mail", 
    "RSVP Mail", "Thanks Mail", "Inquiry Mail", "Like Mail", "Reply Mail", 
    "Bridge Mail S", "Bridge Mail D", "Bridge Mail T", "Bridge Mail V", "Bridge Mail M", 
    "Cheri Berry", "Chesto Berry", "Pecha Berry", "Rawst Berry", "Aspear Berry", 
    "Leppa Berry", "Oran Berry", "Persim Berry", "Lum Berry", "Sitrus Berry", 
    "Figy Berry", "Wiki Berry", "Mago Berry", "Aguav Berry", "Iapapa Berry", 
    "Razz Berry", "Bluk Berry", "Nanab Berry", "Wepear Berry", "Pinap Berry", 
    "Pomeg Berry", "Kelpsy Berry", "Qualot Berry", "Hondew Berry", "Grepa Berry", 
    "Tamato Berry", "Cornn Berry", "Magost Berry", "Rabuta Berry", "Nomel Berry", 
    "Spelon Berry", "Pamtre Berry", "Watmel Berry", "Durin Berry", "Belue Berry", 
    "Occa Berry", "Passho Berry", "Wacan Berry", "Rindo Berry", "Yache Berry", 
    "Chople Berry", "Kebia Berry", "Shuca Berry", "Coba Berry", "Payapa Berry", 
    "Tanga Berry", "Charti Berry", "Kasib Berry", "Haban Berry", "Colbur Berry", 
    "Babiri Berry", "Chilan Berry", "Liechi Berry", "Ganlon Berry", "Salac Berry", 
    "Petaya Berry", "Apicot Berry", "Lansat Berry", "Starf Berry", "Enigma Berry", 
    "Micle Berry", "Custap Berry", "Jaboca Berry", "Rowap Berry", "Bright Powder", 
    "White Herb", "Macho Brace", "Exp. Share", "Quick Claw", "Soothe Bell", "Mental Herb", 
    "Choice Band", "King’s Rock", "Silver Powder", "Amulet Coin", "Cleanse Tag", 
    "Soul Dew", "Deep Sea Tooth", "Deep Sea Scale", "Smoke Ball", "Everstone", 
    "Focus Band", "Lucky Egg", "Scope Lens", "Metal Coat", "Leftovers", "Dragon Scale", 
    "Light Ball", "Soft Sand", "Hard Stone", "Miracle Seed", "Black Glasses", 
    "Black Belt", "Magnet", "Mystic Water", "Sharp Beak", "Poison Barb", "Never-Melt Ice", 
    "Spell Tag", "Twisted Spoon", "Charcoal", "Dragon Fang", "Silk Scarf", "Upgrade", 
    "Shell Bell", "Sea Incense", "Lax Incense", "Lucky Punch", "Metal Powder", 
    "Thick Club", "Leek", "Red Scarf", "Blue Scarf", "Pink Scarf", "Green Scarf", 
    "Yellow Scarf", "Wide Lens", "Muscle Band", "Wise Glasses", "Expert Belt", 
    "Light Clay", "Life Orb", "Power Herb", "Toxic Orb", "Flame Orb", "Quick Powder", 
    "Focus Sash", "Zoom Lens", "Metronome", "Iron Ball", "Lagging Tail", "Destiny Knot", 
    "Black Sludge", "Icy Rock", "Smooth Rock", "Heat Rock", "Damp Rock", "Grip Claw", 
    "Choice Scarf", "Sticky Barb", "Power Bracer", "Power Belt", "Power Lens", 
    "Power Band", "Power Anklet", "Power Weight", "Shed Shell", "Big Root", 
    "Choice Specs", "Flame Plate", "Splash Plate", "Zap Plate", "Meadow Plate", 
    "Icicle Plate", "Fist Plate", "Toxic Plate", "Earth Plate", "Sky Plate", 
    "Mind Plate", "Insect Plate", "Stone Plate", "Spooky Plate", "Draco Plate", 
    "Dread Plate", "Iron Plate", "Odd Incense", "Rock Incense", "Full Incense", 
    "Wave Incense", "Rose Incense", "Luck Incense", "Pure Incense", "Protector", 
    "Electirizer", "Magmarizer", "Dubious Disc", "Reaper Cloth", "Razor Claw", 
    "Razor Fang", "TM01", "TM02", "TM03", "TM04", "TM05", "TM06", "TM07", "TM08", 
    "TM09", "TM10", "TM11", "TM12", "TM13", "TM14", "TM15", "TM16", "TM17", "TM18", 
    "TM19", "TM20", "TM21", "TM22", "TM23", "TM24", "TM25", "TM26", "TM27", "TM28", 
    "TM29", "TM30", "TM31", "TM32", "TM33", "TM34", "TM35", "TM36", "TM37", "TM38", 
    "TM39", "TM40", "TM41", "TM42", "TM43", "TM44", "TM45", "TM46", "TM47", "TM48", 
    "TM49", "TM50", "TM51", "TM52", "TM53", "TM54", "TM55", "TM56", "TM57", "TM58", 
    "TM59", "TM60", "TM61", "TM62", "TM63", "TM64", "TM65", "TM66", "TM67", "TM68", 
    "TM69", "TM70", "TM71", "TM72", "TM73", "TM74", "TM75", "TM76", "TM77", "TM78", 
    "TM79", "TM80", "TM81", "TM82", "TM83", "TM84", "TM85", "TM86", "TM87", "TM88", 
    "TM89", "TM90", "TM91", "TM92", "HM01", "HM02", "HM03", "HM04", "HM05", "HM06", 
    "???", "???", "Explorer Kit", "Loot Sack", "Rule Book", "Poké Radar", "Point Card", 
    "Journal", "Seal Case", "Fashion Case", "Seal Bag", "Pal Pad", "Works Key", 
    "Old Charm", "Galactic Key", "Red Chain", "Town Map", "Vs. Seeker", "Coin Case", 
    "Old Rod", "Good Rod", "Super Rod", "Sprayduck", "Poffin Case", "Bike", 
    "Suite Key", "Oak’s Letter", "Lunar Feather", "Member Card", "Azure Flute", 
    "S.S. Ticket", "Contest Pass", "Magma Stone", "Parcel", "Coupon 1", "Coupon 2", 
    "Coupon 3", "Storage Key", "Secret Medicine", "Vs. Recorder", "Gracidea", 
    "Secret Key", "Apricorn Box", "Unown Report", "Berry Pots", "Dowsing Machine", 
    "Blue Card", "Slowpoke Tail", "Clear Bell", "Card Key", "Basement Key", 
    "Squirt Bottle", "Red Scale", "Lost Item", "Pass", "Machine Part", "Silver Wing", 
    "Rainbow Wing", "Mystery Egg", "Red Apricorn", "Blue Apricorn", "Yellow Apricorn", 
    "Green Apricorn", "Pink Apricorn", "White Apricorn", "Black Apricorn", "Fast Ball", 
    "Level Ball", "Lure Ball", "Heavy Ball", "Love Ball", "Friend Ball", "Moon Ball", 
    "Sport Ball", "Park Ball", "Photo Album", "GB Sounds", "Tidal Bell", "Rage Candy Bar", 
    "Data Card 01", "Data Card 02", "Data Card 03", "Data Card 04", "Data Card 05", 
    "Data Card 06", "Data Card 07", "Data Card 08", "Data Card 09", "Data Card 10", 
    "Data Card 11", "Data Card 12", "Data Card 13", "Data Card 14", "Data Card 15", 
    "Data Card 16", "Data Card 17", "Data Card 18", "Data Card 19", "Data Card 20", 
    "Data Card 21", "Data Card 22", "Data Card 23", "Data Card 24", "Data Card 25", 
    "Data Card 26", "Data Card 27", "Jade Orb", "Lock Capsule", "Red Orb", "Blue Orb"
]

BACKGROUNDS = [
    "FOREST", "BEACH", "VOLCANO", "URBAN", "RUGGED",
    "FIELD", "NIGHT", "SNOW", "CAVE", "WATER",
]

COURSE_SLOTS = [
    "0 - Refreshing Field", "1 - Noisy Forest", "2 - Rugged Road",
    "3 - Beautiful Beach", "4 - Suburban Area", "5 - Dim Cave",
    "6 - Blue Lake", "7 - Town Outskirts", "8 - Hoenn Field",
    "9 - Warm Beach", "10 - Volcano Path", "11 - Treehouse",
    "12 - Scary Cave", "13 - Sinnoh Field", "14 - Icy Mountain Rd.",
    "15 - Big Forest", "16 - White Lake", "17 - Stormy Beach",
    "18 - Resort", "19 - Quiet Cave", "20 - Beyond the Sea",
    "21 - Night Sky's Edge", "22 - Yellow Forest", "23 - Rally",
    "24 - Sightseeing", "25 - Winner's Path", "26 - Amity Meadow"
]

def main():
    root = tk.Tk()
    app = CourseEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
