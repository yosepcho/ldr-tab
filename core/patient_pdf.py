# -*- coding: utf-8 -*-

from pathlib import Path
import pymupdf
import re

LDR_ROOT = Path(r"\\10.29.10.40\ldr\LDR-201509~")


def find_patient_folder(patient_no):
    """
    patient_no 와 일치하는 환자 폴더 반환.

    예:
        123456_hong_kill_dong_1
        123456_test_abc

    patient_no = "123456"
    """

    patient_no = str(patient_no).strip()

    if not LDR_ROOT.exists():
        return None

    for folder in LDR_ROOT.iterdir():

        if not folder.is_dir():
            continue

        if folder.name.startswith(patient_no + "."):
            return folder

    return None


def get_output_pdf(patient_no):
    """
    환자의 03.OP/Output.pdf 경로 반환
    없으면 None
    """

    patient_folder = find_patient_folder(patient_no)

    if patient_folder is None:
        return None

    pdf_path = patient_folder / "03.OP" / "Output.pdf"

    if pdf_path.exists():
        return pdf_path

    return None

def get_prostate_info(patient_no):

    pdf_path = get_output_pdf(patient_no)

    if pdf_path is None:
        return None

    doc = pymupdf.open(pdf_path)

    try:
        text = doc[0].get_text()
    finally:
        doc.close()

    prostate = {}

    patterns = {
        "Total Volume": r"Total Volume:\s*([\d.]+)",
        "V200": r"V200%:\s*([\d.]+)\s*cm³\s*\[([\d.]+)",
        "V150": r"V150%:\s*([\d.]+)\s*cm³\s*\[([\d.]+)",
        "V100": r"V100%:\s*([\d.]+)\s*cm³\s*\[([\d.]+)",
        "D90":  r"D90%:\s*([\d.]+)\s*Gy\s*\[([\d.]+)",
    }


    prostate_block = re.search(
        r"Prostate:.*?D90%:.*?(?=Urethra:)",
        text,
        re.S
    )

    if not prostate_block:
        return None

    block = prostate_block.group(0)
    for key, pattern in patterns.items():
    
        m = re.search(pattern, block)
    
        if not m:
            continue
        
        if key == "Total Volume":
            prostate[key] = float(m.group(1))
        else:
            prostate[key] = (
                float(m.group(1)),   # 값
                float(m.group(2)),   # %
            )

    return prostate