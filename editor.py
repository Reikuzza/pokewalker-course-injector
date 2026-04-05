import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


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

        self.build_ui()

    def build_ui(self):
        # Top frame: basic info
        top = tk.Frame(self.root, padx=5, pady=5)
        top.pack(fill=tk.X)

        tk.Label(top, text="Course Name:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(top, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky="w")

        tk.Label(top, text="Background:").grid(row=1, column=0, sticky="w")
        self.bg_var = tk.StringVar()
        tk.Entry(top, textvariable=self.bg_var, width=30).grid(row=1, column=1, sticky="w")

        # Middle frame: Pokémon and Items
        mid = tk.Frame(self.root, padx=5, pady=5)
        mid.pack(fill=tk.BOTH, expand=True)

        # Pokémon panel
        poke_frame = tk.LabelFrame(mid, text="Pokémon Slots", padx=5, pady=5)
        poke_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.poke_list = tk.Listbox(poke_frame, height=12)
        self.poke_list.pack(fill=tk.BOTH, expand=True)

        poke_btns = tk.Frame(poke_frame)
        poke_btns.pack(fill=tk.X, pady=3)

        tk.Button(poke_btns, text="Add", command=self.add_pokemon).pack(side=tk.LEFT, padx=2)
        tk.Button(poke_btns, text="Edit", command=self.edit_pokemon).pack(side=tk.LEFT, padx=2)
        tk.Button(poke_btns, text="Remove", command=self.remove_pokemon).pack(side=tk.LEFT, padx=2)

        # Items panel
        item_frame = tk.LabelFrame(mid, text="Item Slots", padx=5, pady=5)
        item_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.item_list = tk.Listbox(item_frame, height=12)
        self.item_list.pack(fill=tk.BOTH, expand=True)

        item_btns = tk.Frame(item_frame)
        item_btns.pack(fill=tk.X, pady=3)

        tk.Button(item_btns, text="Add", command=self.add_item).pack(side=tk.LEFT, padx=2)
        tk.Button(item_btns, text="Edit", command=self.edit_item).pack(side=tk.LEFT, padx=2)
        tk.Button(item_btns, text="Remove", command=self.remove_item).pack(side=tk.LEFT, padx=2)

        # Bottom: file buttons
        bottom = tk.Frame(self.root, padx=5, pady=5)
        bottom.pack(fill=tk.X)

        tk.Button(bottom, text="New", command=self.new_course).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Open...", command=self.open_course).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Save", command=self.save_course).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Save As...", command=self.save_course_as).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom, text="Quit", command=self.root.quit).pack(side=tk.RIGHT, padx=2)

    # ---------- Course management ----------

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

        # Map data into our structure, with fallbacks
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
        path = filedialog.asksavefilename(
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
        # Simple: always ask; you can make this smarter if you want
        return messagebox.askyesno("Confirm", "Discard current changes?")

    # ---------- UI sync ----------

    def refresh_ui(self):
        self.name_var.set(self.course.get("name", ""))
        self.bg_var.set(self.course.get("background", ""))

        self.poke_list.delete(0, tk.END)
        for p in self.course.get("pokemon", []):
            species = p.get("species", "???")
            min_lv = p.get("min_level", "?")
            max_lv = p.get("max_level", "?")
            rate = p.get("rate", "?")
            self.poke_list.insert(tk.END, f"{species} Lv{min_lv}-{max_lv} ({rate}%)")

        self.item_list.delete(0, tk.END)
        for it in self.course.get("items", []):
            name = it.get("name", "???")
            rate = it.get("rate", "?")
            self.item_list.insert(tk.END, f"{name} ({rate}%)")

    def update_course_from_ui(self):
        self.course["name"] = self.name_var.get()
        self.course["background"] = self.bg_var.get()

    # ---------- Pokémon editing ----------

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
        initial = initial or {}
        species = simpledialog.askstring(
            "Species",
            "Species (e.g. PIKACHU):",
            initialvalue=initial.get("species", "")
        )
        if species is None:
            return None
        try:
            min_lv = int(simpledialog.askstring(
                "Min Level",
                "Minimum level:",
                initialvalue=str(initial.get("min_level", 1))
            ))
            max_lv = int(simpledialog.askstring(
                "Max Level",
                "Maximum level:",
                initialvalue=str(initial.get("max_level", min_lv))
            ))
            rate = int(simpledialog.askstring(
                "Rate",
                "Encounter rate (0–100):",
                initialvalue=str(initial.get("rate", 10))
            ))
        except (TypeError, ValueError):
            messagebox.showerror("Error", "Invalid numeric value.")
            return None

        return {
            "species": species,
            "min_level": min_lv,
            "max_level": max_lv,
            "rate": rate
        }

    # ---------- Item editing ----------

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
        initial = initial or {}
        name = simpledialog.askstring(
            "Item Name",
            "Item name (e.g. POTION):",
            initialvalue=initial.get("name", "")
        )
        if name is None:
            return None
        try:
            rate = int(simpledialog.askstring(
                "Rate",
                "Item rate (0–100):",
                initialvalue=str(initial.get("rate", 10))
            ))
        except (TypeError, ValueError):
            messagebox.showerror("Error", "Invalid numeric value.")
            return None

        return {
            "name": name,
            "rate": rate
        }


def main():
    root = tk.Tk()
    app = CourseEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
