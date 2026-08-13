
# -*- coding: utf-8 -*-
"""D열 기준 좌우 대칭 검사."""

COLS = ["A", "a", "B", "b", "C", "c", "D", "d", "E", "e", "F", "f", "G"]

# A-G, a-f, B-F, b-e, C-E, c-d, D-D
MIRROR = {COLS[i]: COLS[len(COLS) - 1 - i] for i in range(len(COLS))}


def _entries(summary):
    """summary 를 (real_no, col, row) 목록으로 평탄화. removed 는 제외."""
    out = []
    for real_no, info in summary.items():
        if info.get("is_removed"):
            continue
        col = info.get("col")
        row = info.get("row")
        if col is not None and row is not None:
            out.append((real_no, col, float(row)))

        for ex_no, ex in (info.get("extra") or {}).items():
            ecol = ex.get("col")
            erow = ex.get("row")
            if ecol is not None and erow is not None:
                out.append((ex_no, ecol, float(erow)))
    return out

def _target_items(summary):
    """asymmetry 대상: 기존 needle 중 removed 아닌 것만."""
    out = {}
    for no, info in summary.items():
        if info.get("is_extra"):        # extra 제외
            continue
        if info.get("is_removed"):      # 삭제된 기존 needle 제외
            continue
        out[no] = info
    return out

def find_unpaired(summary, ignore_center=True):
    """짝이 없는 니들의 real_needle 번호 리스트(정렬)를 반환.

    ignore_center=True 이면 D 열(중심축)은 항상 대칭으로 간주해 제외.
    """
    summary = _target_items(summary)
    items = _entries(summary)

    # (col, row) -> 존재 여부
    occupied = {(c, r) for _no, c, r in items}

    unpaired = []
    for no, col, row in items:
        if ignore_center and col == "D":
            continue
        mate = (MIRROR.get(col), row)
        if mate not in occupied:
            unpaired.append(no)

    return sorted(unpaired)


def asymmetry_text(summary, ignore_center=True):
    """'3, 7, 12' 형태 문자열. 없으면 '-' 반환."""
    nos = find_unpaired(summary, ignore_center)
    if not nos:
        return "-"
    return ", ".join(str(n) for n in nos)