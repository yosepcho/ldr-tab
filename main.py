
# -*- coding: utf-8 -*-
"""
LDR Brachytherapy Template Viewer  (Kivy port of plot.py)
--------------------------------------------------------
- read-only + edit mode (retraction / remove / extra needle)
- landscape, 1920x1200 tablet target
"""

import os
import sys

from kivy.config import Config

# PC preview window (tablet 1920x1200 ratio)
if sys.platform.startswith("win") or sys.platform.startswith("linux") \
        or sys.platform == "darwin":
    Config.set("graphics", "width", "1600")
    Config.set("graphics", "height", "1000")

from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import ListProperty, BooleanProperty
from kivy.metrics import dp, sp

# ---------------------------------------------------------------- app modules
import filesource
from filesource import get_files, list_patient_files, label_for, parse_filename
from popups import choose_option, choose_from_list, info

from core.read_txt import load_patient_path
from core.numbering import assign_display_numbers
from core.asymmetry import find_unpaired, asymmetry_text
from core.edit_mode import (
    add_manual_needle,
    find_needle_at,
    find_extra_needle_at,
    get_next_real_needle,
    get_retraction_choices,
    get_extra_needles,
    count_extra_at,
    set_retraction,
)


# ================================================================= constants
EDIT_MODE = True

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
TEMPLATE_PNG = os.path.join(ASSET_DIR, "Template.png")

NOP_BASE = 36
NOP_STEP = 5
NOP_BASE_VAL = 8

IMG_W = 767
IMG_H = 636

# --- plot.py coordinates (identical)
X_A = 75
X_G = 738
Y_1 = 566
Y_6 = 14

COLS = ["A", "a", "B", "b", "C", "c", "D", "d", "E", "e", "F", "f", "G"]

FULL_ROWS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]

# ax_img.set_ylim(height + 200, Y_TOP - 30)
V_BOTTOM = IMG_H + 20           # 836

HOLE_R = 20                     # Circle(radius=20) in plot.py
HIT_R = 40                      # finger-friendly hit radius (image px)

# matplotlib pt -> image px  (dpi100 / axes scale 1.369)  ~= 1.0
FONT_SCALE = 1.0

###### circle label offsets
OFF_CENTER   = (  0,   0)   # 원 안 중앙 : actual seeds
OFF_REAL     = (-28, -23)   # 좌상단 : real number       (검정)
OFF_MULTI    = (-55, -23)   # 좌상단 : "1,2" 합쳐진 번호  (검정)
OFF_3MULTI    = (-75, -23)   # 좌상단 : "1,2,3" 합쳐진 번호  (검정)
OFF_DISPLAY  = (-28,  10)   # 좌하단 : 4D number         (파랑)
OFF_EXPECTED = ( 11, -23)   # 우상단 : expected seeds    (빨강)

LBL_PT        = 22          # 번호 폰트 (pt)
LBL_PT_CENTER = 23          # 원 안 seed 수 폰트

# --- colors
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
BLUE = (0, 0, 1, 1)
RED = (1, 0, 0, 1)
GRAY = (0.55, 0.55, 0.55, 1)
ORANGE = (1.0, 0.55, 0.0, 1)
HL_BG = (1.0, 0.949, 0.8, 1)        # #FFF2CC
GRID = (0.75, 0.75, 0.75, 1)
HEAD_BG = (0.90, 0.90, 0.90, 1)
PANEL_BG = (0.97, 0.97, 0.97, 1)

CHK_ON  = "[V]"
CHK_OFF = "[ ]"

EXTRA_STOCK = {2: 2, 3: 2}

# ================================================================= legend
LEGEND_TEXT = (
    "-0.5  ->  1    2.5  ->  7\n"
    "  0.5  ->  3    3.5  ->  9\n"
    "  1.5  ->  5    4.5  ->  11"
)

LEGEND_W = dp(200)
LEGEND_H = dp(100)
LEGEND_FS = sp(18)
LEGEND_MARGIN = dp(3)

# ================================================================= dose box
DOSE_W = dp(300)
DOSE_H = dp(120)
DOSE_FS = sp(15)



class LegendBox(Label):
    """템플릿 우측 상단 고정 안내 박스 (확대/축소 영향 없음)."""

    def __init__(self, **kw):
        super().__init__(
            text=LEGEND_TEXT,
            color=BLACK,
            bold=True,
            font_size=LEGEND_FS,
            halign="left",
            valign="middle",
            size_hint=(None, None),
            size=(LEGEND_W, LEGEND_H),
            **kw
        )

        with self.canvas.before:
            Color(1, 1, 1, 0.92)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*BLACK)
            self._ln = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=1.2)

        self.bind(pos=self._sync, size=self._sync)
        self._sync()

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ln.rectangle = (self.x, self.y, self.width, self.height)
        self.text_size = (self.width - dp(16), self.height)

# ================================================================= dose box

class ValueBtn(ButtonBehavior, Label):
    """'#' 자리 — 누르면 숫자 입력."""

    def __init__(self, **kw):
        kw.setdefault("width", dp(70))
        super().__init__(
            text="-", color=BLUE, bold=True, font_size=DOSE_FS,
            halign="center", valign="middle",
            size_hint=(None, 1), **kw)

        with self.canvas.before:
            Color(0.86, 0.91, 1.0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(0.30, 0.40, 0.70, 1)
            self._ln = Line(rectangle=(0, 0, 0, 0), width=1.0)

        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ln.rectangle = (self.x, self.y, self.width, self.height)
        self.text_size = self.size

class DoseBox(BoxLayout):
    """템플릿 좌측 상단 고정 입력 박스."""

    def __init__(self, on_edit, **kw):
        super().__init__(
            orientation="vertical",
            padding=(dp(10), dp(8)), spacing=dp(2),
            size_hint=(None, None), size=(DOSE_W, DOSE_H), **kw)

        self.on_edit = on_edit
        self.btn = {}

        with self.canvas.before:
            Color(1, 1, 1, 0.92)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*BLACK)
            self._ln = Line(rectangle=(0, 0, 0, 0), width=1.2)

        self.bind(pos=self._sync, size=self._sync)

        self.add_widget(self._row_pre())
        self.add_widget(self._row_intra())
        self.add_widget(self._row_mosfet())

    # ---------------------------------------------------------- internal
    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ln.rectangle = (self.x, self.y, self.width, self.height)

    @staticmethod
    def _lab(text, w, align="left"):
        return Label(text=text, color=BLACK, font_size=DOSE_FS,
                     halign=align, valign="middle",
                     size_hint=(None, 1), width=w,
                     text_size=(w, None))

    @staticmethod
    def _gap(w):
        return Widget(size_hint=(None, 1), width=w)

    def _mkbtn(self, key, w):
        b = ValueBtn(width=w)
        b.bind(on_release=lambda *_a, k=key: self.on_edit(k))
        self.btn[key] = b
        return b

    @staticmethod
    def _fmt(v, is_int=False):
        if v is None:
            return "-"
        return str(int(v)) if is_int else fmt_num(v)

    # ---------------------------------------------------------- rows
    def _row_pre(self):
        r = BoxLayout(orientation="horizontal", spacing=dp(3))

        r.add_widget(self._lab("Pre", dp(30)))
        r.add_widget(self._lab(":", dp(6)))
        r.add_widget(self._mkbtn("pre", dp(60)))
        r.add_widget(self._lab("Gy", dp(24)))

        r.add_widget(self._gap(dp(5)))          # <-- 간격

        r.add_widget(self._lab("Residual", dp(60)))
        r.add_widget(self._lab(":", dp(6)))
        r.add_widget(self._mkbtn("residual", dp(40)))
        r.add_widget(self._lab("cc", dp(24)))

        r.add_widget(Widget())
        return r

    def _row_intra(self):
        r = BoxLayout(orientation="horizontal", spacing=dp(3))

        r.add_widget(self._lab("Intra", dp(30)))
        r.add_widget(self._lab(":", dp(6)))
        r.add_widget(self._mkbtn("intra", dp(60)))
        r.add_widget(self._lab("Gy", dp(24)))

        r.add_widget(self._gap(dp(5)))          # <-- 간격

        r.add_widget(self._lab("Asymmetry", dp(80)))
        r.add_widget(self._lab(":", dp(6)))
        self.asym_lbl = self._lab("X", dp(40))
        self.asym_lbl.color = RED
        r.add_widget(self.asym_lbl)

        r.add_widget(Widget())
        return r

    def _row_mosfet(self):
        r = BoxLayout(orientation="horizontal", spacing=dp(2))

        r.add_widget(self._lab("Mosfet", dp(50)))
        r.add_widget(self._lab(":", dp(6)))
        r.add_widget(self._mkbtn("mosfet", dp(60)))
        r.add_widget(self._lab("Gy", dp(24)))

        r.add_widget(self._lab("(Ch", dp(25)))   # <-- 바로 붙임
        r.add_widget(self._mkbtn("channel", dp(25)))
        r.add_widget(self._lab(")", dp(12)))

        r.add_widget(Widget())
        return r

    # ---------------------------------------------------------- public
    def set_value(self, key, val):
        b = self.btn.get(key)
        if b is None:
            return
        if val is None:
            b.text = "-"
        elif key in ("channel", "residual"):
            b.text = str(int(val))
        else:
            b.text = fmt_num(val)

    def set_asym(self, summary):
        nums = find_unpaired(summary)
        self.asym_lbl.text = ", ".join(str(n) for n in nums) if nums else "X"

# ================================================================= helpers
# ================================================================= number input
FLOAT_FMT = "{:.1f}"
DECIMALS = 1


def fmt_num(v):
    """숫자를 화면 표기용 문자열로."""
    if v is None:
        return ""
    try:
        return FLOAT_FMT.format(float(v))
    except (TypeError, ValueError):
        return str(v)

def ask_number(title, on_ok=None, initial=None, integer=False, **legacy):
    """자체 숫자 키패드.  OK → float/int, 빈칸이면 None (음수 미지원)"""
    if "init" in legacy:
        initial = legacy["init"]
    if "is_int" in legacy:
        integer = legacy["is_int"]
    # allow_negative / allow_neg 는 받되 무시

    if initial is None:
        start = ""
    elif integer:
        start = str(int(initial))
    else:
        start = fmt_num(initial)
    buf = {"s": start}

    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

    disp = Label(text=buf["s"] or "-", font_size=sp(34),
                 size_hint_y=None, height=dp(56),
                 halign="right", valign="middle")
    disp.bind(size=lambda w, *a: setattr(w, "text_size", w.size))
    root.add_widget(disp)

    def show():
        disp.text = buf["s"] or "-"

    def press(ch):
        s = buf["s"]
        if ch == "C":
            s = ""
        elif ch == "<":
            s = s[:-1]
        elif ch == ".":
            if integer or "." in s:
                return
            s = (s or "0") + "."
        else:
            if len(s) >= 8:
                return
            s += ch
        buf["s"] = s
        show()

    def key(ch):
        b = Button(text=ch, font_size=sp(28))
        b.bind(on_release=lambda *a: press(ch))
        return b

    grid = GridLayout(cols=3, spacing=dp(6))
    for ch in ("7", "8", "9", "4", "5", "6", "1", "2", "3"):
        grid.add_widget(key(ch))
    grid.add_widget(key("C"))
    grid.add_widget(key("0"))
    dot = key(".")
    dot.disabled = integer
    grid.add_widget(dot)
    root.add_widget(grid)

    pop = Popup(title=title, content=root, auto_dismiss=False,
                size_hint=(None, None), size=(dp(320), dp(470)))

    def ok(*a):
        s = buf["s"].strip().rstrip(".")
        if s == "":
            val = None
        else:
            try:
                val = int(round(float(s))) if integer else round(float(s), DECIMALS)
            except ValueError:
                val = None
        pop.dismiss()
        if on_ok:
            on_ok(val)

    bar = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(6))
    b_bs = Button(text="<-", font_size=sp(26))
    b_bs.bind(on_release=lambda *a: press("<"))
    b_ca = Button(text="Cancel", font_size=sp(22))
    b_ca.bind(on_release=lambda *a: pop.dismiss())
    b_ok = Button(text="OK", font_size=sp(24))
    b_ok.bind(on_release=ok)
    for b in (b_bs, b_ca, b_ok):
        bar.add_widget(b)
    root.add_widget(bar)

    pop.open()

def nop_value(nop):
    """36 미만이면 그대로, 36 이상이면 매칭된 값을 반환 (숫자만)."""
    try:
        n = int(nop)
    except (TypeError, ValueError):
        return 0

    if n < NOP_BASE:
        return n
    return NOP_BASE_VAL + (n - NOP_BASE) // NOP_STEP

def nop_label(nop):
    """36 이상이면 '36 (8)' 형태, 미만이면 숫자만."""
    try:
        n = int(nop)
    except (TypeError, ValueError):
        return str(nop)

    if n < NOP_BASE:
        return str(n)
    return "%d (%d)" % (n, nop_value(n))

def retraction_steps(numplane):
    """numplane 에 따른 retraction 선택 폭  -0.5 ~ -(numplane-2)/2"""
    n = nop_value(numplane)
    if n < 2:
        return []
    return [round(-0.5 + 0.5 * i, 1) for i in range(n)]

def nearest_row(value):
    """snap a float row value to the FULL_ROWS grid."""
    return min(FULL_ROWS, key=lambda r: abs(r - value))


def get_xy(col, row):
    """plot.py get_xy() - identical."""
    x_step = (X_G - X_A) / (len(COLS) - 1)
    y_step = (Y_1 - Y_6) / (len(FULL_ROWS) - 1)

    x = X_A + COLS.index(col) * x_step
    y = Y_1 - FULL_ROWS.index(nearest_row(row)) * y_step
    return x, y


def text_texture(text, px, color, bold=False):
    """CoreLabel -> texture (px = font size in pixels)."""
    lbl = CoreLabel(text=str(text), font_size=max(6, px), bold=bold, color=color)
    lbl.refresh()
    return lbl.texture


# ================================================================= template
class TemplateView(StencilView):
    """Right pane : template image + needles + touch handling."""

    def __init__(self, screen, **kw):
        super().__init__(**kw)
        self.last_click = None
        self.screen = screen
        self.scale = 1.0
        self.ox = 0.0
        self.oy = 0.0

        try:
            self.tex = CoreImage(TEMPLATE_PNG).texture
        except Exception:
            self.tex = None

        self.bind(pos=self._redraw, size=self._redraw)

    # ------------------------------------------------------------ geometry
    @property
    def view_top(self):
        return self.screen.y_top - 30

    @property
    def view_h(self):
        return V_BOTTOM - self.view_top

    def _calc(self):
        if self.width <= 1 or self.height <= 1:
            return
        s = min(self.width / float(IMG_W), self.height / float(self.view_h))
        self.scale = s
        self.ox = self.x + (self.width - IMG_W * s) / 2.0
        self.oy = self.y + (self.height - self.view_h * s) / 2.0

    def to_screen(self, mx, my):
        """image coords -> kivy screen coords (y flipped)."""
        return (self.ox + mx * self.scale,
                self.oy + (V_BOTTOM - my) * self.scale)

    def to_image(self, sx, sy):
        return ((sx - self.ox) / self.scale,
                V_BOTTOM - (sy - self.oy) / self.scale)

    # ------------------------------------------------------------ drawing
    def _redraw(self, *a):
        self.draw()

    def _txt(self, text, mx, my, pt, color, bold=False,
             halign="left", valign="baseline"):
        """draw text using matplotlib-like anchoring."""
        px = pt * FONT_SCALE * self.scale
        tex = text_texture(text, px, color, bold)
        sx, sy = self.to_screen(mx, my)

        w, h = tex.size
        if halign == "center":
            sx -= w / 2.0
        elif halign == "right":
            sx -= w

        if valign == "center":
            sy -= h / 2.0
        elif valign == "baseline":
            sy -= h * 0.75
        elif valign == "top":
            sy -= h

        Rectangle(texture=tex, pos=(sx, sy), size=(w, h))

    def draw(self):
        self._calc()
        self.canvas.clear()
        if self.scale <= 0:
            return

        summary = self.screen.summary
        s = self.scale

        with self.canvas:
            # ---------- template image
            Color(1, 1, 1, 1)
            if self.tex:
                bl = self.to_screen(0, IMG_H)
                Rectangle(texture=self.tex, pos=bl,
                          size=(IMG_W * s, IMG_H * s))

            # ---------- collect per-location info (plot.py logic)
            location_highlight = {}
            location_info = {}

            for info in summary.values():
                if info["is_removed"]:
                    continue
                key = (info["col"], nearest_row(info["row"]))

                if info["highlight"]:
                    location_highlight[key] = True

                if key not in location_info:
                    location_info[key] = {"actuals": [], "needles": []}

                location_info[key]["actuals"].append(info["actual_count"])
                location_info[key]["needles"].append(info["real_needle"])

            drawn = set()

            items = sorted(summary.items(),
                           key=lambda kv: (kv[1]["display_needle"],
                                           kv[1]["real_needle"]))

            for real_needle, info in items:
                if info["is_removed"]:
                    continue

                col = info["col"]
                row = nearest_row(info["row"])
                key = (col, row)

                actual = info["actual_count"]
                expected = info["expected_count"]
                real_no = info["real_needle"]
                display_no = info["display_needle"]

                if key in drawn:
                    continue
                drawn.add(key)

                x, y = get_xy(col, row)

                mismatch = (actual != expected)

                # ---------- circle
                face = HL_BG if location_highlight.get(key, False) else WHITE
                Color(*face)
                Ellipse(pos=self.to_screen(x - HOLE_R, y + HOLE_R),
                        size=(HOLE_R * 2 * s, HOLE_R * 2 * s))

                cx, cy = self.to_screen(x, y)
                if mismatch:
                    Color(*ORANGE)
                    Line(circle=(cx, cy, HOLE_R * s), width=1.5 * s)
                else:
                    Color(*BLACK)
                    Line(circle=(cx, cy, HOLE_R * s), width=1.0 * s)

                # ---------- number inside circle
                actual_text = "+".join(
                    str(v) for v in location_info[key]["actuals"])
                Color(1, 1, 1, 1)
                self._txt(actual_text,
                          x + OFF_CENTER[0], y + OFF_CENTER[1],
                          LBL_PT_CENTER, BLACK,
                          halign="center", valign="center")

                # ---------- needle number(s)
                same_location  = len(location_info[key]["needles"]) > 1
                same3_location = len(location_info[key]["needles"]) > 2

                if same_location:
                    needle_text = ",".join(
                        str(v) for v in location_info[key]["needles"])
                    if same3_location:                    # 3개 이상 먼저
                        off = OFF_3MULTI
                    else:                                 # 2개
                        off = OFF_MULTI
                    self._txt(needle_text,
                              x + off[0], y + off[1],
                              LBL_PT, BLACK, True)

                    if real_no != display_no:
                        self._txt(display_no,
                                  x + OFF_DISPLAY[0], y + OFF_DISPLAY[1],
                                  LBL_PT, BLUE, True)

                elif real_no != display_no:
                    self._txt(real_no,
                              x + OFF_REAL[0], y + OFF_REAL[1],
                              LBL_PT, BLACK, True)
                    self._txt(display_no,
                              x + OFF_DISPLAY[0], y + OFF_DISPLAY[1],
                              LBL_PT, BLUE, True)

                else:
                    self._txt(display_no,
                              x + OFF_REAL[0], y + OFF_REAL[1],
                              LBL_PT, BLACK, True)

                # ---------- expected (red) when mismatch
                if mismatch:
                    self._txt(expected,
                              x + OFF_EXPECTED[0], y + OFF_EXPECTED[1],
                              LBL_PT, RED, True)

    # ------------------------------------------------------------ touch
    def on_touch_down(self, touch):
        for w in (getattr(self.screen, "legend", None),
                  getattr(self.screen, "dosebox", None)):
            if w is not None and w.collide_point(*touch.pos):
                return True

        if not self.collide_point(*touch.pos):
            return False
        if not EDIT_MODE:
            return True

        mx, my = self.to_image(touch.x, touch.y)

        best = None
        best_d = None
        for c in COLS:
            for r in FULL_ROWS:
                if r > self.screen.display_max_row:
                    continue
                hx, hy = get_xy(c, r)
                d = (hx - mx) ** 2 + (hy - my) ** 2
                if best_d is None or d < best_d:
                    best_d = d
                    best = (c, r)

        if best is None:
            return True
        if best_d > (HIT_R * 4) ** 2:
            return True

        self.screen.last_click = self.to_window(touch.x, touch.y)
        self.screen.hole_clicked(best[0], best[1])
        return True


# ================================================================= table cell
class TCell(ButtonBehavior, Label):
    """table cell with background + grid line."""

    def __init__(self, bg=WHITE, dot=False, dot_color=RED, prefix="",prefix_color=RED, prefix_gap=None, **kw):
        kw.setdefault("color", BLACK)
        kw.setdefault("font_size", sp(15))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bg = bg
        self.dot = dot
        self.dot_color = dot_color
        self._gap = dp(12) if prefix_gap is None else prefix_gap
        self._prefix_lbl = None
        self.bind(pos=self._paint, size=self._paint, texture_size=self._fit)

        if prefix:
            self._prefix_lbl = Label(
                text=str(prefix),
                color=prefix_color,
                font_size=self.font_size,
                bold=self.bold,
                size_hint=(None, None),
                halign="right",
                valign="middle",
            )
            self._prefix_lbl.bind(
                texture_size=self._prefix_lbl.setter("size"))
            self._prefix_lbl.bind(size=self._place_prefix)
            self.add_widget(self._prefix_lbl)
            self.bind(pos=self._place_prefix, size=self._place_prefix)
            self._place_prefix()

    def _place_prefix(self, *a):
        lb = self._prefix_lbl
        if lb is None:
            return
        lb.right = self.center_x - self._gap
        lb.center_y = self.center_y

    def _fit(self, *a):
        self.text_size = (self.width, None)

    def _paint(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg)
            Rectangle(pos=self.pos, size=self.size)
            Color(*GRID)
            Line(rectangle=(self.x, self.y, self.width, self.height),
                 width=1.0)
            if self.dot:
                r = dp(4)
                Color(*self.dot_color)
                Ellipse(pos=(self.x + self.width * 0.18 - r,
                             self.center_y - r),
                        size=(r * 2, r * 2))

def head_cell(text, **kw):
    kw.setdefault("bg", HEAD_BG)
    kw.setdefault("bold", True)
    kw.setdefault("size_hint_y", None)
    kw.setdefault("height", dp(46))
    return TCell(text=text, **kw)


# ================================================================= root
class RootView(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation="horizontal", **kw)

        self.summary = {}
        self.patient_no = ""
        self.patient_name = ""
        self.numplane = 0
        self.base_needles = 0
        self.base_seeds = 0
        self.original_needle_count = 0
        self.show_4d = False
        self.display_max_row = 6.0
        self.y_top = Y_1
        self.row_index = []

        # ---------------- left panel
        left = BoxLayout(orientation="vertical", size_hint_x=0.34,
                         padding=dp(6), spacing=dp(6))
        with left.canvas.before:
            Color(*PANEL_BG)
            self._lbg = Rectangle(pos=left.pos, size=left.size)
        left.bind(pos=lambda w, v: setattr(self._lbg, "pos", v),
                  size=lambda w, v: setattr(self._lbg, "size", v))

        top = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(6))
        self.info_label = Label(text="No patient loaded",
                                color=BLACK, bold=True,
                                font_size=sp(18), halign="left",
                                valign="middle")
        self.info_label.bind(size=lambda w, v:
                             setattr(w, "text_size", v))
        open_btn = Button(text="Open", size_hint_x=None, width=dp(110),
                          font_size=sp(17))
        open_btn.bind(on_release=lambda *a: self.open_patient())
        top.add_widget(self.info_label)
        top.add_widget(open_btn)
        left.add_widget(top)

        # header row
        self.header = GridLayout(cols=6, size_hint_y=None, height=dp(46),
                                 spacing=0)
        left.add_widget(self.header)

        # scrollable body
        self.grid = GridLayout(cols=6, size_hint_y=None, spacing=0)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        sv = ScrollView(bar_width=dp(8))
        sv.add_widget(self.grid)
        left.add_widget(sv)

        # ---------------- right panel
        self.add_widget(left)

        # ---------------- right panel  (template + plan summary)
        right = BoxLayout(orientation="vertical", size_hint_x=0.66,
                          padding=dp(6), spacing=dp(6))

#        self.view = TemplateView(self, size_hint_y=1)
#        right.add_widget(self.view)

        tpl_wrap = FloatLayout(size_hint_y=1)

        self.view = TemplateView(self, size_hint=(1, 1),
                                 pos_hint={"x": 0, "y": 0})
        tpl_wrap.add_widget(self.view)

        self.tpl_wrap = tpl_wrap

        self.legend = LegendBox(pos_hint={"right": 1, "top": 1})
        tpl_wrap.add_widget(self.legend)

        # --- 추가 ---
        self.dose = {"pre": None, "residual": None, "intra": None,
                     "mosfet": None, "channel": None}

        self.dosebox = DoseBox(self._edit_dose,
                               pos_hint={"x": 0, "top": 1})
        tpl_wrap.add_widget(self.dosebox)
        # -----------

        tpl_wrap.bind(pos=self._place_legend,
                      size=self._place_legend)

        right.add_widget(tpl_wrap)

        # plan summary (under template)
        sumbox = BoxLayout(orientation="vertical", size_hint_y=None,
                           height=dp(180), spacing=dp(4),
                           padding=(dp(40), 0, dp(40), dp(4)))
        sumbox.add_widget(TCell(text="Plan Summary", bg=HEAD_BG,color=BLACK, bold=True,
                                font_size=sp(25), size_hint_y=None,
                                height=dp(32)))
        self.sumgrid = GridLayout(cols=4, size_hint_y=None, height=dp(132))
        sumbox.add_widget(self.sumgrid)
        right.add_widget(sumbox)

        self.add_widget(right)


        Clock.schedule_once(self._place_legend, 0)
        Clock.schedule_once(lambda dt: self.open_patient(), 0.4)

    # ============================================================ loading
    def open_patient(self):

        if not filesource.ensure_permission():
            filesource.request_all_files_access()
            self.msg("권한 필요",
                     "'모든 파일 접근'을 켠 뒤\n다시 Open 을 누르세요.")
            return

        try:
            files = get_files()          # <-- 최신 5개
        except Exception as e:
            self.msg("Error", "File search failed\n%s" % e)
            return

        if not files:
            self.msg("No files",
                     "TXT 파일이 없습니다.\n\n[검색 위치]\n%s"
                     % filesource.scanned_paths_text())
            return

        opts = [(label_for(f), f) for f in files]
        choose_from_list("Select patient", "# Brachy   Name",
                         opts, self._load)

    def _load(self, picked):
        if picked is None:
            return
    
        # ---------- 경로 / 파일명 정보 ----------
        if isinstance(picked, dict):
            path = picked.get("path")
            pinfo = picked                      # list_patient_files() 결과 재사용
        else:
            path = picked
            pinfo = filesource.parse_filename(os.path.basename(path))
    
        if not path:
            self.msg("Error", "No file selected")
            return
    
        # ---------- TXT 파싱 ----------
        try:
            result = load_patient_path(path)
        except Exception as e:
            self.msg("Error", "Load failed\n%s" % e)
            return
    
        # ---------- 환자 정보 (파일명 우선, TXT는 fallback) ----------
        self.path = path
    
        self.patient_no = (
            pinfo.get("patient_no")
            or result.get("patient_no")
            or ""
        )
        self.patient_name = (
            pinfo.get("name")
            or result.get("name")
            or ""
        )
    
        self.numplane = result.get("number_of_planes", 0)
    
        # ---------- 시드 / 니들 ----------
        summary = result["summary"]
    
        self.base_needles = sum(
            1 for s in summary.values()
            if not s["is_extra"]
        )
        self.base_seeds = sum(
            s["actual_count"] for s in summary.values()
            if not s["is_extra"]
        )

        self.original_needle_count = len(summary)

        self.summary = assign_display_numbers(summary)
    
        self.refresh() 

    # ============================================================ legend
    def _place_legend(self, *a):
        w = self.tpl_wrap

        self.legend.x = w.right - LEGEND_W - LEGEND_MARGIN
        self.legend.top = w.top - LEGEND_MARGIN

        self.dosebox.x = w.x + LEGEND_MARGIN
        self.dosebox.top = w.top - LEGEND_MARGIN

    # ============================================================ dose
    def _edit_dose(self, key):
        title = {
            "pre":     "Pre dose (Gy)",
            "residual": "Residual (cc)",
            "intra":   "Intra dose (Gy)",
            "mosfet":  "Mosfet dose (Gy)",
            "channel": "Mosfet channel",
        }[key]

        is_int = key in ("channel", "residual")

        def _ok(v):
            self.dose[key] = v
            self.dosebox.set_value(key, v)

        ask_number(title, _ok,
                   initial=self.dose.get(key),
                   integer=is_int)

    def _recalc_rows(self):
        if not self.summary:
            self.display_max_row = 6.0
        else:
            max_row = max(nearest_row(s["row"]) for s in self.summary.values())
            self.display_max_row = min(6.0, max_row + 1.0)

        idx = FULL_ROWS.index(nearest_row(self.display_max_row))
        self.y_top = Y_1 - ((Y_1 - Y_6) * idx / (len(FULL_ROWS) - 1))

    def need_4d(self):
        return any(
            s["real_needle"] != s["display_needle"]
            for s in self.summary.values()
            if not s["is_removed"]
        )

    def refresh(self):
        self.summary = assign_display_numbers(self.summary)
        self.show_4d = self.need_4d()         
        self._recalc_rows()

        self.info_label.text = "%s   %s   Image : %s" % (
            self.patient_no, self.patient_name, nop_label(self.numplane))

        self.build_table()
        self.build_summary()
        self.view.draw()
        self.dosebox.set_asym(self.summary)

    # ============================================================ table
    def build_table(self):
        cols = 6 if self.show_4d else 5
        self.header.cols = cols
        self.grid.cols = cols

        self.header.clear_widgets()
        self.grid.clear_widgets()
        self.row_index = []

        FS = sp(22)          # 데이터 셀 폰트
        rh = dp(28)          # 데이터 행 높이

        live = [n for n, i in self.summary.items() if not i["is_removed"]]
        all_hl = bool(live) and all(self.summary[n]["highlight"] for n in live)
        hl_head = "H.L.\n" + (CHK_ON if all_hl else CHK_OFF)

        if self.show_4d:
            titles = ["Real\nnumber", "4D\nnumber", "Retraction\n(cm)",
                      "Hole\nLocation", "Number\nSeeds", hl_head]
            widths = [0.16, 0.15, 0.20, 0.18, 0.17, 0.14]
        else:
            titles = ["Real\nnumber", "Retraction\n(cm)",
                      "Hole\nLocation", "Number\nSeeds", hl_head]
            widths = [0.19, 0.23, 0.21, 0.20, 0.17]

        for idx, (t, w) in enumerate(zip(titles, widths)):
            c = head_cell(t)
            c.size_hint_x = w
            c.halign = "center"
            c.valign = "middle"
            if idx == len(titles) - 1:
                c.bind(on_release=lambda *a: self.toggle_all_highlight())
            self.header.add_widget(c)

        items = sorted(
            ((k, v) for k, v in self.summary.items()
             if not (v["is_removed"] and v["is_extra"])),
            key=lambda kv: (kv[1]["real_needle"]))

        for real_no, info in items:
            removed = info["is_removed"]
            base_c = BLACK
            bg = WHITE if removed else (HL_BG if info["highlight"] else WHITE)

            # ── seed count 비교를 루프 상단에서 미리 계산 ──
            actual = info["actual_count"]
            expected = info["expected_count"]
            mismatch = (not removed) and (actual != expected)
            is_extra = (not removed) and bool(info["is_extra"])

            self.row_index.append(real_no)
            i = 0                      # 열 인덱스 카운터

            # --- 1) Real number (display) + extra / mismatch dot
            c0 = TCell(text=("" if removed else str(info["real_needle"])),
                       color=base_c, bold=True, bg=bg,
                       dot=(mismatch or is_extra),
                       dot_color=(RED if mismatch else BLACK),
                       font_size=FS,
                       size_hint_y=None, height=rh)
            c0.size_hint_x = widths[i]; i += 1
            c0.bind(on_release=lambda w, n=real_no: self.row_clicked(n))
            self.grid.add_widget(c0)

            # --- 2) 4D number
            if self.show_4d:
                d = info["display_needle"]
                v_txt = "" if (removed or d == info["real_needle"]) else str(d)
                c4 = TCell(text=v_txt,
                           color=BLUE, bg=bg,
                           font_size=FS,
                           size_hint_y=None, height=rh)
                c4.size_hint_x = widths[i]; i += 1
                c4.bind(on_release=lambda w, n=real_no: self.row_clicked(n))
                self.grid.add_widget(c4)

            # --- 3) Retraction (cm)
            rt = info.get("retraction")
            rt_txt = "" if (removed or rt in (None, "")) \
                else ("%.1f" % float(rt))
            c3 = TCell(text=rt_txt, color=base_c, bg=bg,
                       font_size=FS,
                       size_hint_y=None, height=rh)
            c3.size_hint_x = widths[i]; i += 1
            if removed:
                c3.bind(on_release=lambda w, n=real_no: self.row_clicked(n))
            else:
                c3.bind(on_release=lambda w, n=real_no: self.retraction_menu(n))
            self.grid.add_widget(c3)

            # --- 4) Hole Location
            if removed:
                loc = ""
            else:
                row_v = nearest_row(info["row"])
                loc = "%s %.1f" % (info["col"], row_v)
            c1 = TCell(text=loc, color=base_c, bg=bg,
                       font_size=FS,
                       size_hint_y=None, height=rh)
            c1.size_hint_x = widths[i]; i += 1
            c1.bind(on_release=lambda w, n=real_no: self.row_clicked(n))
            self.grid.add_widget(c1)

            # --- 5) Number Seeds (expected in red / actual)
            if removed:
                seed_txt = ""
                seed_pfx = ""
            elif mismatch:
                seed_txt = str(actual)
                seed_pfx = str(expected)
            else:
                seed_txt = str(actual)
                seed_pfx = ""
            c2 = TCell(text=seed_txt, color=base_c, bg=bg, prefix=seed_pfx, prefix_color=RED, prefix_gap=dp(22),
                       font_size=FS,
                       size_hint_y=None, height=rh)
            c2.size_hint_x = widths[i]; i += 1
            c2.bind(on_release=lambda w, n=real_no: self.row_clicked(n))
            self.grid.add_widget(c2)

            # --- 6) H.L. checkbox
            mark = "" if removed else (CHK_ON if info["highlight"] else CHK_OFF)
            c5 = TCell(text=mark, color=base_c, bg=bg, bold=False,
                       font_size=FS,
                       size_hint_y=None, height=rh)
            c5.size_hint_x = widths[i]
            c5.bind(on_release=lambda w, n=real_no: self.toggle_highlight(n))
            self.grid.add_widget(c5)

    # ============================================================ summary
    def build_summary(self):
        self.sumgrid.clear_widgets()

        cur_needles = sum(1 for s in self.summary.values()
                          if not s["is_removed"])
        cur_seeds = sum(s["actual_count"] for s in self.summary.values()
                        if not s["is_removed"])

        dn = cur_needles - self.base_needles
        ds = cur_seeds - self.base_seeds

        dn_txt = ("%+d" % dn) if dn else ""
        ds_txt = ("%+d" % ds) if ds else ""

        rows = [
            ["", "Initial", "Extra", "Final"],
            ["Needle", self.base_needles, dn_txt, cur_needles],
            ["Seed", self.base_seeds, ds_txt, cur_seeds],
        ]

        h = dp(44)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                is_head = (r == 0)
                bg = HEAD_BG if is_head else (HL_BG if c == 3 else WHITE)
                cell = TCell(text=str(val), bg=bg,
                             bold=is_head or c == 3 or c == 0,
                             font_size=sp(24),
                             size_hint_y=None, height=h)
                self.sumgrid.add_widget(cell)

    # ============================================================ actions
    def toggle_all_highlight(self):
        live = [s for s in self.summary.values() if not s["is_removed"]]
        if not live:
            return
        on = not all(s["highlight"] for s in live)
        for s in live:
            s["highlight"] = on
        self.refresh()

    def toggle_highlight(self, real_no):
        s = self.summary.get(real_no)
        if s is None or s["is_removed"]:
            return
        s["highlight"] = not s["highlight"]
        self.refresh()

    def _stock_used(self):
        """현재 사용 중인 extra 니들 개수 {2: n, 3: n}."""
        used = {2: 0, 3: 0}
        for s in self.summary.values():
            if s["is_extra"] and not s["is_removed"]:
                c = s["actual_count"]
                if c in used:
                    used[c] += 1
        return used

    def _can_add(self, seeds):
        """seeds(2~5) 추가 가능 여부 -> (ok, 필요한 니들 리스트)."""
        need = get_extra_needles(seeds)
        if not need:
            return False, []
        used = self._stock_used()
        for k in (2, 3):
            if used[k] + need.count(k) > EXTRA_STOCK[k]:
                return False, need
        return True, need

    def add_extra(self, col, row, seeds):
        ok, need = self._can_add(seeds)
        if not ok:
            u = self._stock_used()
            self.msg("Out of stock",
                     "Cannot add %d seeds\n\n"
                     "2-seed : %d / %d\n3-seed : %d / %d"
                     % (seeds, u[2], EXTRA_STOCK[2],
                        u[3], EXTRA_STOCK[3]))
            return

        for s in need:
            no = get_next_real_needle(
                self.summary, self.original_needle_count, s)
            if no is None:
                self.msg("Out of stock",
                         "No free slot for %d-seed needle" % s)
                break
            add_manual_needle(self.summary, no, col, row, s)

        self.refresh()

    def row_clicked(self, real_no):
        return

    def _find_base_at(self, col, row):
        for n, i in self.summary.items():
            if not i["is_extra"] and nearest_row(i["row"]) == row \
                    and i["col"] == col:
                return n
        return None

    def hole_clicked(self, col, row):
        row = nearest_row(row)

        base_no = self._find_base_at(col, row)
        extra_no = find_extra_needle_at(self.summary, col, row)

        if base_no is not None:
            self.needle_menu(base_no, self.summary[base_no],
                             extra_no=extra_no)
            return

        if extra_no is not None:
            self.needle_menu(extra_no, self.summary[extra_no])
            return

        self.ask_add_extra(col, row)

    # ---------------- menus
    def needle_menu(self, real_no, info, extra_no=None):
        is_extra = info["is_extra"]
        removed  = info["is_removed"]
        used     = self._stock_used()

        col = info["col"]
        row = nearest_row(info["row"])

        # 이 구멍의 extra 실번호 (자기 자신이 extra 면 real_no)
        ex_no = real_no if is_extra else extra_no
        has_extra = ex_no is not None

        # 같은 구멍의 extra 키 전부
        ex_keys = [k for k, s in self.summary.items()
                   if s["is_extra"] and s["col"] == col
                   and nearest_row(s["row"]) == row]

        opts = []

        # ---------------- 1) 최상단 : Delete / Remove / Restore
        if has_extra:
            lab = "Delete extra"
            opts.append((lab, ("del", 0)))
        elif removed:
            opts.append(("Restore", ("restore", 0)))
        else:
            opts.append(("Remove", ("rm", 0)))

        # ---------------- 2) Extra 2 / 3 / 4 / 5
        for v in (2, 3, 4, 5):
            need = get_extra_needles(v)
            ok = need and all(
                used[k] + need.count(k) <= EXTRA_STOCK[k] for k in (2, 3))
            if ok:
                opts.append(("Extra  %d" % v, ("add", v)))
            else:
                opts.append(("Extra  %d  \n(out of stock)" % v, ("x", v)))

        # ---------------- 제목 / 부제목
        if has_extra:
            title = "Extra needle  -  %s %.1f" % (col, row)
            sub = "extra %d ea  2 seeds: %d / %d    3 seeds: %d / %d" % (
                len(ex_keys), used[2], EXTRA_STOCK[2],
                used[3], EXTRA_STOCK[3])
        else:
            title = "Needle %s" % (info["real_needle"] if removed
                                   else info["display_needle"])
            state = ("  (removed)" if removed
                     else "  seeds %d" % info["actual_count"])
            sub = "%s %.1f %s   2 seeds: %d / %d    3 seeds: %d / %d" % (
                col, row, state, used[2], EXTRA_STOCK[2],
                used[3], EXTRA_STOCK[3])

        def cb(v):
            if not v:
                return
            act, val = v
            if act == "rm":
                info["is_removed"] = True
                self.refresh()
            elif act == "restore":
                info["is_removed"] = False
                self.refresh()
            elif act == "add":
                self.add_extra(col, row, val)
            elif act == "del":
                for k in ex_keys:
                    self.summary.pop(k, None)
                self.refresh()

        choose_option(title, sub, opts, cb, anchor=getattr(self, "last_click", None))

    def retraction_menu(self, real_no):
        info = self.summary.get(real_no)
        if not info or info["is_removed"]:
            return

        cur = info.get("retraction")
        steps = retraction_steps(self.numplane)
        if not steps:
            return

        opts = []
        for v in steps:
            mark = "  ●" if (cur is not None and abs(cur - v) < 1e-6) else ""
            opts.append(("%.1f%s" % (v, mark), ("set", v)))

        if cur is not None:
            opts.append(("Clear", ("clear", 0)))

        # ↓ 여기 추가
        if "_prev_ret" in info:
            p = info["_prev_ret"]
            lab = "Undo  (%s)" % ("Clear" if p is None else "%.1f" % p)
            opts.append((lab, ("undo", 0)))

        title = "Retraction  -  needle %s" % info["display_needle"]
        sub = ("%s %.1f      seeds %d"
               % (info["col"], info["row"],
                  info["actual_count"]))

        def cb(v):
            if not v:
                return
            act, val = v
            if act == "undo":
                info["retraction"] = info.pop("_prev_ret", None)
                self.refresh()
                return
            
            info["_prev_ret"] = cur 

            if act == "set":
                info["retraction"] = val
            elif act == "clear":
                info["retraction"] = None
            self.refresh()

        choose_option(title, sub, opts, cb, anchor=getattr(self, "last_click", None))

    def ask_retraction(self, real_no):
        info = self.summary.get(real_no)
        if info is None:
            return
        try:
            choices = get_retraction_choices(info["actual_count"])
        except TypeError:
            choices = get_retraction_choices(self.summary, real_no)

        opts = [("%g" % float(v), float(v)) for v in choices]

        def cb(v):
            if v is None:
                return
            set_retraction(self.summary, real_no, v)
            self.refresh()

        choose_option("Retraction",
                      "Needle %s" % info["display_needle"],
                      opts, cb)

    def ask_add_extra(self, col, row):
        used = self._stock_used()

        opts = []
        for v in (2, 3, 4, 5):
            need = get_extra_needles(v)
            ok = need and all(
                used[k] + need.count(k) <= EXTRA_STOCK[k] for k in (2, 3))
            opts.append(("Extra  %d" % v if ok
                         else "Extra  %d   (out of stock)" % v,
                         v if ok else None))

        def cb(v):
            if v is None:
                return
            self.add_extra(col, row, v)

        choose_option("Add extra needle",
                      "%s %.1f    2 seeds: %d / %d    3 seeds: %d / %d"
                      % (col, row, used[2], EXTRA_STOCK[2],
                         used[3], EXTRA_STOCK[3]),
                      opts, cb)
    # ============================================================ util
    def msg(self, title, text):
        choose_option(title, text, [("OK", None)], lambda v: None)


# ================================================================= app
class LDRApp(App):
    title = "LDR Template Viewer"

    def build(self):
        return RootView()


if __name__ == "__main__":
    LDRApp().run()