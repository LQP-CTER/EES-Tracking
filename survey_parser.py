"""
═══════════════════════════════════════════════════════════════════════════
GHN EES 2026 — Survey Parser
═══════════════════════════════════════════════════════════════════════════
Parse Google Form responses cho từng nhóm 2A / 2B / 3A / 3B.
Output chuẩn hóa gồm các cột:
  timestamp, survey_group, phong_ban_raw, vung_canonical,
  bo_phan_raw, cap_bac, division_wf, section_wf, is_gxt, is_warehouse
═══════════════════════════════════════════════════════════════════════════
"""
import pandas as pd
import numpy as np
from org_hierarchy import (
    resolve_vung_from_form,
    resolve_ktc_from_form,
    resolve_gxt_section_from_form,
    resolve_ho_division_from_form,
    VUNG_LIST,
)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN DETECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _find_col(df: pd.DataFrame, *keywords) -> str | None:
    """Tìm cột đầu tiên có chứa bất kỳ keyword nào (case-insensitive)."""
    kw_lower = [k.lower() for k in keywords]
    for col in df.columns:
        cl = str(col).lower()
        if any(k in cl for k in kw_lower):
            return col
    return None


def _clean(s) -> str | None:
    """Chuẩn hóa cell value: strip, None nếu rỗng/nan."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).strip()
    return None if s in ("", "nan", "None", "N/A") else s


# ─────────────────────────────────────────────────────────────────────────────
# PARSE GROUP 2A — NV Vận hành Kho
# ─────────────────────────────────────────────────────────────────────────────
def parse_2a(df: pd.DataFrame) -> pd.DataFrame:
    """
    Columns thực tế trong form 2A:
      - Timestamp
      - Phòng ban (*)   → chọn: Vùng (Bưu Cục) | Vùng (KTC) | KTC/TTTC | GXT | Warehouse
      - Bạn thuộc Vùng nào?
      - Bạn thuộc KCT/TTCT nào?
      - Bạn thuộc bộ phận nào?   (GXT)
      - Warehouse/Fulfillment (KHL)
      - Cấp bậc hiện tại (*)
      + 26 câu hỏi survey
    """
    if len(df) == 0:
        return _empty_output()

    rows = []
    col_ts       = _find_col(df, "timestamp", "thời gian")
    col_pb       = _find_col(df, "phòng ban", "phong ban")
    col_vung     = _find_col(df, "thuộc vùng", "bạn thuộc vùng")
    col_ktc      = _find_col(df, "kct", "ttct", "ktc")
    col_gxt_bp   = _find_col(df, "bộ phận nào", "bo phan")
    col_khl      = _find_col(df, "warehouse", "fulfillment", "khl")
    col_rank     = _find_col(df, "cấp bậc", "cap bac")

    for _, row in df.iterrows():
        ts   = pd.to_datetime(row[col_ts], errors="coerce") if col_ts else pd.NaT
        pb   = _clean(row[col_pb]) if col_pb else None
        rank = _clean(row[col_rank]) if col_rank else None

        vung_c      = None
        section_wf  = None
        division_wf = None
        is_gxt      = False
        is_warehouse= False
        bo_phan_raw = None

        if pb is None:
            pass
        elif "warehouse" in pb.lower() or "fulfillment" in pb.lower() or "khl" in pb.lower():
            is_warehouse = True
            division_wf  = "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)"
            bo_phan_raw  = _clean(row[col_khl]) if col_khl else None
        elif "giao hàng nặng" in pb.lower() or "gxt" in pb.lower():
            is_gxt      = True
            division_wf = "Freight Project"
            gxt_val     = _clean(row[col_gxt_bp]) if col_gxt_bp else None
            bo_phan_raw = gxt_val
            section_wf  = resolve_gxt_section_from_form(gxt_val) if gxt_val else None
        elif "kho trung chuyển" in pb.lower() or "ktc" in pb.lower() or "tttc" in pb.lower():
            division_wf = "Market Division"
            ktc_val     = _clean(row[col_ktc]) if col_ktc else None
            bo_phan_raw = ktc_val
            vung_c      = resolve_ktc_from_form(ktc_val) if ktc_val else None
        else:
            # Vùng (Bưu Cục / KTC thuộc Vùng)
            division_wf = "Market Division"
            vung_val    = _clean(row[col_vung]) if col_vung else None
            bo_phan_raw = vung_val
            vung_c      = resolve_vung_from_form(vung_val) if vung_val else None

        rows.append({
            "timestamp":     ts,
            "survey_group":  "2A",
            "phong_ban_raw": pb,
            "vung_canonical":vung_c,
            "bo_phan_raw":   bo_phan_raw,
            "cap_bac":       rank,
            "division_wf":   division_wf,
            "section_wf":    section_wf,
            "is_gxt":        is_gxt,
            "is_warehouse":  is_warehouse,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PARSE GROUP 2B — Quản lý Tuyến đầu
# ─────────────────────────────────────────────────────────────────────────────
def parse_2b(df: pd.DataFrame) -> pd.DataFrame:
    """
    Columns thực tế trong form 2B:
      - Timestamp
      - Phòng Ban bạn đang làm việc?  → Vùng (...) | KTC/TTTC | GXT | Warehouse
      - Bạn thuộc Vùng nào?
      - Bạn thuộc KCT/TTCT nào?
      - Bạn thuộc bộ phận nào?        (GXT)
      - Warehouse/Fulfillment (KHL)
      - Cấp bậc hiện tại của bạn?
    """
    if len(df) == 0:
        return _empty_output()

    rows = []
    col_ts   = _find_col(df, "timestamp", "thời gian")
    col_pb   = _find_col(df, "phòng ban", "phong ban")
    col_vung = _find_col(df, "thuộc vùng", "bạn thuộc vùng")
    col_ktc  = _find_col(df, "kct", "ttct", "ktc")
    col_gxt  = _find_col(df, "bộ phận nào", "bo phan nao")
    col_khl  = _find_col(df, "warehouse", "fulfillment", "khl")
    col_rank = _find_col(df, "cấp bậc", "cap bac")

    for _, row in df.iterrows():
        ts   = pd.to_datetime(row[col_ts], errors="coerce") if col_ts else pd.NaT
        pb   = _clean(row[col_pb]) if col_pb else None
        rank = _clean(row[col_rank]) if col_rank else None

        vung_c      = None
        section_wf  = None
        division_wf = None
        is_gxt      = False
        is_warehouse= False
        bo_phan_raw = None

        if pb is None:
            pass
        elif "warehouse" in pb.lower() or "fulfillment" in pb.lower():
            is_warehouse = True
            division_wf  = "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)"
            bo_phan_raw  = _clean(row[col_khl]) if col_khl else None
        elif "giao hàng nặng" in pb.lower() or "gxt" in pb.lower():
            is_gxt      = True
            division_wf = "Freight Project"
            gxt_val     = _clean(row[col_gxt]) if col_gxt else None
            bo_phan_raw = gxt_val
            section_wf  = resolve_gxt_section_from_form(gxt_val) if gxt_val else None
        elif "kho trung chuyển" in pb.lower() or "trung tâm" in pb.lower():
            division_wf = "Market Division"
            ktc_val     = _clean(row[col_ktc]) if col_ktc else None
            bo_phan_raw = ktc_val
            vung_c      = resolve_ktc_from_form(ktc_val) if ktc_val else None
        else:
            # Vùng (Bưu Cục, KTC thuộc Vùng)
            division_wf = "Market Division"
            vung_val    = _clean(row[col_vung]) if col_vung else None
            bo_phan_raw = vung_val
            vung_c      = resolve_vung_from_form(vung_val) if vung_val else None

        rows.append({
            "timestamp":     ts,
            "survey_group":  "2B",
            "phong_ban_raw": pb,
            "vung_canonical":vung_c,
            "bo_phan_raw":   bo_phan_raw,
            "cap_bac":       rank,
            "division_wf":   division_wf,
            "section_wf":    section_wf,
            "is_gxt":        is_gxt,
            "is_warehouse":  is_warehouse,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PARSE GROUP 3A — NV Văn phòng HO
# ─────────────────────────────────────────────────────────────────────────────
def parse_3a(df: pd.DataFrame) -> pd.DataFrame:
    """
    Columns thực tế trong form 3A:
      - Timestamp
      - Phòng Ban (*)   → chọn Division (Khối CT, Khối KH, ...)
      - Bạn thuộc (*)   → chọn Department bên trong
      - Cấp bậc (*)
    """
    if len(df) == 0:
        return _empty_output()

    rows = []
    col_ts   = _find_col(df, "timestamp", "thời gian")
    col_div  = _find_col(df, "phòng ban", "phong ban", "division", "khối")
    col_dept = _find_col(df, "bạn thuộc", "ban thuoc", "department", "bộ phận")
    col_rank = _find_col(df, "cấp bậc", "cap bac")

    for _, row in df.iterrows():
        ts       = pd.to_datetime(row[col_ts], errors="coerce") if col_ts else pd.NaT
        div_raw  = _clean(row[col_div]) if col_div else None
        dept_raw = _clean(row[col_dept]) if col_dept else None
        rank     = _clean(row[col_rank]) if col_rank else None

        division_wf = resolve_ho_division_from_form(div_raw) if div_raw else None

        rows.append({
            "timestamp":     ts,
            "survey_group":  "3A",
            "phong_ban_raw": div_raw,
            "vung_canonical":None,
            "bo_phan_raw":   dept_raw,
            "cap_bac":       rank,
            "division_wf":   division_wf,
            "section_wf":    dept_raw,   # dept → section mapping
            "is_gxt":        False,
            "is_warehouse":  False,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PARSE GROUP 3B — Manager / Director HO
# ─────────────────────────────────────────────────────────────────────────────
def parse_3b(df: pd.DataFrame) -> pd.DataFrame:
    """Giống 3A, khác ở cấp bậc (Expert → Senior Director)."""
    if len(df) == 0:
        return _empty_output()

    result = parse_3a(df)   # reuse logic, chỉ đổi survey_group
    result["survey_group"] = "3B"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────
PARSERS = {
    "2A": parse_2a,
    "2B": parse_2b,
    "3A": parse_3a,
    "3B": parse_3b,
}

def parse_survey(group: str, df: pd.DataFrame) -> pd.DataFrame:
    """Entry point: gọi parser phù hợp với group."""
    parser = PARSERS.get(group)
    if parser is None:
        return _empty_output()
    try:
        return parser(df)
    except Exception as e:
        import traceback
        print(f"[survey_parser] Error parsing {group}: {e}")
        traceback.print_exc()
        return _empty_output()


def _empty_output() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "timestamp", "survey_group", "phong_ban_raw", "vung_canonical",
        "bo_phan_raw", "cap_bac", "division_wf", "section_wf",
        "is_gxt", "is_warehouse",
    ])