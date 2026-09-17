# -*- coding: utf-8 -*-
"""
TXT 파일 목록을 얻는 모듈.

Android : /storage/emulated/0/Download   (= 내장 메모리 / Download)
PC      : BASE_DIR / DEFAULT_DATE 폴더  + ./sample

Outlook 첨부를 Download 에 직접 저장해서 쓴다.
폴더에 옛날 파일이 쌓이므로

  1) 같은 환자번호는 저장 시각이 가장 최신인 것 1개만 남기고
  2) 그중 최신 MAX_FILES 명만 고른다.

표시 순서는 환자번호 오름차순.

main.py 진입점 : get_files()
점검          : py filesource.py
"""

import os
import re
import time

try:
    from kivy.utils import platform
except Exception:
    platform = "unknown"


# =====================================================
# 설정
# =====================================================

# 최신 몇 명까지 가져올지. None 이면 전부.
MAX_FILES = 5

# 같은 환자번호가 여러 개면 최신 것 1개만 남긴다.
DEDUP_BY_PATIENT = True

# Android 기본 검색 폴더 (내장 메모리 / Download)
ANDROID_DIR = "/storage/emulated/0/Download"

# 자동 탐색이 실패할 때만 적는다. 보통 비워둔다.
EXTRA_DIRS = [
    # "/storage/emulated/0/LDR",
]

DATE_PATTERN = re.compile(r"^\d{6}$")


# =====================================================
# 플랫폼 / 권한
# =====================================================

def is_android():
    return platform == "android"


def _sdk_int():
    try:
        from jnius import autoclass
        return autoclass("android.os.Build$VERSION").SDK_INT
    except Exception:
        return 0


def has_all_files_access():
    """Android 11+ 의 '모든 파일에 대한 접근' 상태."""

    if not is_android():
        return True

    if _sdk_int() < 30:
        return True

    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        return bool(Environment.isExternalStorageManager())
    except Exception:
        return False


def request_all_files_access():
    """설정 화면을 연다. 사용자가 직접 토글을 켜야 한다."""

    if not is_android() or _sdk_int() < 30:
        return False

    try:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        Activity = autoclass("org.kivy.android.PythonActivity").mActivity

        intent = Intent(
            Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse("package:" + Activity.getPackageName()))
        Activity.startActivity(intent)
        return True

    except Exception:
        pass

    try:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Activity = autoclass("org.kivy.android.PythonActivity").mActivity

        Activity.startActivity(
            Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
        return True

    except Exception:
        return False


def request_legacy_permissions():
    """Android 10 이하."""

    if not is_android() or _sdk_int() >= 30:
        return

    try:
        from android.permissions import request_permissions, Permission

        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ])
    except Exception:
        pass


def ensure_permission():
    """True 면 읽기 가능. False 면 request_all_files_access() 로 안내."""

    if not is_android():
        return True

    if _sdk_int() < 30:
        request_legacy_permissions()
        return True

    return has_all_files_access()


# =====================================================
# 후보 폴더
# =====================================================

def _external_root():
    try:
        from android.storage import primary_external_storage_path
        return primary_external_storage_path()
    except Exception:
        return "/storage/emulated/0"


def latest_date_dir(base=None):
    """PC : BASE_DIR 아래 6자리 날짜 폴더 중 최신."""

    base = base or BASE_DIR

    if not os.path.isdir(base):
        return None

    try:
        names = os.listdir(base)
    except OSError:
        return None

    cands = [n for n in names
             if DATE_PATTERN.match(n)
             and os.path.isdir(os.path.join(base, n))]

    if not cands:
        return None

    cands.sort(reverse=True)

    return os.path.join(base, cands[0])


def candidate_dirs():
    """스캔할 폴더 목록을 우선순위대로 반환."""

    dirs = []

    if is_android():

        dirs.append(ANDROID_DIR)

        root = _external_root()

        if root and root != "/storage/emulated/0":
            dirs.append(os.path.join(root, "Download"))

    else:

        if DEFAULT_DATE:
            dirs.append(os.path.join(BASE_DIR, DEFAULT_DATE))
        else:
            d = latest_date_dir()
            if d:
                dirs.append(d)

        dirs.append(BASE_DIR)
        dirs.append(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "sample"))

    dirs.extend(EXTRA_DIRS)

    # 중복 제거 (순서 유지)
    out = []
    seen = set()

    for d in dirs:
        if not d:
            continue
        k = os.path.normpath(d).lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(d)

    return out


# =====================================================
# 파싱
# =====================================================

def parse_filename(fname):
    """파일명에서 환자번호 / 이름을 뽑는다."""

    base = os.path.splitext(fname)[0].strip()

    if "_" in base:
        no, rest = base.split("_", 1)
        no = no.strip()
    else:
        no, rest = None, base

    name = rest.split(" - ")[0].strip()

    return {
        "patient_no": no or None,
        "name": name or None,
    }


def label_for(info):
    """리스트에 표시할 한 줄."""

    no = info.get("patient_no")
    name = info.get("name")

    if no and name:
        return "%-8s  %s" % (no, name)
    if name:
        return name
    if no:
        return no

    return info.get("filename", "(unknown)")


# =====================================================
# 목록
# =====================================================

def _sort_key(it):
    """환자번호 오름차순."""

    no = it.get("patient_no")

    if no is not None and str(no).isdigit():
        return (0, int(no), it["filename"])

    return (1, 0, it["filename"])


def list_patient_files(dirs=None):
    """
    후보 폴더들의 .txt 를 모두 모아 반환 (필터 없음).

    return : [
        {"filename", "path", "folder",
         "patient_no", "name",
         "mtime", "mtime_str"}, ...
    ]
    """

    if dirs is None:
        dirs = candidate_dirs()

    items = []
    seen = set()

    for folder in dirs:

        if not folder or not os.path.isdir(folder):
            continue

        try:
            names = os.listdir(folder)
        except OSError:
            continue

        for fname in names:

            if not fname.lower().endswith(".txt"):
                continue

            full = os.path.join(folder, fname)

            if not os.path.isfile(full):
                continue

            key = os.path.normpath(full).lower()

            if key in seen:
                continue

            seen.add(key)

            try:
                mt = os.path.getmtime(full)
            except OSError:
                mt = 0

            info = parse_filename(fname)
            info["filename"] = fname
            info["path"] = full
            info["folder"] = folder
            info["mtime"] = mt
            info["mtime_str"] = time.strftime(
                "%m/%d %H:%M", time.localtime(mt))

            items.append(info)

    items.sort(key=_sort_key)

    return items


def _patient_key(it):
    """환자 식별자. 번호가 없으면 이름, 그것도 없으면 파일명."""

    no = it.get("patient_no")

    if no:
        return ("no", str(no))

    name = it.get("name")

    if name:
        return ("name", name.lower())

    return ("file", it["filename"].lower())


def dedup_latest(items):
    """같은 환자번호는 mtime 이 가장 큰 것 1개만 남긴다."""

    best = {}

    for it in items:

        k = _patient_key(it)
        cur = best.get(k)

        if cur is None or it.get("mtime", 0) > cur.get("mtime", 0):
            best[k] = it

    out = list(best.values())
    out.sort(key=_sort_key)

    return out


def select_files(items, limit=None):
    """목록에서 최신 limit 명을 고르고 환자번호 오름차순으로 반환."""

    if limit is None:
        limit = MAX_FILES

    if DEDUP_BY_PATIENT:
        items = dedup_latest(items)

    if limit and len(items) > limit:
        items = sorted(items, key=lambda d: d.get("mtime", 0),
                       reverse=True)[:limit]

    items = list(items)
    items.sort(key=_sort_key)

    return items


def get_files(dirs=None, limit=None):
    """main.py 진입점."""

    return select_files(list_patient_files(dirs), limit)


def scanned_paths_text(dirs=None):
    """오류 메시지에 쓸 폴더 목록 문자열."""

    if dirs is None:
        dirs = candidate_dirs()

    lines = []

    for d in dirs:
        mark = "OK " if os.path.isdir(d) else "없음"
        lines.append("%s  %s" % (mark, d))

    return "\n".join(lines)


def folder_signature(dirs=None):
    """폴더 변경 감지용 서명 (파일명 + mtime)."""

    items = list_patient_files(dirs)

    return tuple(sorted(
        (it["filename"], int(it.get("mtime", 0))) for it in items))


# =====================================================
# 진단
# =====================================================

def _row(it):
    return "%-8s %-18s %s" % (
        it.get("patient_no") or "-",
        (it.get("name") or "-")[:18],
        it.get("mtime_str"),
    )


def diagnose():
    """권한 / 폴더 / 파일 상태를 문자열로."""

    out = []

    out.append("platform : %s" % platform)
    out.append("android  : %s" % is_android())

    if is_android():
        out.append("sdk      : %s" % _sdk_int())
        out.append("권한     : %s" % has_all_files_access())

    out.append("dedup    : %s" % DEDUP_BY_PATIENT)

    out.append("")
    out.append("[검색 폴더]")

    dirs = candidate_dirs()

    for d in dirs:

        if not os.path.isdir(d):
            out.append("  %-58s 없음" % d)
            continue

        try:
            n = len([f for f in os.listdir(d)
                     if f.lower().endswith(".txt")])
            out.append("  %-58s (txt %d)" % (d, n))
        except OSError as e:
            out.append("  %-58s 접근 실패 %s" % (d, e))

    allf = list_patient_files(dirs)
    sel = select_files(allf)

    # path 기준으로 비교해야 정확하다
    picked = set(os.path.normpath(x["path"]).lower() for x in sel)

    out.append("")
    out.append("[전체 %d개 -> 선택 %d개]   (환자번호 오름차순)"
               % (len(allf), len(sel)))

    for it in sel:
        out.append("  * " + _row(it))

    drop = [x for x in allf
            if os.path.normpath(x["path"]).lower() not in picked]

    if drop:
        drop.sort(key=lambda d: d.get("mtime", 0), reverse=True)
        out.append("")
        out.append("[제외 %d개]  (구버전 또는 정원 초과)" % len(drop))
        for it in drop:
            out.append("    " + _row(it))

    bad = [x for x in sel
           if not x.get("patient_no") or not x.get("name")]

    out.append("")

    if bad:
        out.append("[파싱 실패] 파일명 규칙 확인 필요")
        for it in bad:
            out.append("    %s" % it["filename"])
    else:
        out.append("파싱 정상. 환자번호/이름 모두 추출됨.")

    return "\n".join(out)


if __name__ == "__main__":
    print(diagnose())