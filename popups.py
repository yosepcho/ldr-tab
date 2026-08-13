
# -*- coding: utf-8 -*-
"""
Kivy Popup 다이얼로그.

    choose_option("Title", "prompt", [("Label", value), ...], cb)

anchor 를 넘기지 않아도 마지막 터치 지점 근처에 뜬다.
(Window 전역 터치 추적)
"""

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView


CELL_H = dp(38)
CELL_W = dp(96)
GAP = dp(4)
PAD = dp(8)
TITLE_H = dp(34)
CANCEL_H = dp(40)

EDGE = dp(4)
OFFSET = dp(10)

DEBUG_ANCHOR = False     # 확인 끝나면 False


# =====================================
# 전역 터치 추적
# =====================================

_LAST_TOUCH = [None]


def _track_touch(win, touch):
    _LAST_TOUCH[0] = (touch.x, touch.y)
    return False


Window.bind(on_touch_down=_track_touch)


def last_touch():
    return _LAST_TOUCH[0]


# =====================================
# 앵커 배치 믹스인
# =====================================
class AnchorMixin:
    """anchor_pos 근처에 배치. None 이면 마지막 터치 지점."""

    anchor_pos = None
    _busy = False

    def _target(self):
        return self.anchor_pos or _LAST_TOUCH[0]

    # ---- Window 에 붙기 전에 위치 확정 ----

    def open(self, *a, **kw):

        if self._target():
            self.opacity = 0
            self._apply_anchor()          # add_widget 이전

        r = super().open(*a, **kw)

        self._apply_anchor()              # add_widget 직후
        Clock.schedule_once(self._late, 0)
        return r

    def _late(self, dt):
        self._apply_anchor()
        self.opacity = 1

    # ---- 배치 ----

    def _apply_anchor(self, *a):

        tgt = self._target()

        if not tgt or self._busy:
            return

        w, h = self.size
        ax, ay = tgt

        x = ax + OFFSET
        y = ay - h - OFFSET

        if x + w > Window.width - EDGE:
            x = ax - w - OFFSET

        if y < EDGE:
            y = ay + OFFSET

        x = max(EDGE, min(x, Window.width - w - EDGE))
        y = max(EDGE, min(y, Window.height - h - EDGE))

        if abs(self.x - x) < 0.5 and abs(self.y - y) < 0.5:
            return

        self._busy = True
        self.pos = (x, y)
        self._busy = False

        if DEBUG_ANCHOR:
            print("[ANCHOR] tgt=", tgt, " size=", (w, h), " -> ", (x, y))

    def _align_center(self, *a):

        if self._target():
            self._apply_anchor()
            return

        try:
            super()._align_center(*a)
        except AttributeError:
            self.center = Window.center

    def on_pre_open(self):

        try:
            super().on_pre_open()
        except AttributeError:
            pass

        self._apply_anchor()

    def on_open(self):

        try:
            super().on_open()
        except AttributeError:
            pass

        self.bind(pos=self._apply_anchor, size=self._apply_anchor)
        self._apply_anchor()

# =====================================
# 세로 리스트 팝업
# =====================================

class _ChoicePopup(Popup):

    def __init__(self, title, prompt, options, on_select,
                 row_height=dp(56), width_hint=0.55,
                 height_hint=0.75, **kw):

        self._on_select = on_select
        self._picked = False

        root = BoxLayout(orientation="vertical",
                         padding=dp(10), spacing=dp(8))

        if prompt:
            lbl = Label(text=prompt, size_hint_y=None,
                        halign="left", valign="middle",
                        font_size=sp(16))
            lbl.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
            lbl.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(8)))
            root.add_widget(lbl)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(8))

        box = BoxLayout(orientation="vertical",
                        size_hint_y=None, spacing=dp(4))
        box.bind(minimum_height=lambda w, v: setattr(w, "height", v))

        for label, value in options:
            btn = Button(text=str(label), size_hint_y=None,
                         height=row_height, font_size=sp(17),
                         halign="left", valign="middle")
            btn.bind(size=lambda w, v: setattr(
                w, "text_size", (v[0] - dp(20), v[1])))
            btn.bind(on_release=self._h(value))
            box.add_widget(btn)

        scroll.add_widget(box)
        root.add_widget(scroll)

        cancel = Button(text="Cancel", size_hint_y=None,
                        height=dp(50), font_size=sp(16))
        cancel.bind(on_release=lambda *a: self.dismiss())
        root.add_widget(cancel)

        super().__init__(title=title, content=root,
                         size_hint=(width_hint, height_hint),
                         auto_dismiss=True, title_size=sp(18), **kw)

    def _h(self, value):

        def _f(*a):
            if self._picked:
                return
            self._picked = True
            self.dismiss()
            if self._on_select is not None:
                self._on_select(value)

        return _f


# =====================================
# 소형 격자 팝업
# =====================================

class _GridPopup(AnchorMixin, Popup):

    def __init__(self, title, prompt, options, on_select,
                 cols=3, cell_h=CELL_H, cell_w=CELL_W,
                 anchor=None, **kw):

        self._on_select = on_select
        self._picked = False
        self.anchor_pos = anchor

        root = BoxLayout(orientation="vertical",
                         padding=PAD, spacing=GAP)

        prompt_h = 0

        if prompt:
            lbl = Label(text=str(prompt), size_hint_y=None,
                        height=dp(22), halign="center",
                        valign="middle", font_size=sp(13))
            lbl.bind(size=lambda w, v: setattr(w, "text_size", v))
            root.add_widget(lbl)
            prompt_h = dp(22) + GAP

        grid = GridLayout(cols=cols, size_hint_y=None, spacing=GAP)

        for label, value in options:
            btn = Button(text=str(label), size_hint_y=None,
                         height=cell_h, font_size=sp(14),
                         halign="center", valign="middle")
            btn.bind(size=lambda w, v: setattr(
                w, "text_size", (v[0] - dp(6), v[1])))
            btn.bind(on_release=self._h(value))
            grid.add_widget(btn)

        n_rows = (len(options) + cols - 1) // cols
        grid_h = n_rows * cell_h + max(0, n_rows - 1) * GAP
        grid.height = grid_h

        n_c = min(cols, max(1, len(options)))
        want_w = n_c * cell_w + (n_c - 1) * GAP + PAD * 2
        pop_w = min(want_w, Window.width * 0.92)

        chrome = PAD * 2 + prompt_h + CANCEL_H + GAP + TITLE_H + dp(16)

        max_body = Window.height * 0.78 - chrome
        body_h = min(grid_h, max_body)

        if grid_h > max_body:
            scroll = ScrollView(do_scroll_x=False, bar_width=dp(6),
                                size_hint_y=None, height=body_h)
            scroll.add_widget(grid)
            root.add_widget(scroll)
        else:
            root.add_widget(grid)

        cancel = Button(text="Cancel", size_hint_y=None,
                        height=CANCEL_H, font_size=sp(14))
        cancel.bind(on_release=lambda *a: self.dismiss())
        root.add_widget(cancel)

        super().__init__(title=str(title), content=root,
                         size_hint=(None, None),
                         size=(pop_w, body_h + chrome),
                         auto_dismiss=True, title_size=sp(15), **kw)

    def _h(self, value):

        def _f(*a):
            if self._picked:
                return
            self._picked = True
            self.dismiss()
            if self._on_select is not None:
                self._on_select(value)

        return _f


# =====================================
# 공개 API
# =====================================

def choose_option(title, prompt, options, on_select, anchor=None):

    if not options:
        return None

    p = _GridPopup(title, prompt, options, on_select,
                   cols=3, anchor=anchor)
    p.open()
    return p


def choose_grid(title, prompt, options, on_select,
                cols=3, cell_h=CELL_H, cell_w=CELL_W, anchor=None):

    if not options:
        return None

    p = _GridPopup(title, prompt, options, on_select,
                   cols=cols, cell_h=cell_h, cell_w=cell_w,
                   anchor=anchor)
    p.open()
    return p


def choose_from_list(title, prompt, options, on_select):

    if not options:
        return None

    p = _ChoicePopup(title, prompt, options, on_select,
                     width_hint=0.30, height_hint=0.48)
    p.open()
    return p


def info(title, message):

    root = BoxLayout(orientation="vertical",
                     padding=dp(14), spacing=dp(10))

    lbl = Label(text=message, halign="left",
                valign="top", font_size=sp(16))
    lbl.bind(size=lambda w, v: setattr(w, "text_size", v))
    root.add_widget(lbl)

    btn = Button(text="OK", size_hint_y=None,
                 height=dp(50), font_size=sp(16))
    root.add_widget(btn)

    p = Popup(title=title, content=root,
              size_hint=(0.5, 0.45), title_size=sp(18))

    btn.bind(on_release=lambda *a: p.dismiss())
    p.open()
    return p