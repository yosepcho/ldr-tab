from pathlib import Path
from collections import defaultdict

def get_patient_info(filepath):

    filepath = Path(filepath)

    stem = filepath.stem
    
    patient_no, rest = stem.split("_", 1)
    
    patient_name = rest.split(" - ")[0]

    return patient_no, patient_name


def load_source_locations(filepath):

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]

    start = None
    end = None

    for i, line in enumerate(lines):

        if line.startswith("Number of Planes;"):
            nop = int(line.split(";")[1])

        elif line == "Source Locations":
            start = i + 2

        elif line.startswith("Checksum;"):
            end = i
            break

    if start is None:
        raise Exception("Source Locations를 찾을 수 없습니다.")

    if end is None:
        raise Exception("Checksum을 찾을 수 없습니다.")

    result = []

    for line in lines[start:end]:

        if not line.startswith(";;"):
            continue

        p = line.split(";")

        result.append({
            "needle": int(p[2]),
            "col": p[3],
            "row": float(p[4]),
            "retraction": float(p[5]),
            "z": float(p[-1])
        })

    return result, nop

def summarize_needles(data):

    needles = defaultdict(list)

    for row in data:
        needles[row["needle"]].append(row)

    summary = {}

    for needle, rows in needles.items():

        z_values = sorted([r["z"] for r in rows])

        actual_count = len(z_values)

        expected_count = round(
            max(z_values) - min(z_values)
        ) + 1

        summary[needle] = {
            "real_needle": needle,
            "display_needle": None,
            "is_extra": False,
            "is_removed": False,
            "highlight": False,
            "col": rows[0]["col"],
            "row": rows[0]["row"],
            "retraction": rows[0]["retraction"],
            "actual_count": actual_count,
            "expected_count": expected_count
        }

    return summary

def load_patient_path(txt_file):
    """
    파일 경로를 직접 받아서 로드한다.
    (load_patient() 과 동일하되 파일 검색 단계만 생략)
    """
    txt_file = Path(txt_file)
    number, name = get_patient_info(txt_file)

    data, nop = load_source_locations(txt_file)

    summary = summarize_needles(data)

    return {
        "patient_no": number,
        "patient_name": name,
        "summary": summary,
        "number_of_planes": nop
    }