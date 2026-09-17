# dialogs_core.py
# -------------------------------------------------------------
# 공용 설정 / 유틸 / 기본 다이얼로그 위젯
# (dialogs.py 에서 import 해서 사용)
#
# [수정 요점]
#  1) matplotlib(TkAgg)가 만든 Tk 루트가 있으면 재사용 -> Tk 중복 생성 방지
#  2) 부모가 숨김(withdraw) 상태면 transient 생략 -> 작업표시줄에 표시됨
#  3) topmost / lift / focus_force 로 창을 강제로 앞으로
#  4) winfo_exists() 를 try/except 로 안전 처리
# -------------------------------------------------------------

import re

import tkinter as tk
from tkinter import ttk



# =====================================
# 공용 유틸
# =====================================

_ROOT = None

# 우리가 직접 만든 루트인지 여부
# (matplotlib 것을 빌려 쓴 경우엔 destroy 하면 안 됨)
_ROOT_OWNED = False


def _alive(w):
    """위젯이 살아있는지 안전하게 확인."""

    if w is None:
        return False

    try:
        return bool(w.winfo_exists())
    except Exception:
        return False


def _get_root():
    """
    tk root 하나를 확보한다.

    우선순위
      1) 이전에 확보해 둔 _ROOT
      2) 이미 존재하는 tk._default_root (matplotlib TkAgg 등)
      3) 새로 생성
    """

    global _ROOT, _ROOT_OWNED

    # 1) 캐시된 루트
    if _alive(_ROOT):
        return _ROOT

    _ROOT = None
    _ROOT_OWNED = False

    # 2) 이미 살아있는 기본 루트 재사용
    existing = getattr(tk, "_default_root", None)

    if _alive(existing):
        _ROOT = existing
        _ROOT_OWNED = False
        return _ROOT

    # 3) 새로 생성
    _ROOT = tk.Tk()
    _ROOT_OWNED = True

    _ROOT.withdraw()

    try:
        _ROOT.call("tk", "scaling", 1.2)
    except Exception:
        pass

    return _ROOT


def close_root():
    """
    우리가 만든 루트만 정리한다.
    (matplotlib 루트는 건드리지 않음)
    """

    global _ROOT, _ROOT_OWNED

    if _ROOT_OWNED and _alive(_ROOT):
        try:
            _ROOT.destroy()
        except Exception:
            pass

    _ROOT = None
    _ROOT_OWNED = False


def _is_viewable(w):
    """부모 창이 실제로 화면에 보이는 상태인지."""

    if not _alive(w):
        return False

    try:
        return bool(w.winfo_viewable())
    except Exception:
        return False


def _center(win, parent=None):
    """창을 화면(또는 부모) 중앙으로."""

    try:
        win.update_idletasks()
    except Exception:
        return

    w = win.winfo_width()
    h = win.winfo_height()

    if w <= 1 or h <= 1:
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()

    if _is_viewable(parent):
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        x = px + (pw - w) // 2
        y = py + (ph - h) // 2

    else:
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 3

    win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))


def _bring_to_front(top):
    """
    창을 확실히 화면 맨 앞으로 끌어올린다.

    VS Code 통합 터미널에서 실행할 때
    창이 에디터 뒤로 숨어 '멈춘 것처럼' 보이는 문제 방지.
    """

    try:
        top.deiconify()
    except Exception:
        pass

    try:
        top.attributes("-topmost", True)
    except Exception:
        pass

    try:
        top.lift()
    except Exception:
        pass

    try:
        top.focus_force()
    except Exception:
        pass

    # 잠시 뒤 topmost 해제 (다른 창을 계속 가리지 않도록)
    def _release():
        try:
            if top.winfo_exists():
                top.attributes("-topmost", False)
        except Exception:
            pass

    try:
        top.after(400, _release)
    except Exception:
        pass


def _setup_modal(top, parent):
    """
    다이얼로그 공통 마무리 처리.

    - 부모가 보일 때만 transient 지정
      (숨겨진 부모에 transient 를 걸면 작업표시줄에서 사라짐)
    - 중앙 배치 + 앞으로 끌어올림
    - grab_set 은 실패해도 무시
    """

    if _is_viewable(parent):
        try:
            top.transient(parent)
        except Exception:
            pass

    _center(top, parent)
    _bring_to_front(top)

    try:
        top.grab_set()
    except Exception:
        pass


def _wait(top, parent):
    """다이얼로그가 닫힐 때까지 대기."""

    try:
        parent.wait_window(top)
    except Exception:
        # 부모 쪽 문제 시 자체 대기로 폴백
        try:
            top.wait_window(top)
        except Exception:
            pass


# =====================================
# 콤보 다이얼로그
# =====================================

class _ComboDialog:

    def __init__(self, parent, title, prompt, labels, initial_index=0):

        self.index = None

        top = self.top = tk.Toplevel(parent)
        top.title(title)
        top.resizable(False, False)

        frm = ttk.Frame(top, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=prompt, justify="left").pack(
            anchor="w", pady=(0, 10)
        )

        self.var = tk.StringVar()

        cb = self.cb = ttk.Combobox(
            frm,
            textvariable=self.var,
            values=labels,
            state="readonly",
            width=24,
            font=("Consolas", 11)
        )
        cb.pack(fill="x")

        if labels:
            idx = initial_index if 0 <= initial_index < len(labels) else 0
            cb.current(idx)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(14, 0))

        ttk.Button(btns, text="취소", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="확인", command=self._ok).pack(
            side="right", padx=(0, 6)
        )

        cb.bind("<Return>", lambda e: self._ok())
        top.bind("<Escape>", lambda e: self._cancel())
        top.protocol("WM_DELETE_WINDOW", self._cancel)

        _setup_modal(top, parent)

        try:
            cb.focus_set()
        except Exception:
            pass

        _wait(top, parent)

    def _ok(self):
        try:
            self.index = self.cb.current()
        except Exception:
            self.index = None

        self._close()

    def _cancel(self):
        self.index = None
        self._close()

    def _close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass

        try:
            self.top.destroy()
        except Exception:
            pass


def choose_option(title, prompt, options, initial_index=0):
    """
    options : [(label, value), ...]
    return  : 선택된 value 또는 None(취소)
    """

    if not options:
        return None

    root = _get_root()

    labels = [str(o[0]) for o in options]

    dlg = _ComboDialog(root, title, prompt, labels, initial_index)

    if dlg.index is None or dlg.index < 0:
        return None

    return options[dlg.index][1]


# =====================================
# 리스트 다이얼로그
# =====================================

class _ListDialog:

    def __init__(self, parent, title, prompt, labels):

        self.index = None

        top = self.top = tk.Toplevel(parent)
        top.title(title)
        top.resizable(True, True)

        frm = ttk.Frame(top, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=prompt, justify="left").pack(
            anchor="w", pady=(0, 8)
        )

        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(box, orient="vertical")

        lb = self.lb = tk.Listbox(
            box,
            height=min(16, max(4, len(labels))),
            width=52,
            activestyle="dotbox",
            exportselection=False,
            font=("Consolas", 11),
            yscrollcommand=sb.set
        )
        sb.config(command=lb.yview)

        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for lab in labels:
            lb.insert("end", lab)

        if labels:
            lb.selection_set(0)
            lb.see(0)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(14, 0))

        ttk.Button(btns, text="취소", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="열기", command=self._ok).pack(
            side="right", padx=(0, 6)
        )

        lb.bind("<Double-Button-1>", lambda e: self._ok())
        lb.bind("<Return>", lambda e: self._ok())
        top.bind("<Escape>", lambda e: self._cancel())
        top.protocol("WM_DELETE_WINDOW", self._cancel)

        _setup_modal(top, parent)

        try:
            lb.focus_set()
        except Exception:
            pass

        _wait(top, parent)

    def _ok(self):
        try:
            sel = self.lb.curselection()
            self.index = sel[0] if sel else None
        except Exception:
            self.index = None

        self._close()

    def _cancel(self):
        self.index = None
        self._close()

    def _close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass

        try:
            self.top.destroy()
        except Exception:
            pass


def choose_from_list(title, prompt, options):
    """
    options : [(label, value), ...]
    return  : 선택된 value 또는 None(취소)
    """

    if not options:
        return None

    root = _get_root()

    labels = [str(o[0]) for o in options]

    dlg = _ListDialog(root, title, prompt, labels)

    if dlg.index is None or dlg.index < 0:
        return None

    return options[dlg.index][1]


# =====================================
# 단독 테스트
# =====================================

if __name__ == "__main__":

    print("[test] choose_from_list")

    v = choose_from_list(
        "리스트 테스트",
        "항목을 고르세요",
        [("첫번째", 1), ("두번째", 2), ("세번째", 3)]
    )
    print("  ->", v)

    print("[test] choose_option")

    v = choose_option(
        "콤보 테스트",
        "옵션을 고르세요",
        [("A", "a"), ("B", "b"), ("C", "c")]
    )
    print("  ->", v)

    close_root()

    print("[test] done")