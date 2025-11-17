import customtkinter as ctk
import math
import random
import os
import sys
from PIL import Image as PILImage
from tkinter import *
from tkinter import scrolledtext as st  # можно удалить, если не нужен

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class Calculator:
    def format_number(self, value):
        """
        Превращает float в аккуратную строку:
        0.30000000000000004 -> 0.3
        2.0 -> 2
        """
        try:
            value = float(value)
        except (TypeError, ValueError):
            return str(value)

        if not math.isfinite(value):
            return str(value)

        # если число практически целое, показываем без дробной части
        if abs(value - round(value)) < 1e-12:
            return str(int(round(value)))

        # до 15 значащих цифр без лишних нулей
        s = f"{value:.15g}"
        return s

    def __init__(self, root):
        self.root = root
        self.root.title("Калькулятор")
        self.set_icon()

        # базовый размер
        self.width = 480
        self.height = 650

        # центрируем окно
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = (screen_h - self.height) // 2
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self.root.resizable(True, True)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # плавное появление
        self.root.attributes("-alpha", 0.0)

        # состояние
        self.expression = ""
        self.result_var = ctk.StringVar(value="0")
        self.history_list = []

        self.current_theme = "Dark"
        self.is_fullscreen = False

        self.main_frame = None
        self.randomizer_frame = None
        self.science_frame = None
        self.settings_frame = None
        self.coin_frame = None       # экран "Орёл и решка"
        self.wheel_frame = None      # экран "Колесо фортуны"

        self.angle_mode = "DEG"  # DEG / RAD
        self.mem_value = 0.0
        self.deg_button = None
        self.second_button = None
        self.second_mode = False
        self.sci_buttons = {}
        self.sci_layout_normal = {}
        self.sci_layout_second = {}

        # состояние монетки
        self.coin_flipping = False
        self.coin_result_var = None
        self.coin_label_var = None

        # состояние колеса фортуны
        self.wheel_items_text = None
        self.wheel_current_var = None
        self.wheel_result_var = None
        self.wheel_spinning = False

        self.create_calculator_ui()
        self.bind_keys()
        self.fade_in_main()

    # ---------- ИКОНКА ----------

    def set_icon(self):
        try:
            if hasattr(sys, "_MEIPASS"):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    # ---------- ПЛАВНОЕ ПОЯВЛЕНИЕ ----------

    def fade_in_main(self, step=0.05):
        alpha = self.root.attributes("-alpha")
        if alpha < 1.0:
            self.root.attributes("-alpha", min(alpha + step, 1.0))
            self.root.after(15, self.fade_in_main)
        else:
            self.root.attributes("-alpha", 1.0)

    def fade_in_window(self, window, step=0.08):
        try:
            alpha = window.attributes("-alpha")
        except Exception:
            window.attributes("-alpha", 0.0)
            alpha = 0.0
        if alpha < 1.0:
            window.attributes("-alpha", min(alpha + step, 1.0))
            window.after(15, lambda: self.fade_in_window(window))
        else:
            window.attributes("-alpha", 1.0)

    # ---------- КЛАВИАТУРА / FULLSCREEN ----------

    def bind_keys(self):
        for key in "0123456789.":
            self.root.bind(key, self.handle_key)
        for key in "+-*/":
            self.root.bind(key, self.handle_key)

        self.root.bind("<Return>", self.handle_key)
        self.root.bind("=", self.handle_key)
        self.root.bind("<BackSpace>", self.handle_backspace)
        self.root.bind("<Escape>", lambda event: self.clear())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def handle_key(self, event):
        # в других режимах клавиатора калькулятора не работает
        if (self.randomizer_frame is not None or
                self.settings_frame is not None or
                self.coin_frame is not None or
                self.wheel_frame is not None):
            return
        ch = event.char
        if ch in "0123456789.+-*/":
            self.on_button_click(ch)
        elif event.keysym in ("Return", "KP_Enter", "equal"):
            self.on_button_click("=")

    def handle_backspace(self, event=None):
        if (self.randomizer_frame is not None or
                self.settings_frame is not None or
                self.coin_frame is not None or
                self.wheel_frame is not None):
            return "break"
        if self.expression:
            self.expression = self.expression[:-1]
            self.result_var.set(self.expression if self.expression else "0")
        else:
            self.result_var.set("0")
        return "break"

    # ---------- ПРЕОБРАЗОВАНИЕ В PYTHON-ВЫРАЖЕНИЕ ----------

    def _to_python_expr(self, expr: str) -> str:
        """
        Пользователь видит:
            5^2 + 10%
        Python получает:
            5**2 + 10*0.01
        """
        if not expr:
            return ""
        safe = expr.replace('^', '**')
        safe = safe.replace('%', '*0.01')
        return safe

    def _eval_current(self) -> float:
        safe = self._to_python_expr(self.expression)
        return eval(safe)

    # ---------- ВСПОМОГАТЕЛЬНОЕ ДОБАВЛЕНИЕ ----------

    def _append(self, text):
        if self.result_var.get() == "0" and text not in ('.', ')'):
            self.expression = str(text)
        else:
            self.expression += str(text)
        self.result_var.set(self.expression)

    # ---------- УДАЛЕНИЕ ФРЕЙМОВ ----------

    def clear_frames(self):
        for name in (
            "main_frame",
            "randomizer_frame",
            "science_frame",
            "settings_frame",
            "coin_frame",
            "wheel_frame",
        ):
            frame = getattr(self, name)
            if frame is not None:
                frame.grid_forget()
                frame.destroy()
                setattr(self, name, None)

    # ---------- ОБЫЧНЫЙ КАЛЬКУЛЯТОР ----------
    def create_calculator_ui(self):
        self.clear_frames()
        self.root.title("Калькулятор")

        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # строки 0..5, чтобы кнопки были до низа
        for r in range(0, 6):
            self.main_frame.grid_rowconfigure(r, weight=1)
        for c in range(4):
            self.main_frame.grid_columnconfigure(c, weight=1)

        # верхняя панель
        top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_frame.grid(
            row=0, column=0, columnspan=4,
            sticky="nsew", padx=10, pady=10
        )

        # история (создаём, но пока не пакуем)
        history_button = ctk.CTkButton(
            top_frame,
            text="↺",
            command=self.show_history,
            width=40,
            height=40,
            font=("Arial", 24, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )

        # настройки (создаём, но пока не пакуем)
        settings_button = ctk.CTkButton(
            top_frame,
            text="⚙",
            command=self.show_settings,
            width=40,
            height=40,
            font=("Arial", 26, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )

        # ПОЛЕ ВВОДА
        self.display = ctk.CTkEntry(
            top_frame,
            textvariable=self.result_var,
            font=("Arial", 40, "bold"),
            justify='right',
            state='readonly',
            text_color=("#000000", "#FFFFFF")
        )

        # 1. сначала ставим дисплей — он занимает всю ширину снизу
        self.display.pack(side=BOTTOM, fill=X, padx=0, pady=(10, 0))

        # 2. потом в оставшемся месте сверху размещаем кнопки
        history_button.pack(side=LEFT, anchor=NW)
        settings_button.pack(side=RIGHT, anchor=NE)

        # ===== КНОПКИ КАЛЬКУЛЯТОРА =====
        blue = ('#339CFF', '#1565C0')
        gray = ('#EEEEEE', '#666666')

        buttons = [
            ('AC',   1, 0, blue),
            ('←',    1, 1, blue),
            ('√',    1, 2, blue),
            ('/',    1, 3, blue),

            ('7',    2, 0, gray),
            ('8',    2, 1, gray),
            ('9',    2, 2, gray),
            ('*',    2, 3, blue),

            ('4',    3, 0, gray),
            ('5',    3, 1, gray),
            ('6',    3, 2, gray),
            ('-',    3, 3, blue),

            ('1',    4, 0, gray),
            ('2',    4, 1, gray),
            ('3',    4, 2, gray),
            ('+',    4, 3, blue),

            ('0',    5, 0, gray, 2),
            ('.',    5, 2, gray),
            ('=',    5, 3, ('#4CAF50', '#388E3C')),
        ]

        for (text, row, col, color_tuple, *span) in buttons:
            col_span = span[0] if span else 1

            btn = ctk.CTkButton(
                self.main_frame,
                text=text,
                font=("Arial", 20, "bold"),
                fg_color=color_tuple,
                text_color=("#000000", "#FFFFFF")
            )

            def make_cmd(t=text, b=btn):
                return lambda: (self.animate_button_click(b),
                                self.on_button_click(t))

            btn.configure(command=make_cmd())
            btn.grid(
                row=row,
                column=col,
                columnspan=col_span,
                padx=5,
                pady=5,
                sticky="nsew"
            )

        # восстановить горячие клавиши после других экранов
        self.bind_keys()

    # ---------- НАУЧНЫЙ КАЛЬКУЛЯТОР ----------

    def create_science_ui(self):
        self.clear_frames()
        self.root.title("Научный калькулятор")

        self.science_frame = ctk.CTkFrame(self.root)
        self.science_frame.grid(row=0, column=0, sticky="nsew")

        self.science_frame.grid_rowconfigure(0, weight=2)
        self.science_frame.grid_rowconfigure(1, weight=5)
        self.science_frame.grid_rowconfigure(2, weight=5)
        self.science_frame.grid_columnconfigure(0, weight=1)

        # верхняя панель
        top_frame = ctk.CTkFrame(self.science_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        top_frame.grid_columnconfigure(0, weight=1)

        # отдельный фрейм только для иконок сверху
        icons_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        icons_frame.pack(side=TOP, fill="x")

        # история слева (если хочешь другой значок – просто поменяй text)
        history_button = ctk.CTkButton(
            icons_frame,
            text="↺",
            command=self.show_history,
            width=40,
            height=40,
            font=("Arial", 24, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )
        history_button.pack(side=LEFT, anchor=NW)

        # справочник – книжка справа от истории
        help_button = ctk.CTkButton(
            icons_frame,
            text="📖",
            command=self.show_science_help,
            width=40,
            height=40,
            font=("Arial", 24, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )
        help_button.pack(side=LEFT, anchor=NW, padx=(6, 0))

        # настройки справа
        settings_button = ctk.CTkButton(
            icons_frame,
            text="⚙",
            command=self.show_settings,
            width=40,
            height=40,
            font=("Arial", 26, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )
        settings_button.pack(side=RIGHT, anchor=NE)

        # ОКНО ВВОДА – как раньше, на всю ширину
        display = ctk.CTkEntry(
            top_frame,
            textvariable=self.result_var,
            font=("Arial", 40, "bold"),
            justify='right',
            state='readonly',
            text_color=("#000000", "#FFFFFF")
        )
        display.pack(side=BOTTOM, fill="x", pady=(15, 0))

        # блок функций
        sci_frame = ctk.CTkFrame(self.science_frame, fg_color="transparent")
        sci_frame.grid(row=1, column=0, sticky="nsew", padx=6)
        for r in range(5):
            sci_frame.grid_rowconfigure(r, weight=1)
        for c in range(6):
            sci_frame.grid_columnconfigure(c, weight=1)

        # блок цифр
        num_frame = ctk.CTkFrame(self.science_frame, fg_color="transparent")
        num_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(4, 8))
        for r in range(5):
            num_frame.grid_rowconfigure(r, weight=1)
        for c in range(4):
            num_frame.grid_columnconfigure(c, weight=1)

        blue = ('#339CFF', '#1565C0')
        gray = ('#EEEEEE', '#666666')
        op_gray = ('#2f2f2f', '#444444')

        # разметка функций: (row, col) -> (label, token)
        self.sci_layout_normal = {
            (0, 0): ('(', '('),
            (0, 1): (')', ')'),
            (0, 2): ('mc', 'mc'),
            (0, 3): ('m+', 'm+'),
            (0, 4): ('m-', 'm-'),
            (0, 5): ('mr', 'mr'),

            (1, 0): ('2nd', '2nd'),
            (1, 1): ('x²', 'x²'),
            (1, 2): ('x³', 'x³'),
            (1, 3): ('xʸ', 'x^y'),
            (1, 4): ('eˣ', 'e^x'),
            (1, 5): ('10ˣ', '10^x'),

            (2, 0): ('1/x', '1/x'),
            (2, 1): ('²√x', '2√x'),
            (2, 2): ('³√x', '3√x'),
            (2, 3): ('ʸ√x', 'y√x'),
            (2, 4): ('ln', 'ln'),
            (2, 5): ('log₁₀', 'log10'),

            (3, 0): ('x!', 'x!'),
            (3, 1): ('sin', 'sin'),
            (3, 2): ('cos', 'cos'),
            (3, 3): ('tg', 'tg'),
            (3, 4): ('e', 'e'),
            (3, 5): ('EE', 'EE'),

            (4, 0): ('Rand', 'Rand'),
            (4, 1): ('sh', 'sh'),
            (4, 2): ('ch', 'ch'),
            (4, 3): ('th', 'th'),
            (4, 4): ('π', 'π'),
            (4, 5): ('Deg', 'Deg'),
        }

        # второй режим
        self.sci_layout_second = dict(self.sci_layout_normal)
        # ln <-> e^x
        self.sci_layout_second[(1, 4)] = ('ln', 'ln')
        self.sci_layout_second[(2, 4)] = ('eˣ', 'e^x')
        # log <-> 10^x
        self.sci_layout_second[(1, 5)] = ('log₁₀', 'log10')
        self.sci_layout_second[(2, 5)] = ('10ˣ', '10^x')
        # тригонометрия
        self.sci_layout_second[(3, 1)] = ('sin⁻¹', 'asin')
        self.sci_layout_second[(3, 2)] = ('cos⁻¹', 'acos')
        self.sci_layout_second[(3, 3)] = ('tg⁻¹', 'atan')

        self.second_mode = False
        self.sci_buttons = {}
        self.deg_button = None
        self.second_button = None

        # создать кнопки научного блока
        for (row, col), (label, token) in self.sci_layout_normal.items():
            btn = ctk.CTkButton(
                sci_frame,
                text=label,
                font=("Arial", 16, "bold"),
                fg_color=op_gray,
                corner_radius=22,
                text_color=("#FFFFFF", "#FFFFFF")
            )

            if token == 'Deg':
                self.deg_button = btn
                btn.configure(command=lambda b=btn: self.toggle_angle_mode())
            elif token == '2nd':
                self.second_button = btn
                btn.configure(command=self.toggle_second_mode)
            else:
                def make_cmd(t=token, b=btn):
                    return lambda: (self.animate_button_click(b),
                                    self.on_button_click(t))
                btn.configure(command=make_cmd())

            btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            self.sci_buttons[(row, col)] = btn
         # восстановить горячие клавиши после других экранов
        self.bind_keys()


        # цифры
        num_buttons = [
            ('←',   0, 0, blue),
            ('AC',  0, 1, blue),
            ('%',   0, 2, blue),
            ('÷',   0, 3, blue),

            ('7',   1, 0, gray),
            ('8',   1, 1, gray),
            ('9',   1, 2, gray),
            ('×',   1, 3, blue),

            ('4',   2, 0, gray),
            ('5',   2, 1, gray),
            ('6',   2, 2, gray),
            ('-',   2, 3, blue),

            ('1',   3, 0, gray),
            ('2',   3, 1, gray),
            ('3',   3, 2, gray),
            ('+',   3, 3, blue),

            ('+/-', 4, 0, gray),
            ('0',   4, 1, gray),
            ('.',   4, 2, gray),
            ('=',   4, 3, ('#4CAF50', '#388E3C')),
        ]

        for (text, row, col, color_tuple) in num_buttons:
            btn = ctk.CTkButton(
                num_frame,
                text=text,
                font=("Arial", 20, "bold"),
                fg_color=color_tuple,
                corner_radius=22,
                text_color=("#000000", "#FFFFFF")
            )

            def make_cmd(t=text, b=btn):
                return lambda: (self.animate_button_click(b),
                                self.on_button_click(t))
            btn.configure(command=make_cmd())
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    # ---------- ПЕРЕКЛЮЧЕНИЕ 2ND ----------

    def toggle_second_mode(self):
        if not self.sci_buttons:
            return
        self.second_mode = not self.second_mode
        layout = self.sci_layout_second if self.second_mode else self.sci_layout_normal

        # подсветка 2nd
        if self.second_button:
            if self.second_mode:
                self.second_button.configure(fg_color=("#ffb74d", "#ff9800"))
            else:
                self.second_button.configure(fg_color=("#2f2f2f", "#444444"))

        for (row, col), btn in self.sci_buttons.items():
            label, token = layout[(row, col)]

            if token == 'Deg':
                btn.configure(text=label)
                continue
            if token == '2nd':
                btn.configure(text=label)
                continue

            def make_cmd(t=token, b=btn):
                return lambda: (self.animate_button_click(b),
                                self.on_button_click(t))
            btn.configure(text=label, command=make_cmd())

    # ---------- РАНДОМАЙЗЕР ----------

    def create_randomizer_ui(self):
        self.clear_frames()
        self.root.title("Рандомайзер")

        self.randomizer_frame = ctk.CTkFrame(self.root)
        self.randomizer_frame.grid(row=0, column=0, sticky="nsew")

        self.randomizer_frame.grid_rowconfigure(0, weight=1)
        self.randomizer_frame.grid_rowconfigure(1, weight=2)
        self.randomizer_frame.grid_rowconfigure(2, weight=4)
        self.randomizer_frame.grid_rowconfigure(3, weight=2)
        self.randomizer_frame.grid_columnconfigure(0, weight=1)

        top_frame = ctk.CTkFrame(self.randomizer_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)

        history_button = ctk.CTkButton(
            top_frame,
            text="↺",
            command=self.show_history,
            width=40,
            height=40,
            font=("Arial", 24, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )
        history_button.pack(side=LEFT, anchor=NW)

        settings_button = ctk.CTkButton(
            top_frame,
            text="⚙",
            command=self.show_settings,
            width=40,
            height=40,
            font=("Arial", 26, "bold"),
            corner_radius=20,
            fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"),
            text_color=("#ffffff", "#ffffff")
        )
        settings_button.pack(side=RIGHT, anchor=NE)

        title = ctk.CTkLabel(
            self.randomizer_frame,
            text="🎲 Генератор случайных чисел",
            font=("Arial", 26, "bold")
        )
        title.grid(row=1, column=0, pady=(5, 5), sticky="n")

        center_wrap = ctk.CTkFrame(self.randomizer_frame, fg_color="transparent")
        center_wrap.grid(row=1, column=0, sticky="s")
        center_wrap.grid_columnconfigure(0, weight=1)

        inputs_frame = ctk.CTkFrame(center_wrap, fg_color="transparent")
        inputs_frame.grid(row=1, column=0, padx=10, pady=10)

        self.min_var = ctk.StringVar(value="1")
        self.max_var = ctk.StringVar(value="100")

        label_font = ("Arial", 18)
        entry_font = ("Arial", 22)

        ctk.CTkLabel(inputs_frame, text="От:", font=label_font).grid(
            row=0, column=0, padx=5, pady=10, sticky="e"
        )
        ctk.CTkEntry(
            inputs_frame,
            textvariable=self.min_var,
            font=entry_font,
            width=140,
            height=50
        ).grid(row=0, column=1, padx=5, pady=10)

        ctk.CTkLabel(inputs_frame, text="До:", font=label_font).grid(
            row=0, column=2, padx=5, pady=10, sticky="e"
        )
        ctk.CTkEntry(
            inputs_frame,
            textvariable=self.max_var,
            font=entry_font,
            width=140,
            height=50
        ).grid(row=0, column=3, padx=5, pady=10)

        self.random_result = ctk.StringVar(value="—")
        result_label = ctk.CTkLabel(
            self.randomizer_frame,
            textvariable=self.random_result,
            font=("Arial", 64, "bold")
        )
        result_label.grid(row=2, column=0, pady=10, padx=20, sticky="n")

        bottom_frame = ctk.CTkFrame(self.randomizer_frame, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, pady=(0, 20), padx=40, sticky="n")
        bottom_frame.grid_columnconfigure(0, weight=1)

        generate_btn = ctk.CTkButton(
            bottom_frame,
            text="Сгенерировать",
            fg_color=('#339CFF', '#1565C0'),
            font=("Arial", 22, "bold"),
            height=60,
            text_color=("#FFFFFF", "#FFFFFF"),
            command=self.generate_random
        )
        generate_btn.grid(row=0, column=0, sticky="nsew")

    def generate_random(self):
        try:
            min_val = int(self.min_var.get())
            max_val = int(self.max_var.get())
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            value = random.randint(min_val, max_val)
            self.random_result.set(str(value))
        except Exception:
            self.random_result.set("Ошибка")

    # ---------- ОРЁЛ И РЕШКА ----------

    def create_coin_ui(self):
        self.clear_frames()
        self.root.title("Орёл и решка")

        self.coin_frame = ctk.CTkFrame(self.root)
        self.coin_frame.grid(row=0, column=0, sticky="nsew")

        for r in range(5):
            self.coin_frame.grid_rowconfigure(r, weight=1)
        self.coin_frame.grid_columnconfigure(0, weight=1)

        # верхняя панель
        top_frame = ctk.CTkFrame(self.coin_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))

        ctk.CTkButton(
            top_frame, text="↺", command=self.show_history,
            width=40, height=40, font=("Arial", 24, "bold"),
            corner_radius=20, fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"), text_color="#ffffff"
        ).pack(side=LEFT)

        ctk.CTkButton(
            top_frame, text="⚙", command=self.show_settings,
            width=40, height=40, font=("Arial", 26, "bold"),
            corner_radius=20, fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"), text_color="#ffffff"
        ).pack(side=RIGHT)

        ctk.CTkLabel(
            self.coin_frame, text="🪙 Орёл и решка",
            font=("Arial", 28, "bold")
        ).grid(row=1, column=0, pady=5)

        # Canvas
        bg = self.coin_frame._fg_color[1] if ctk.get_appearance_mode() == "Dark" else \
             self.coin_frame._fg_color[0]

        self.coin_canvas = Canvas(
            self.coin_frame,
            width=380,
            height=380,
            bg=bg,
            highlightthickness=0,
        )
        self.coin_canvas.grid(row=2, column=0, pady=10)
        self.coin_canvas.bind("<Configure>", lambda e: self.draw_coin())

        # состояние монеты
        self.coin_side = "—"
        self.coin_scale_x = 1.0
        self.coin_scale_y = 1.0
        self.coin_shadow_scale = 1.0
        self.coin_anim_step = 0
        self.coin_flipping = False
        self.coin_theta = 0.0  # угол для прыжка / эффектов

        self.coin_result_var = ctk.StringVar(value="Нажми «Подбросить»")
        ctk.CTkLabel(
            self.coin_frame, textvariable=self.coin_result_var,
            font=("Arial", 20)
        ).grid(row=3, column=0)

        bottom = ctk.CTkFrame(self.coin_frame, fg_color="transparent")
        bottom.grid(row=4, column=0, pady=20, padx=40, sticky="nsew")
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            bottom, text="Подбросить",
            fg_color=('#339CFF', '#1565C0'),
            font=("Arial", 22, "bold"),
            height=60, text_color="#FFFFFF",
            command=self.start_coin_flip
        ).grid(row=0, column=0, sticky="nsew")

        # пробел и Enter тоже крутят монету
        self.root.bind("<space>", self._coin_key_flip)
        self.root.bind("<Return>", self._coin_key_flip)

        self.draw_coin()

    def _coin_key_flip(self, event):
        if self.coin_frame is not None and not self.coin_flipping:
            self.start_coin_flip()
            return "break"

    def draw_coin(self):
        """Рисует монетку с 3D-эффектом и 'выгравированным' текстом."""
        if not hasattr(self, "coin_canvas") or self.coin_canvas is None:
            return

        self.coin_canvas.delete("all")

        w = self.coin_canvas.winfo_width()
        h = self.coin_canvas.winfo_height()
        if w < 20 or h < 20:
            return

        cx = w // 2
        cy = h // 2

        # вертикальный "прыжок" монеты
        jump_offset = int(18 * math.sin(self.coin_theta * 0.5))
        cy = cy - jump_offset

        r = int(min(w, h) * 0.35)
        if r <= 0:
            return

        sx = self.coin_scale_x
        sy = self.coin_scale_y
        shadow_scale = self.coin_shadow_scale

        # тень
        shadow_r = int(r * 0.9 * shadow_scale)
        self.coin_canvas.create_oval(
            cx - shadow_r, cy + r + 5,
            cx + shadow_r, cy + r + 25,
            fill="#202020", outline=""
        )

        # основная монета
        self.coin_canvas.create_oval(
            cx - r * sx, cy - r * sy,
            cx + r * sx, cy + r * sy,
            fill="#f5d28a", outline="#c9a350", width=4
        )

        # внутреннее кольцо
        self.coin_canvas.create_oval(
            cx - r * 0.78 * sx, cy - r * 0.78 * sy,
            cx + r * 0.78 * sx, cy + r * 0.78 * sy,
            outline="#e8c070", width=2
        )

        # "блик" сверху слева
        highlight_r_x = r * 0.55 * sx
        highlight_r_y = r * 0.35 * sy
        self.coin_canvas.create_oval(
            cx - highlight_r_x * 0.9,
            cy - highlight_r_y * 1.3,
            cx + highlight_r_x * 0.2,
            cy - highlight_r_y * 0.3,
            fill="#ffe8a8", outline="#f5d28a"
        )

        # лёгкое затемнение снизу справа
        self.coin_canvas.create_arc(
            cx - r * sx, cy - r * sy,
            cx + r * sx, cy + r * sy,
            start=-40, extent=90,
            style="arc",
            outline="#b18434",
            width=4
        )

        # лёгкий объём внутри
        self.coin_canvas.create_oval(
            cx - r * 0.4 * sx, cy - r * 0.4 * sy,
            cx + r * 0.4 * sx, cy + r * 0.4 * sy,
            outline="#d1aa5a", width=2
        )

        # ---- ВЫГРАВИРОВАННЫЙ ТЕКСТ ----
        side_text = self.coin_side if self.coin_side else "—"

        # размер шрифта меняется вместе с "толщиной" монеты
        font_size = int(r * 0.45 * sy)
        if font_size < 8:
            font_size = 8

        # тень текста (как углубление) — сверху слева
        self.coin_canvas.create_text(
            cx - 2, cy - 2,
            text=side_text,
            fill="#8a6420",
            font=("Arial", font_size, "bold")
        )

        # светлый кант снизу справа
        self.coin_canvas.create_text(
            cx + 2, cy + 2,
            text=side_text,
            fill="#ffe6a0",
            font=("Arial", font_size, "bold")
        )

        # основной текст
        self.coin_canvas.create_text(
            cx, cy,
            text=side_text,
            fill="#3a2b10",
            font=("Arial", font_size, "bold")
        )

    def start_coin_flip(self):
        if self.coin_flipping:
            return

        self.coin_flipping = True
        self.coin_result_var.set("Крутим монетку...")

        # настройки кручения: много быстрых переворотов
        self.coin_anim_step = 0
        self.coin_total_steps = 130
        self.coin_max_flips = random.randint(20, 40)
        self.coin_final_side = random.choice(["Орёл", "Решка"])

        self._coin_animation()

    def _coin_animation(self):
        step = self.coin_anim_step
        total = self.coin_total_steps

        t = step / total
        ease = 1 - (1 - t) ** 3  # плавное замедление

        # угол для вращения
        theta = ease * self.coin_max_flips * math.pi
        self.coin_theta = theta

        # 3D-плющение по Y и небольшой разброс по X
        self.coin_scale_y = abs(math.cos(theta))              # "ребро" монеты
        self.coin_scale_x = 1.0 + 0.35 * (math.sin(theta) ** 2)
        self.coin_shadow_scale = 1.0 + 0.5 * (math.sin(theta) ** 2)

        # пока крутится — стороны меняются
        if step < total - 1:
            side_index = int(theta / math.pi) % 2
            self.coin_side = "Орёл" if side_index == 0 else "Решка"
        else:
            self.coin_side = self.coin_final_side

        self.draw_coin()

        if step < total:
            self.coin_anim_step += 1
            delay = 3 + int(50 * t)
            self.root.after(delay, self._coin_animation)
        else:
            self.coin_flipping = False
            self.coin_result_var.set(f"Выпало: {self.coin_side}")
            self.history_list.append(f"Монетка: {self.coin_side}")

    # ---------- КОЛЕСО ФОРТУНЫ ----------

    def create_wheel_ui(self):
        self.clear_frames()
        self.root.title("Колесо фортуны")

        self.wheel_frame = ctk.CTkFrame(self.root)
        self.wheel_frame.grid(row=0, column=0, sticky="nsew")

        self.wheel_frame.grid_rowconfigure(0, weight=0)
        self.wheel_frame.grid_rowconfigure(1, weight=0)
        self.wheel_frame.grid_rowconfigure(2, weight=1)
        self.wheel_frame.grid_rowconfigure(3, weight=0)
        self.wheel_frame.grid_columnconfigure(0, weight=1)

        top_frame = ctk.CTkFrame(self.wheel_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            top_frame, text="↺", command=self.show_history,
            width=40, height=40, font=("Arial", 24, "bold"),
            corner_radius=20, fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"), text_color="#ffffff"
        ).pack(side=LEFT, anchor=NW)

        ctk.CTkButton(
            top_frame, text="⚙", command=self.show_settings,
            width=40, height=40, font=("Arial", 26, "bold"),
            corner_radius=20, fg_color=("#333333", "#222222"),
            hover_color=("#4c4c4c", "#3b3b3b"), text_color="#ffffff"
        ).pack(side=RIGHT, anchor=NE)

        ctk.CTkLabel(
            self.wheel_frame, text="🎡 Колесо фортуны",
            font=("Arial", 28, "bold")
        ).grid(row=1, column=0, pady=(5, 5), sticky="n")

        self.wheel_canvas = Canvas(
            self.wheel_frame,
            bg="#222222",
            highlightthickness=0
        )
        self.wheel_canvas.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        self.wheel_canvas.bind("<Configure>", lambda e: self.draw_wheel())

        self.wheel_angle = 0.0
        self.wheel_spinning = False
        self.wheel_sectors = []
        self.wheel_colors = []

        bottom = ctk.CTkFrame(self.wheel_frame, fg_color="transparent")
        bottom.grid(row=3, column=0, pady=(5, 15), padx=20, sticky="nsew")
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bottom,
            text="Сектора (через пробел или запятую):",
            font=("Arial", 16)
        ).grid(row=0, column=0, sticky="w")

        self.wheel_entry = ctk.CTkEntry(bottom, font=("Arial", 14), height=40)
        self.wheel_entry.grid(row=1, column=0, sticky="ew", pady=6)
        self.wheel_entry.insert(0, "Да, Нет, Может быть, Позже, Сейчас")

        self.wheel_result_var = ctk.StringVar(
            value="Нажми «Крутить» (кнопка или Enter)"
        )
        ctk.CTkLabel(
            bottom,
            textvariable=self.wheel_result_var,
            font=("Arial", 16),
            wraplength=360,
            justify="center"
        ).grid(row=2, column=0, pady=5)

        self.wheel_spin_button = ctk.CTkButton(
            bottom, text="Крутить",
            fg_color=('#339CFF', '#1565C0'),
            font=("Arial", 22, "bold"),
            height=60, text_color="#FFFFFF",
            command=self.start_wheel_spin
        )
        self.wheel_spin_button.grid(row=3, column=0, sticky="nsew")

        # теперь только Enter крутит колесо (без пробела)
        self.root.bind("<Return>", self._wheel_key_spin)

        self.wheel_sectors = self.parse_wheel_sectors()
        self.draw_wheel()

    def _wheel_key_spin(self, event):
        if self.wheel_frame is not None and not self.wheel_spinning:
            self.start_wheel_spin()
            return "break"

    def parse_wheel_sectors(self):
        txt = self.wheel_entry.get().strip()

        if not txt:
            sectors = ["Да", "Нет", "Может быть", "Позже", "Сейчас"]
        else:
            if "," in txt:
                parts = [p.strip() for p in txt.split(",") if p.strip()]
            else:
                parts = [p for p in txt.split() if p]
            sectors = parts or ["Да", "Нет", "Может быть", "Позже", "Сейчас"]

        palette = [
            "#4E79A7", "#59A14F", "#9C755F", "#F28E2B",
            "#EDC948", "#B07AA1", "#76B7B2", "#FF9DA7"
        ]

        self.wheel_colors = [palette[i % len(palette)] for i in range(len(sectors))]
        return sectors

    def draw_wheel(self):
        if not self.wheel_canvas.winfo_width() or not self.wheel_canvas.winfo_height():
            return

        self.wheel_canvas.delete("all")

        w = self.wheel_canvas.winfo_width()
        h = self.wheel_canvas.winfo_height()

        r = int(min(w, h) * 0.4)
        cx = w // 2
        cy = h // 2 + 10

        sectors = self.wheel_sectors or ["—"]
        n = len(sectors)
        angle_per = 360 / n

        for i, name in enumerate(sectors):
            start = self.wheel_angle + angle_per * i
            color = self.wheel_colors[i]

            self.wheel_canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=start, extent=angle_per,
                fill=color, outline="#222222", width=2
            )

            ang = math.radians(start + angle_per / 2)
            tx = cx + r * 0.6 * math.cos(ang)
            ty = cy - r * 0.6 * math.sin(ang)

            self.wheel_canvas.create_text(
                tx, ty, text=name,
                fill="white", font=("Arial", 10, "bold")
            )

        pointer_top_y = cy - r - 30
        pointer_tip_y = pointer_top_y + 25
        if pointer_top_y < 5:
            pointer_top_y = 5
            pointer_tip_y = 30

        self.wheel_canvas.create_polygon(
            cx - 12, pointer_top_y,
            cx + 12, pointer_top_y,
            cx,      pointer_tip_y,
            fill="red", outline="black", width=1
        )

    def start_wheel_spin(self):
        if self.wheel_spinning:
            return

        self.wheel_sectors = self.parse_wheel_sectors()
        if len(self.wheel_sectors) < 2:
            self.wheel_result_var.set("Нужно минимум 2 сектора 🙃")
            return

        self.wheel_spinning = True
        self.wheel_result_var.set("Крутим колесо...")

        self._start_angle = self.wheel_angle
        self._total_angle = random.randint(1080, 1800)
        self._steps = 200

        self._spin_step(0)

    def _spin_step(self, step):
        t = step / self._steps
        ease = 1 - (1 - t) ** 3

        self.wheel_angle = self._start_angle + self._total_angle * ease
        self.draw_wheel()

        if step < self._steps:
            delay = int(10 + 40 * (t ** 2))
            self.root.after(delay, lambda: self._spin_step(step + 1))
        else:
            sectors = self.wheel_sectors
            n = len(sectors)
            angle_per = 360 / n

            cur = (self.wheel_angle % 360 + 360) % 360
            top = (90 - cur + 360) % 360
            idx = int(top // angle_per) % n
            winner = sectors[idx]

            self.wheel_result_var.set(f"Выпало: {winner}")
            self.history_list.append(f"Колесо фортуны: {winner}")
            self.wheel_spinning = False

    # ---------- АНИМАЦИЯ КНОПОК ----------

    def animate_button_click(self, button):
        try:
            orig = button.cget("fg_color")
        except Exception:
            orig = None
        if orig:
            highlight = ("#dcdcdc", "#555555")
            button.configure(fg_color=highlight)
            self.root.after(90, lambda: button.configure(fg_color=orig))

    # ---------- ЛОГИКА ----------

    def on_button_click(self, char):
        if (self.randomizer_frame is not None or
                self.settings_frame is not None or
                self.coin_frame is not None or
                self.wheel_frame is not None):
            return

        if char == '÷':
            char = '/'
        elif char == '×':
            char = '*'

        if char in ('=',):
            self.calculate()
        elif char in ('C', 'AC'):
            self.clear()
        elif char == '←':
            self.handle_backspace()
        elif char == '+/-':
            try:
                if not self.expression:
                    return
                val = -float(self._eval_current())
                res_str = self.format_number(val)
                self.expression = res_str
                self.result_var.set(res_str)
            except Exception:
                self.result_var.set("Ошибка")
                self.expression = ""
        elif char == 'x^y':
            self._append('^')
        elif char in ('mc', 'm+', 'm-', 'mr'):
            self.memory_operation(char)
        elif char == 'Rand':
            res = random.random()
            res_str = self.format_number(res)
            self.history_list.append(f"Rand = {res_str}")
            self.result_var.set(res_str)
            self.expression = res_str
        elif char == 'EE':
            self._append('e')
        elif char == 'π':
            self._append(str(math.pi))
        elif char == 'e':
            self._append(str(math.e))
        elif char == '2nd':
            self.toggle_second_mode()
        elif char in (
            '√', '%', 'sin', 'cos', 'tan', 'tg',
            'x²', 'x³', 'e^x', '10^x', '1/x',
            '2√x', '3√x', 'y√x', 'ln', 'log10',
            'x!', 'sh', 'ch', 'th',
            'asin', 'acos', 'atan'
        ):
            self.apply_math_function(char)
        else:
            self._append(char)

    def calculate(self):
        try:
            if not self.expression:
                return
            safe = self._to_python_expr(self.expression)
            result = eval(safe)
            result_str = self.format_number(result)
            self.history_list.append(f"{self.expression} = {result_str}")
            self.result_var.set(result_str)
            self.expression = result_str
        except ZeroDivisionError:
            self.result_var.set("Деление на ноль")
            self.expression = ""
        except SyntaxError:
            self.result_var.set("Ошибка синтаксиса")
            self.expression = ""
        except Exception:
            self.result_var.set("Ошибка")
            self.expression = ""


    def angle_to_radians(self, val):
        if self.angle_mode == "DEG":
            return math.radians(val)
        return val

    def radians_to_angle(self, val):
        if self.angle_mode == "DEG":
            return math.degrees(val)
        return val

    def apply_math_function(self, func):
        try:
            if not self.expression:
                return
            val = float(self._eval_current())

            if func == '√' or func == '2√x':
                if val < 0:
                    raise ValueError("Корень из отрицательного числа")
                res = math.sqrt(val)

            elif func == '3√x':
                res = math.copysign(abs(val) ** (1.0 / 3.0), val)

            elif func == 'y√x':
                dialog = ctk.CTkInputDialog(
                    text="Степень корня (y):",
                    title="y√x"
                )
                y_str = dialog.get_input()
                if y_str is None or y_str.strip() == "":
                    return
                y_val = float(y_str)
                if y_val == 0:
                    raise ZeroDivisionError
                if val < 0 and int(y_val) % 2 == 0:
                    raise ValueError("Корень чётной степени из отрицательного числа")
                res = math.copysign(abs(val) ** (1.0 / y_val), val)

            elif func == '%':
                res = val / 100

            elif func in ('sin',):
                a = self.angle_to_radians(val)
                res = math.sin(a)

            elif func in ('cos',):
                a = self.angle_to_radians(val)
                res = math.cos(a)

            elif func in ('tan', 'tg'):
                a = self.angle_to_radians(val)
                res = math.tan(a)

            elif func == 'asin':
                res = self.radians_to_angle(math.asin(val))

            elif func == 'acos':
                res = self.radians_to_angle(math.acos(val))

            elif func == 'atan':
                res = self.radians_to_angle(math.atan(val))

            elif func == 'sh':
                a = self.angle_to_radians(val)
                res = math.sinh(a)

            elif func == 'ch':
                a = self.angle_to_radians(val)
                res = math.cosh(a)

            elif func == 'th':
                a = self.angle_to_radians(val)
                res = math.tanh(a)

            elif func == 'x²':
                res = val * val

            elif func == 'x³':
                res = val * val * val

            elif func == 'e^x':
                res = math.exp(val)

            elif func == '10^x':
                res = 10 ** val

            elif func == '1/x':
                if val == 0:
                    raise ZeroDivisionError
                res = 1.0 / val

            elif func == 'ln':
                if val <= 0:
                    raise ValueError("ln(x) при x>0")
                res = math.log(val)

            elif func == 'log10':
                if val <= 0:
                    raise ValueError("log(x) при x>0")
                res = math.log10(val)

            elif func == 'x!':
                if val < 0 or int(val) != val:
                    raise ValueError("Факториал целого ≥0")
                res = math.factorial(int(val))

            else:
                return

            res_str = self.format_number(res)
            self.history_list.append(f"{func}({self.expression}) = {res_str}")
            self.result_var.set(res_str)
            self.expression = res_str

        except ValueError as e:
            self.result_var.set(str(e))
            self.expression = ""
        except ZeroDivisionError:
            self.result_var.set("Деление на ноль")
            self.expression = ""
        except Exception:
            self.result_var.set("Ошибка функции")
            self.expression = ""

    def clear(self):
        self.expression = ""
        self.result_var.set("0")

    # ---------- ПАМЯТЬ ----------

    def memory_operation(self, op):
        try:
            if op == 'mc':
                self.mem_value = 0.0
            elif op in ('m+', 'm-'):
                if not self.expression:
                    return
                val = float(self._eval_current())
                if op == 'm+':
                    self.mem_value += val
                else:
                    self.mem_value -= val
            elif op == 'mr':
                self.expression = self.format_number(self.mem_value)
                self.result_var.set(self.expression)
        except Exception:
            pass

    # ---------- ИСТОРИЯ ----------

    def show_history(self):
        if self.settings_frame is not None:
            return

        self.root.update_idletasks()
        w, h = 300, 400
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2

        history_window = ctk.CTkToplevel(self.root)
        history_window.title("История операций")
        history_window.geometry(f"{w}x{h}+{x}+{y}")
        history_window.grab_set()
        history_window.attributes("-alpha", 0.0)
        self.fade_in_window(history_window)

        bg = history_window._fg_color[1] if ctk.get_appearance_mode() == "Dark" else history_window._fg_color[0]
        fg = '#FFFFFF' if ctk.get_appearance_mode() == "Dark" else '#000000'

        text = Text(
            history_window,
            bg=bg,
            fg=fg,
            font=("Arial", 12),
            bd=0,
            highlightthickness=0
        )
        text.pack(expand=True, fill='both')

        for op in self.history_list:
            text.insert(END, op + "\n")

        text.configure(state='disabled')

    # ---------- КРАСИВЫЙ СПРАВОЧНИК ----------

    def show_science_help(self):
        self.root.update_idletasks()
        w, h = 460, 540
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2

        help_window = ctk.CTkToplevel(self.root)
        help_window.title("Справочник научного калькулятора")
        help_window.geometry(f"{w}x{h}+{x}+{y}")
        help_window.grab_set()
        help_window.attributes("-alpha", 0.0)
        self.fade_in_window(help_window)

        # заголовок
        title = ctk.CTkLabel(
            help_window,
            text="📖 Справочник функций",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=(10, 0))

        subtitle = ctk.CTkLabel(
            help_window,
            text="Кратко, что делает каждая кнопка научного калькулятора",
            font=("Arial", 12),
            text_color="#AAAAAA"
        )
        subtitle.pack(pady=(0, 8))

        # текстовое поле с прокруткой
        box = ctk.CTkTextbox(
            help_window,
            width=w - 30,
            height=h - 80,
            font=("Arial", 12),
            wrap="word"
        )
        box.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        info = (
            "──────── 1. Скобки и память ────────\n"
            "( , )  – группировка частей выражения.\n"
            "mc     – очистить память (обнулить M).\n"
            "m+     – добавить текущее значение к памяти.\n"
            "m-     – вычесть текущее значение из памяти.\n"
            "mr     – подставить значение из памяти на экран.\n\n"

            "──────── 2. Режимы ────────\n"
            "2nd    – переключает второй набор функций:\n"
            "         • sin, cos, tg → sin⁻¹, cos⁻¹, tg⁻¹\n"
            "         • eˣ ↔ ln ; 10ˣ ↔ log₁₀\n"
            "Deg    – переключение градусов/радиан:\n"
            "         • Deg – ввод и вывод в градусах\n"
            "         • Rad – ввод и вывод в радианах\n\n"

            "──────── 3. Степени и корни ────────\n"
            "x²     – квадрат числа.\n"
            "x³     – куб числа.\n"
            "xʸ     – возведение x в степень y (x^y).\n"
            "1/x    – обратное число (1 / x).\n"
            "²√x    – квадратный корень.\n"
            "³√x    – кубический корень.\n"
            "ʸ√x    – корень степени y (программа спросит y).\n"
            "x!     – факториал (целое число ≥ 0).\n\n"

            "──────── 4. Экспоненты и логарифмы ────────\n"
            "eˣ     – экспонента e^x.\n"
            "10ˣ    – десятичная степень 10^x.\n"
            "ln     – натуральный логарифм (основание e).\n"
            "log₁₀  – логарифм по основанию 10.\n"
            "EE     – экспоненциальная форма записи\n"
            "         (например 3 EE 4 = 3 * 10^4).\n\n"

            "──────── 5. Константы ────────\n"
            "e      – число Эйлера ≈ 2.71828.\n"
            "π      – число пи ≈ 3.14159.\n\n"

            "──────── 6. Тригонометрия ────────\n"
            "sin    – синус угла.\n"
            "cos    – косинус угла.\n"
            "tg     – тангенс угла.\n"
            "sin⁻¹  – арксинус (обратный sin).\n"
            "cos⁻¹  – арккосинус (обратный cos).\n"
            "tg⁻¹   – арктангенс (обратный tg).\n"
            "⚠ Угол считается в градусах или радианах\n"
            "   в зависимости от режима Deg/Rad.\n\n"

            "──────── 7. Гиперболические функции ────────\n"
            "sh     – гиперболический синус sinh(x).\n"
            "ch     – гиперболический косинус cosh(x).\n"
            "th     – гиперболический тангенс tanh(x).\n\n"

            "──────── 8. Прочее ────────\n"
            "Rand   – случайное число от 0 до 1.\n"
            "%      – перевести значение в проценты (деление на 100).\n"
            "+/-    – смена знака текущего числа.\n"
        )

        box.insert("1.0", info)
        box.configure(state="disabled")

    # ---------- НАСТРОЙКИ ----------

    def toggle_angle_mode(self):
        if self.angle_mode == "DEG":
            self.angle_mode = "RAD"
            if self.deg_button:
                self.deg_button.configure(text="Rad")
        else:
            self.angle_mode = "DEG"
            if self.deg_button:
                self.deg_button.configure(text="Deg")

    def show_settings(self):
        self.clear_frames()
        self.root.title("Настройки")

        self.settings_frame = ctk.CTkFrame(self.root)
        self.settings_frame.grid(row=0, column=0, sticky="nsew")

        for r in range(6):
            self.settings_frame.grid_rowconfigure(r, weight=1)
        self.settings_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.settings_frame,
            text="Настройки",
            font=("Arial", 28, "bold")
        )
        title.grid(row=0, column=0, pady=(20, 10))

        theme_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        theme_frame.grid(row=1, column=0, pady=10)
        ctk.CTkLabel(theme_frame, text="Тема оформления:", font=("Arial", 16)).pack(pady=5)
        ctk.CTkButton(theme_frame, text="Светлая", width=140,
                      command=lambda: self.switch_theme("Light")).pack(pady=3)
        ctk.CTkButton(theme_frame, text="Тёмная", width=140,
                      command=lambda: self.switch_theme("Dark")).pack(pady=3)

        mode_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        mode_frame.grid(row=2, column=0, pady=10)
        ctk.CTkLabel(mode_frame, text="Режим работы:", font=("Arial", 16)).pack(pady=5)
        ctk.CTkButton(
            mode_frame,
            text="Обычный калькулятор",
            width=200,
            command=self.create_calculator_ui
        ).pack(pady=3)
        ctk.CTkButton(
            mode_frame,
            text="Научный калькулятор",
            width=200,
            command=self.create_science_ui
        ).pack(pady=3)
        ctk.CTkButton(
            mode_frame,
            text="🎲 Рандомайзер",
            width=200,
            command=self.create_randomizer_ui
        ).pack(pady=3)
        ctk.CTkButton(
            mode_frame,
            text="🪙 Орёл и решка",
            width=200,
            command=self.create_coin_ui
        ).pack(pady=3)
        ctk.CTkButton(
            mode_frame,
            text="🎡 Колесо фортуны",
            width=200,
            command=self.create_wheel_ui
        ).pack(pady=3)

        # --- Разработчики + донат ---
        dev_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        dev_frame.grid(row=5, column=0, pady=15)
        dev_frame.grid_columnconfigure(0, weight=1)

        dev_label = ctk.CTkLabel(
            dev_frame,
            text="Разработчики:\nКучаев Влад и Шурупов Олег",
            font=("Arial", 12, "italic"),
            text_color="#AAAAAA",
            justify="center"
        )
        dev_label.grid(row=0, column=0, pady=(0, 8), sticky="n")

        def open_donate(event=None):
            import webbrowser
            webbrowser.open("https://dalink.to/kuchaev_vlad")

        donate_label = ctk.CTkLabel(
            dev_frame,
            text="💸 Нравится калькулятор? Поддержи разработчиков 💸",
            font=("Arial", 15, "underline"),
            text_color="#3FA9F5",
            cursor="hand2",
            justify="center",
        )

        donate_label.grid(row=1, column=0, sticky="n")

        try:
            if hasattr(sys, "_MEIPASS"):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            qr_path = os.path.join(base_path, "donate_qr.png")

            qr_img_pil = PILImage.open(qr_path)
            qr_img = ctk.CTkImage(
                light_image=qr_img_pil,
                dark_image=qr_img_pil,
                size=(140, 140)
            )

            qr_label = ctk.CTkLabel(dev_frame, image=qr_img, text="")
            qr_label.image = qr_img
            qr_label.grid(row=2, column=0, pady=(10, 0), sticky="n")
        except Exception as e:
            print("Ошибка загрузки QR-кода:", e)

        def on_hover(event):
            donate_label.configure(text_color="#6FC4FF")

        def on_leave(event):
            donate_label.configure(text_color="#3FA9F5")

        donate_label.bind("<Enter>", on_hover)
        donate_label.bind("<Leave>", on_leave)
        donate_label.bind("<Button-1>", open_donate)

    def switch_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self.current_theme = mode
        self.root.update_idletasks()


if __name__ == "__main__":
    root = ctk.CTk()
    app = Calculator(root)
    root.mainloop()
