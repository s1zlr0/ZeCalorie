"""
zecalorie.py — ZeCalorie

Мой трекер калорий) делал на выходных, пока сидел на диете.
Переделал интерфейс на кастомные виджеты, потому что стандартный tkinter
выглядит как из 2005 года. Стало норм, вроде.

TODO: может добавить темную тему когда-нибудь
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


def resource_path(*parts):
    """Путь к файлам, зашитым внутрь exe (иконка и т.п.) — при сборке PyInstaller
    они распаковываются во временную папку sys._MEIPASS."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def data_path(*parts):
    """Путь к файлам с пользовательскими данными. Если использовать __file__
    в собранном --onefile exe, он будет указывать на временную папку, которая
    удаляется при закрытии программы — и все сохранения будут пропадать.
    Поэтому для .exe данные кладём рядом с самим exe-файлом."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


DATA_FILE = data_path("meals.json")
SETTINGS_FILE = data_path("settings.json")
ICON_ICO = resource_path("assets", "app_icon.ico")
ICON_PNG = resource_path("assets", "app_icon_256.png")

CATEGORIES = ["Завтрак", "Обед", "Ужин", "Перекус"]

# ---- палитра (нейтральный светлый фон + один акцентный цвет, без вырвиглазного) ----
PAGE_BG = "#f3f4f6"
CARD_BG = "#ffffff"
BORDER = "#e5e7eb"
BORDER_SOFT = "#eef0f3"
TEXT = "#111827"
TEXT_MUTED = "#6b7280"
ACCENT = "#ff6b4a"
ACCENT_HOVER = "#f2572f"
ACCENT_SOFT = "#fff0ea"
GREEN = "#15803d"
AMBER = "#b45309"
RED = "#b91c1c"
TRACK = "#e9eaee"

FONT = "Segoe UI"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def rounded_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


class RoundedButton(tk.Canvas):
    """Кнопка со скруглёнными углами, рисуется на канвасе (обычный ttk выглядит слишком по-виндовски)."""

    def __init__(self, parent, text, command=None, bg=ACCENT, fg="white",
                 hover_bg=ACCENT_HOVER, border=None, font_size=10, bold=False,
                 radius=10, padx=18, pady=10):
        font = (FONT, font_size, "bold" if bold else "normal")
        probe = tk.Label(parent, text=text, font=font)
        probe.update_idletasks()
        w = probe.winfo_reqwidth() + padx * 2
        h = probe.winfo_reqheight() + pady * 2
        probe.destroy()

        parent_bg = parent.cget("bg") if "bg" in parent.keys() else PAGE_BG
        super().__init__(parent, width=w, height=h, bg=parent_bg, highlightthickness=0, cursor="hand2")

        self.command = command
        self.text = text
        self.font = font
        self.w, self.h, self.radius = w, h, radius
        self.bg_normal = bg
        self.bg_hover = hover_bg
        self.fg = fg
        self.border = border

        self._draw(self.bg_normal)
        self.bind("<Enter>", lambda e: self._draw(self.bg_hover))
        self.bind("<Leave>", lambda e: self._draw(self.bg_normal))
        self.bind("<Button-1>", self._click)

    def _click(self, _event):
        if self.command:
            self.command()

    def _draw(self, color):
        self.delete("all")
        pts = rounded_points(1, 1, self.w - 1, self.h - 1, self.radius)
        outline = self.border if self.border else color
        self.create_polygon(pts, smooth=True, fill=color, outline=outline, width=1)
        self.create_text(self.w / 2, self.h / 2, text=self.text, fill=self.fg, font=self.font)

    def set_state(self, active: bool):
        """для кнопок-переключателей вкладок"""
        if active:
            self.bg_normal, self.fg_saved = ACCENT, self.fg
            self.fg = "white"
            self._draw(ACCENT)
        else:
            self.fg = TEXT_MUTED
            self._draw(CARD_BG)


class SegmentedControl(tk.Frame):
    """Переключатель вкладок в виде "таблетки", вместо стандартных ttk-табов."""

    def __init__(self, parent, options, on_change):
        super().__init__(parent, bg=PAGE_BG)
        self.on_change = on_change
        self.buttons = {}
        self.active = options[0][0]

        pill = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        pill.pack()

        for key, label in options:
            btn = RoundedButton(
                pill, label, command=lambda k=key: self._select(k),
                bg=CARD_BG, hover_bg=ACCENT_SOFT, fg=TEXT_MUTED,
                radius=8, padx=16, pady=8,
            )
            btn.pack(side="left", padx=3, pady=3)
            self.buttons[key] = btn

        self._select(self.active, notify=False)

    def _select(self, key, notify=True):
        self.active = key
        for k, btn in self.buttons.items():
            if k == key:
                btn.fg = "white"
                btn._draw(ACCENT)
            else:
                btn.fg = TEXT_MUTED
                btn._draw(CARD_BG)
        if notify:
            self.on_change(key)


class Card(tk.Frame):
    """Белая карточка со скруглёнными углами, подстраивается под содержимое."""

    def __init__(self, parent, title=None, padx=16, pady=14, radius=14):
        super().__init__(parent, bg=PAGE_BG)
        self.canvas = tk.Canvas(self, bg=PAGE_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=CARD_BG)
        self._win = self.canvas.create_window(padx, pady, window=self.inner, anchor="nw")
        self.padx, self.pady, self.radius = padx, pady, radius

        if title:
            tk.Label(
                self.inner, text=title, bg=CARD_BG, fg=TEXT,
                font=(FONT, 11, "bold"),
            ).pack(anchor="w", pady=(0, 10))

        self.inner.bind("<Configure>", self._redraw)

    def _redraw(self, _event=None):
        w = self.inner.winfo_reqwidth() + self.padx * 2
        h = self.inner.winfo_reqheight() + self.pady * 2
        self.canvas.config(width=w, height=h)
        self.canvas.delete("card_bg")
        pts = rounded_points(1, 1, w - 1, h - 1, self.radius)
        self.canvas.create_polygon(pts, smooth=True, fill=CARD_BG, outline=BORDER, width=1, tags="card_bg")
        self.canvas.tag_lower("card_bg")


class ProgressBar(tk.Canvas):
    """Тонкая полоска прогресса под сводкой калорий."""

    def __init__(self, parent, width=380, height=10):
        super().__init__(parent, width=width, height=height, bg=CARD_BG, highlightthickness=0)
        self.w, self.h = width, height
        self.set_value(0, TRACK)

    def set_value(self, fraction, color):
        self.delete("all")
        r = self.h / 2
        self.create_polygon(rounded_points(0, 0, self.w, self.h, r), smooth=True, fill=TRACK, outline=TRACK)
        fraction = max(0.0, min(1.0, fraction))
        fw = max(self.h, self.w * fraction)
        if fraction > 0:
            self.create_polygon(rounded_points(0, 0, fw, self.h, r), smooth=True, fill=color, outline=color)


def styled_entry(parent, textvariable=None, width=16):
    return tk.Entry(
        parent, textvariable=textvariable, width=width, font=(FONT, 10),
        bg=CARD_BG, fg=TEXT, relief="flat",
        highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
        insertbackground=TEXT,
    )


class CalorieTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZeCalorie 🍽")
        self.geometry("720x820")
        self.minsize(720, 700)
        self.configure(bg=PAGE_BG)
        self.resizable(True, True)
        self._set_app_icon()
        self._setup_ttk_style()

        self.meals = load_json(DATA_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {"daily_goal": 2000})

        # дата фиксируется при запуске, потом не трогаем
        self.current_date = datetime.now().strftime("%Y-%m-%d")

        self.pages = {}
        self._build_ui()
        self.refresh_today_list()
        self.refresh_history_dates()
        self._maximize_window()

    def _maximize_window(self):
        # разворачиваем на весь экран при запуске, по-разному на разных ОС
        try:
            self.state("zoomed")  # Windows и часть Linux WM
            return
        except tk.TclError:
            pass
        try:
            self.attributes("-zoomed", True)  # Linux (X11)
            return
        except tk.TclError:
            pass
        # запасной вариант (macOS и всё остальное) — растягиваем под размер экрана
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")

    def _set_app_icon(self):
        try:
            self.iconbitmap(ICON_ICO)
        except tk.TclError:
            pass
        try:
            icon_img = tk.PhotoImage(file=ICON_PNG)
            self.iconphoto(True, icon_img)
            self._icon_ref = icon_img
        except tk.TclError:
            pass

    def _setup_ttk_style(self):
        # combobox остается ttk-шным (без него неудобно), но перекрашиваем под общий стиль
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TCombobox",
            fieldbackground=CARD_BG,
            background=CARD_BG,
            foreground=TEXT,
            bordercolor=BORDER,
            arrowcolor=TEXT_MUTED,
            padding=6,
        )
        style.map("TCombobox", fieldbackground=[("readonly", CARD_BG)])

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # центрируем колонку с контентом, чтобы на широком экране всё не липло к левому краю
        wrapper = tk.Frame(self, bg=PAGE_BG)
        wrapper.place(relx=0.5, rely=0, anchor="n")

        top = tk.Frame(wrapper, bg=PAGE_BG)
        top.pack(fill="x", padx=24, pady=(20, 4))

        tk.Label(
            top, text="🍽", bg=PAGE_BG, font=(FONT, 20),
        ).pack(side="left")
        title_box = tk.Frame(top, bg=PAGE_BG)
        title_box.pack(side="left", padx=(8, 0))
        tk.Label(title_box, text="ZeCalorie", bg=PAGE_BG, fg=TEXT, font=(FONT, 17, "bold")).pack(anchor="w")
        tk.Label(
            title_box, text="считаем что съел, а не то что хотели бы",
            bg=PAGE_BG, fg=TEXT_MUTED, font=(FONT, 9),
        ).pack(anchor="w")

        nav_row = tk.Frame(wrapper, bg=PAGE_BG)
        nav_row.pack(pady=(14, 10))
        self.segmented = SegmentedControl(
            nav_row,
            [("today", "Сегодня"), ("history", "История"), ("settings", "Настройки")],
            on_change=self.show_page,
        )
        self.segmented.pack()

        self.content = tk.Frame(wrapper, bg=PAGE_BG)
        self.content.pack(fill="both", expand=True, pady=(0, 20))

        self.pages["today"] = tk.Frame(self.content, bg=PAGE_BG)
        self.pages["history"] = tk.Frame(self.content, bg=PAGE_BG)
        self.pages["settings"] = tk.Frame(self.content, bg=PAGE_BG)

        self._build_today_page(self.pages["today"])
        self._build_history_page(self.pages["history"])
        self._build_settings_page(self.pages["settings"])

        self.show_page("today")

    def show_page(self, key):
        for name, frame in self.pages.items():
            if name == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    def _build_today_page(self, parent):
        form_card = Card(parent, title="Добавить что съел")
        form_card.pack(fill="x", pady=(0, 14))
        form = form_card.inner

        row1 = tk.Frame(form, bg=CARD_BG)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Категория", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=0, column=0, sticky="w")
        tk.Label(row1, text="Название", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=0, column=1, sticky="w", padx=(14, 0))

        self.category_var = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(
            row1, textvariable=self.category_var, values=CATEGORIES, state="readonly", width=13
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.name_var = tk.StringVar()
        styled_entry(row1, textvariable=self.name_var, width=26).grid(row=1, column=1, sticky="w", padx=(14, 0), pady=(2, 0))

        row2 = tk.Frame(form, bg=CARD_BG)
        row2.pack(fill="x", pady=(12, 4))
        tk.Label(row2, text="Калории", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=0, column=0, sticky="w")
        tk.Label(row2, text="Белки / Жиры / Углеводы (г)", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(
            row=0, column=1, sticky="w", padx=(14, 0)
        )

        self.cal_var = tk.StringVar()
        styled_entry(row2, textvariable=self.cal_var, width=13).grid(row=1, column=0, sticky="w", pady=(2, 0))

        macro_frame = tk.Frame(row2, bg=CARD_BG)
        macro_frame.grid(row=1, column=1, sticky="w", padx=(14, 0), pady=(2, 0))
        self.protein_var = tk.StringVar()
        self.fat_var = tk.StringVar()
        self.carbs_var = tk.StringVar()
        styled_entry(macro_frame, textvariable=self.protein_var, width=5).pack(side="left")
        styled_entry(macro_frame, textvariable=self.fat_var, width=5).pack(side="left", padx=6)
        styled_entry(macro_frame, textvariable=self.carbs_var, width=5).pack(side="left")

        btn_row = tk.Frame(form, bg=CARD_BG)
        btn_row.pack(fill="x", pady=(16, 0))
        self.add_button = RoundedButton(btn_row, "Добавить  →", command=self.add_meal, bold=True)
        self.add_button.pack(anchor="w")

        list_card = Card(parent, title="Что было сегодня")
        list_card.pack(fill="x", pady=(0, 14))
        list_body = list_card.inner

        list_wrap = tk.Frame(list_body, bg=CARD_BG, highlightbackground=BORDER_SOFT, highlightthickness=1)
        list_wrap.pack(fill="x")

        self.today_listbox = tk.Listbox(
            list_wrap, height=7, bg=CARD_BG, fg=TEXT, selectbackground=ACCENT, selectforeground="white",
            font=(FONT, 10), borderwidth=0, highlightthickness=0, activestyle="none",
        )
        self.today_listbox.pack(fill="both", expand=True, side="left", padx=8, pady=6)

        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical", command=self.today_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.today_listbox.config(yscrollcommand=scrollbar.set)

        del_row = tk.Frame(list_body, bg=CARD_BG)
        del_row.pack(fill="x", pady=(12, 0))
        RoundedButton(
            del_row, "Удалить выбранное", command=self.delete_selected_meal,
            bg=CARD_BG, hover_bg=BORDER_SOFT, fg=TEXT, border=BORDER,
        ).pack(anchor="w")

        summary_card = Card(parent, title="Итог за день")
        summary_card.pack(fill="x")
        sbody = summary_card.inner

        self.summary_label = tk.Label(sbody, text="", bg=CARD_BG, fg=TEXT, font=(FONT, 12, "bold"))
        self.summary_label.pack(anchor="w")

        self.summary_note = tk.Label(sbody, text="", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9))
        self.summary_note.pack(anchor="w", pady=(2, 8))

        self.progress = ProgressBar(sbody, width=420, height=10)
        self.progress.pack(anchor="w")

    def _build_history_page(self, parent):
        list_card = Card(parent, title="Прошлые дни")
        list_card.pack(fill="x", pady=(0, 14))

        self.history_dates_listbox = tk.Listbox(
            list_card.inner, height=6, bg=CARD_BG, fg=TEXT, font=(FONT, 10),
            selectbackground=ACCENT, selectforeground="white", borderwidth=0,
            highlightthickness=1, highlightbackground=BORDER_SOFT, activestyle="none",
        )
        self.history_dates_listbox.pack(fill="x", ipady=4)
        self.history_dates_listbox.bind("<<ListboxSelect>>", self.show_history_day)

        detail_card = Card(parent, title="Детали дня")
        detail_card.pack(fill="x")

        self.history_detail = tk.Text(
            detail_card.inner, height=12, width=52, state="disabled", bg=CARD_BG, fg=TEXT,
            font=(FONT, 10), borderwidth=0, highlightthickness=0,
        )
        self.history_detail.pack(fill="both", expand=True)

    def _build_settings_page(self, parent):
        goal_card = Card(parent, title="Дневная норма калорий")
        goal_card.pack(fill="x", pady=(0, 14))
        gbody = goal_card.inner

        tk.Label(gbody, text="Сколько калорий в день себе позволяю", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).pack(
            anchor="w"
        )
        self.goal_var = tk.StringVar(value=str(self.settings.get("daily_goal", 2000)))
        row = tk.Frame(gbody, bg=CARD_BG)
        row.pack(fill="x", pady=(6, 0))
        styled_entry(row, textvariable=self.goal_var, width=10).pack(side="left")
        RoundedButton(row, "Сохранить", command=self.save_goal, bold=True).pack(side="left", padx=(10, 0))

        calc_card = Card(parent, title="Не знаешь свою норму?")
        calc_card.pack(fill="x")
        cbody = calc_card.inner

        tk.Label(
            cbody, text="Посчитаем по формуле Миффлина-Сан Жеора", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)
        ).pack(anchor="w", pady=(0, 10))

        calc_form = tk.Frame(cbody, bg=CARD_BG)
        calc_form.pack(anchor="w")

        tk.Label(calc_form, text="Пол", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=0, column=0, sticky="w", pady=3)
        self.gender_var = tk.StringVar(value="Мужской")
        ttk.Combobox(
            calc_form, textvariable=self.gender_var, values=["Мужской", "Женский"], state="readonly", width=10
        ).grid(row=0, column=1, pady=3, padx=(10, 0), sticky="w")

        tk.Label(calc_form, text="Вес (кг)", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=1, column=0, sticky="w", pady=3)
        self.weight_var = tk.StringVar()
        styled_entry(calc_form, textvariable=self.weight_var, width=10).grid(row=1, column=1, pady=3, padx=(10, 0), sticky="w")

        tk.Label(calc_form, text="Рост (см)", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=2, column=0, sticky="w", pady=3)
        self.height_var = tk.StringVar()
        styled_entry(calc_form, textvariable=self.height_var, width=10).grid(row=2, column=1, pady=3, padx=(10, 0), sticky="w")

        tk.Label(calc_form, text="Возраст", bg=CARD_BG, fg=TEXT_MUTED, font=(FONT, 9)).grid(row=3, column=0, sticky="w", pady=3)
        self.age_var = tk.StringVar()
        styled_entry(calc_form, textvariable=self.age_var, width=10).grid(row=3, column=1, pady=3, padx=(10, 0), sticky="w")

        RoundedButton(
            cbody, "Посчитать", command=self.calculate_goal,
            bg=CARD_BG, hover_bg=BORDER_SOFT, fg=TEXT, border=BORDER,
        ).pack(anchor="w", pady=(14, 0))

    # -------------------------------------------------------------- logic
    def add_meal(self):
        name = self.name_var.get().strip()
        cal_text = self.cal_var.get().strip()

        calories = float(cal_text) if cal_text else 0

        meal = {
            "date": self.current_date,
            "category": self.category_var.get(),
            "name": name,
            "calories": calories,
            "protein": float(self.protein_var.get()) if self.protein_var.get() else 0,
            "fat": float(self.fat_var.get()) if self.fat_var.get() else 0,
            "carbs": float(self.carbs_var.get()) if self.carbs_var.get() else 0,
        }
        self.meals.append(meal)
        save_json(DATA_FILE, self.meals)

        self.name_var.set("")
        self.cal_var.set("")
        self.protein_var.set("")
        self.fat_var.set("")
        self.carbs_var.set("")

        self.refresh_today_list()
        self.refresh_history_dates()

    def delete_selected_meal(self):
        selection = self.today_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        today_meals = [m for m in self.meals if m["date"] == self.current_date]
        meal_to_remove = today_meals[index]
        self.meals.remove(meal_to_remove)
        save_json(DATA_FILE, self.meals)
        self.refresh_today_listbox()

    def refresh_today_listbox(self):
        self.today_listbox.delete(0, tk.END)
        today_meals = [m for m in self.meals if m["date"] == self.current_date]
        for meal in today_meals:
            self.today_listbox.insert(
                tk.END, f"[{meal['category']}] {meal['name']} — {meal['calories']} ккал"
            )

    def refresh_summary(self):
        today_meals = [m for m in self.meals if m["date"] == self.current_date]
        total_calories = sum(meal["calories"] for meal in today_meals)
        goal = self.settings.get("daily_goal", 2000)
        remaining = goal - total_calories

        if remaining < 0:
            color, note = RED, "перебор, ну и ладно"
        elif goal > 0 and remaining < goal * 0.15:
            color, note = AMBER, "почти уложился"
        else:
            color, note = GREEN, "все норм"

        self.summary_label.config(text=f"{total_calories} / {goal} ккал")
        self.summary_note.config(text=f"осталось: {remaining} ккал — {note}", fg=color)

        fraction = (total_calories / goal) if goal else 0
        self.progress.set_value(fraction, color)

    def refresh_today_list(self):
        self.refresh_today_listbox()
        self.refresh_summary()

    def refresh_history_dates(self):
        self.history_dates_listbox.delete(0, tk.END)
        dates = sorted({m["date"] for m in self.meals}, reverse=True)
        for d in dates:
            self.history_dates_listbox.insert(tk.END, d)

    def show_history_day(self, event=None):
        selection = self.history_dates_listbox.curselection()
        if not selection:
            return
        selected_date = self.history_dates_listbox.get(selection[0])
        day_meals = [m for m in self.meals if m["date"] == selected_date]

        lines = [f"📅 {selected_date}", ""]
        total = 0
        for m in day_meals:
            lines.append(f"[{m['category']}] {m['name']} — {m['calories']} ккал")
            total += m["calories"]
        lines.append("")
        lines.append(f"Итого: {total} ккал")

        self.history_detail.config(state="normal")
        self.history_detail.delete("1.0", tk.END)
        self.history_detail.insert(tk.END, "\n".join(lines))
        self.history_detail.config(state="disabled")

    def save_goal(self):
        goal_text = self.goal_var.get().strip()
        goal = int(goal_text)
        self.settings["daily_goal"] = goal
        save_json(SETTINGS_FILE, self.settings)
        self.refresh_today_list()
        messagebox.showinfo("Готово", "Норма сохранена, погнали считать)")

    def calculate_goal(self):
        weight = float(self.weight_var.get())
        height = float(self.height_var.get())
        age = int(self.age_var.get())

        if self.gender_var.get() == "Мужской":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        goal = round(bmr * 1.2)  # коэфф. низкой активности, самый частый случай
        self.goal_var.set(str(goal))
        self.settings["daily_goal"] = goal
        save_json(SETTINGS_FILE, self.settings)
        self.refresh_today_list()
        messagebox.showinfo("Готово", f"Вот твоя норма: {goal} ккал/день")


if __name__ == "__main__":
    app = CalorieTrackerApp()
    app.mainloop()
