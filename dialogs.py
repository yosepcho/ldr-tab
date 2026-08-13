
# dialogs.py
# -------------------------------------------------------------
# plot.py 에서 사용하는 공용 다이얼로그 모음
#   - choose_patient_file() : 날짜 폴더의 TXT 목록에서 환자 선택
#   - choose_hole_action()  : hole 클릭 시 동작 선택
#   - choose_retraction()   : retraction 값 선택
#
# 실제 위젯/유틸은 dialogs_core.py 에 있음
# -------------------------------------------------------------

import os

from tkinter import messagebox

from dialogs_core import (
    BASE_DIR,
    DEFAULT_DATE,
    FILE_RE,
    _get_root,
    _ListDialog,
    choose_option,
)


# =====================================
# 1) 환자 파일 선택
# =====================================

def _parse_filename(fname):
    m = FILE_RE.match(fname)

    if not m:
        return {
            "patient_no": None,
            "name": None,
            "rest": None,
        }

    return {
        "patient_no": m.group("no").strip(),
        "name": m.group("name").strip(),
        "rest": m.group("rest").strip(),
    }


def list_patient_files(date=DEFAULT_DATE, base_dir=BASE_DIR):

    folder = os.path.join(base_dir, str(date))

    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)

    items = []

    for fname in os.listdir(folder):

        if not fname.lower().endswith(".txt"):
            continue

        full = os.path.join(folder, fname)

        if not os.path.isfile(full):
            continue

        info = _parse_filename(fname)
        info["filename"] = fname
        info["path"] = full

        items.append(info)

    # 환자번호 기준 정렬 (숫자면 숫자순, 아니면 파일명순)
    def _key(it):
        no = it.get("patient_no")

        if no is not None and no.isdigit():
            return (0, int(no), it["filename"])

        return (1, 0, it["filename"])

    items.sort(key=_key)

    return items


def _label_for(info):
    """리스트에 표시할 한 줄 라벨."""

    no = info.get("patient_no")
    name = info.get("name")

    if no and name:
        return "%-10s %s" % (no, name)

    return info["filename"]


def choose_patient_file(date=DEFAULT_DATE, base_dir=BASE_DIR):
    """
    날짜 폴더의 TXT 파일 목록을 띄우고 하나를 고르게 한다.

    return : list_patient_files() 항목 dict 또는 None(취소)
    """

    root = _get_root()

    folder = os.path.join(base_dir, str(date))

    try:
        items = list_patient_files(date, base_dir)

    except FileNotFoundError:
        messagebox.showerror(
            "폴더 없음",
            "폴더를 찾을 수 없습니다.\n\n%s" % folder,
            parent=root
        )
        return None

    except OSError as e:
        messagebox.showerror(
            "접근 실패",
            "폴더를 열 수 없습니다.\n\n%s\n\n%s" % (folder, e),
            parent=root
        )
        return None

    if not items:
        messagebox.showwarning(
            "파일 없음",
            "TXT 파일이 없습니다.\n\n%s" % folder,
            parent=root
        )
        return None

    labels = [_label_for(it) for it in items]

    prompt = "%s   (총 %d명)\n환자를 선택하세요." % (folder, len(items))

    dlg = _ListDialog(root, "환자 선택", prompt, labels)

    if dlg.index is None:
        return None

    return items[dlg.index]


# =====================================
# 2) hole 클릭 동작 선택
# =====================================

HOLE_ACTIONS = [
    ("제거", "remove"),
    ("복구", "restore"),
    ("2 seeds", "2"),
    ("3 seeds", "3"),
    ("4 seeds", "4"),
    ("5 seeds", "5"),
]


def choose_hole_action(col, row):
    """
    hole 클릭 시 동작 선택.

    return :
        None       : 취소
        "remove"   : 해당 hole 제거
        "restore"  : 제거 취소(복구)
        "2".."5"   : extra needle 추가 + seed 개수
    """

    prompt = "위치 : %s%s\n\n동작을 선택하세요." % (col, row)

    return choose_option(
        "Hole 편집",
        prompt,
        HOLE_ACTIONS,
        initial_index=0
    )


# =====================================
# 3) retraction 선택
# =====================================

def _fmt_retraction(v):
    """retraction 표시용 문자열."""

    if v is None:
        return "-"

    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return "%d" % int(round(v))
        return ("%.2f" % v).rstrip("0").rstrip(".")

    return str(v)


def choose_retraction(choices, current=None):
    """
    choices : get_retraction_choices() 가 만든 값 리스트
    current : 현재 retraction 값 (초기 선택 위치)

    return : 선택된 값 또는 None(취소)
    """

    if not choices:
        root = _get_root()
        messagebox.showinfo(
            "Retraction",
            "선택할 수 있는 retraction 값이 없습니다.",
            parent=root
        )
        return None

    options = [(_fmt_retraction(v), v) for v in choices]

    initial = 0

    for i, v in enumerate(choices):
        if v == current:
            initial = i
            break

    prompt = "현재 : %s\n\nretraction 값을 선택하세요." % _fmt_retraction(current)

    return choose_option(
        "Retraction",
        prompt,
        options,
        initial_index=initial
    )


# =====================================
# 단독 실행 테스트
# =====================================

if __name__ == "__main__":

    picked = choose_patient_file(DEFAULT_DATE)
    print("picked   :", picked)

    if picked is not None:
        print("action   :", choose_hole_action("D", 3))
        print("retract  :", choose_retraction([0, 5, 10, 15], 5))
