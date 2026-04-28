"""
═══════════════════════════════════════════════════════════════════════════
GHN EES 2026 — Organization Hierarchy & Survey Mapping
═══════════════════════════════════════════════════════════════════════════
Source: org_hierarchy Google Sheet (7 sheets) + survey form schemas

Cấu trúc phân cấp workforce:
  BU → Division → Department → Section → Team → Group

Survey groups:
  2A  NV Vận hành Kho (NVXL, NVPH, Admin KHL)
  2B  Quản lý Tuyến đầu (AM, OM, Supervisor, TBC, Team Leader)
  3A  NV Văn phòng / Hỗ trợ – Indirect HO
  3B  Manager / Senior Manager & Director HO
  1A  Shipper (App Driver – chưa có data)
  1B  Tài xế GXT (App Driver – chưa có data)
═══════════════════════════════════════════════════════════════════════════
"""
import unicodedata
import re

# ─────────────────────────────────────────────────────────────────────────────
# 1. CANONICAL VÙNG LIST (14 Vùng + 4 Sorting Centers)
# ─────────────────────────────────────────────────────────────────────────────
VUNG_LIST = [
    "Vùng HNO", "Vùng DSH", "Vùng XBG", "Vùng DBB",
    "Vùng TBB", "Vùng TNT", "Vùng BTB", "Vùng TTB",
    "Vùng TNG", "Vùng NTB", "Vùng DNB", "Vùng TNB",
    "Vùng HCM", "Vùng ĐCL",
    "Xuyên Á Sorting", "M12 Sorting", "Đài Tư Sorting", "Hưng Yên Sorting",
]

# Map: tên form → canonical
# Key = giá trị xuất hiện trong cột "Bạn thuộc Vùng nào?" của survey
VUNG_FORM_TO_CANONICAL = {
    "Vùng Hà Nội (HNO)":                        "Vùng HNO",
    "Vùng Đồng Bằng Sông Hồng (DSH)":           "Vùng DSH",
    "Vùng Xuyên Biên Giới (XBG)":               "Vùng XBG",
    "Vùng Đông Bắc Bộ (DBB)":                   "Vùng DBB",
    "Vùng Tây Bắc Bộ (TBB)":                    "Vùng TBB",
    "Vùng Tây Nam Thủ Đô (TNT)":                "Vùng TNT",
    "Vùng Bắc Trung Bộ (BTB)":                  "Vùng BTB",
    "Vùng Trung Trung Bộ (TTB)":                "Vùng TTB",
    "Vùng Tây Nguyên (TNG)":                    "Vùng TNG",
    "Vùng Nam Trung Bộ (NTB)":                  "Vùng NTB",
    "Vùng Đông Nam Bộ (DNB)":                   "Vùng DNB",
    "Vùng Tây Nam Bộ (TNB)":                    "Vùng TNB",
    "Vùng Hồ Chí Minh (HCM)":                  "Vùng HCM",
    "Vùng Đồng Bằng Sông Cửu Long (DCL)":      "Vùng ĐCL",
    "Vùng Đồng Bằng Sông Cửu Long (ĐCL)":      "Vùng ĐCL",
    # Short codes (fallback)
    "HNO": "Vùng HNO", "DSH": "Vùng DSH", "XBG": "Vùng XBG",
    "DBB": "Vùng DBB", "TBB": "Vùng TBB", "TNT": "Vùng TNT",
    "BTB": "Vùng BTB", "TTB": "Vùng TTB", "TNG": "Vùng TNG",
    "NTB": "Vùng NTB", "DNB": "Vùng DNB", "TNB": "Vùng TNB",
    "HCM": "Vùng HCM", "DCL": "Vùng ĐCL", "ĐCL": "Vùng ĐCL",
}

# Map: tên form KTC → canonical Sorting
KTC_FORM_TO_CANONICAL = {
    "KTC Xuyên Á":    "Xuyên Á Sorting",
    "KTC M12":        "M12 Sorting",
    "KTC Đài Tư":     "Đài Tư Sorting",
    "TTTC Hưng Yên":  "Hưng Yên Sorting",
    "KTC Dương Xá":   "Đài Tư Sorting",   # Dương Xá thuộc cụm Đài Tư
    "Xuyên Á Sorting": "Xuyên Á Sorting",
    "M12 Sorting":     "M12 Sorting",
    "Đài Tư Sorting":  "Đài Tư Sorting",
    "Hưng Yên Sorting":"Hưng Yên Sorting",
}

# Map: workforce section_name → canonical Vùng
WF_SECTION_TO_VUNG = {
    "HNO Region": "Vùng HNO",
    "DSH Region": "Vùng DSH",
    "XBG Region": "Vùng XBG",
    "DBB Region": "Vùng DBB",
    "TBB Region": "Vùng TBB",
    "TNT Region": "Vùng TNT",
    "BTB Region": "Vùng BTB",
    "TTB Region": "Vùng TTB",
    "TNG Region": "Vùng TNG",
    "NTB Region": "Vùng NTB",
    "DNB Region": "Vùng DNB",
    "TNB Region": "Vùng TNB",
    "HCM Region": "Vùng HCM",
    "ĐCL Region": "Vùng ĐCL",
    "DCL Region": "Vùng ĐCL",
    # Sorting centers
    "Xuyên Á Sorting Centers": "Xuyên Á Sorting",
    "XASC":                    "Xuyên Á Sorting",
    "M12 Sorting Centers":     "M12 Sorting",
    "Đài Tư Sorting Centers":  "Đài Tư Sorting",
    "DTSC":                    "Đài Tư Sorting",
    "Hưng Yên Sorting Centers":"Hưng Yên Sorting",
    "HYSC":                    "Hưng Yên Sorting",
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. GXT (Freight B2B) SECTIONS
# ─────────────────────────────────────────────────────────────────────────────
GXT_FORM_OPTIONS = [
    "Vận hành B2B HN",
    "Vận hành B2B Miền Bắc 1",
    "Vận hành B2B Miền Bắc 2",
    "Vận hành B2B Miền Bắc 3",
    "Vận hành B2B Miền Trung",
    "Vận hành B2B Miền Đông",
    "Vận hành B2B Miền Tây",
    "Vận hành B2B HCM",
]

GXT_FORM_TO_WF_SECTION = {
    "Vận hành B2B HN":          "B2B Operations Department - HN",
    "Vận hành B2B Miền Bắc 1":  "B2B Operations Department - North 1",
    "Vận hành B2B Miền Bắc 2":  "B2B Operations Department - North 2",
    "Vận hành B2B Miền Bắc 3":  "B2B Operations Department - North 3",
    "Vận hành B2B Miền Trung":  "B2B Operations Department - Central",
    "Vận hành B2B Miền Đông":   "B2B Operations Department - Eastern",
    "Vận hành B2B Miền Tây":    "B2B Operations Department - Western",
    "Vận hành B2B HCM":         "B2B Operations Department - HCM",
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. WAREHOUSE / FULFILLMENT
# ─────────────────────────────────────────────────────────────────────────────
WAREHOUSE_FORM_OPTIONS = [
    "Bộ Phận Dịch Vụ Kho Vận Miền Nam",
    "Bộ Phận Dịch Vụ Kho Vận Miền Bắc",
]


# ─────────────────────────────────────────────────────────────────────────────
# 4. HO DIVISIONS (3A & 3B)
# ─────────────────────────────────────────────────────────────────────────────
# Tên xuất hiện trong form → division_name trong workforce
HO_DIVISION_FORM_TO_WF = {
    "Giao Hàng Nặng - Freight Project":                          "Freight Project",
    "Khối Công Nghệ - Technology Division":                      "Technology Division",
    "Khối Khách Hàng - Customer Division":                       "Customer Division",
    "Khối Nhân Lực - Human Resource Division":                   "Human Resource Division",
    "Khối Tài Chính - Finance Division":                         "Finance Division",
    "Khối Thị Trường - Market Division":                         "Market Division",
    "Phòng AI Cốt Lõi & Nền Tảng Dữ Liệu - Core AI & Data Platform Department": "Core AI & Data Platform Department",
    "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)":           "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)",
    "Internal Audit & Legal & CEO Office":                       "General Management Department",
    "Phòng Kinh Doanh Khách Hàng Lớn (KA)":                    "Phòng Kinh Doanh Khách Hàng Lớn (KA)",
    "Phòng Sản Phẩm (Product Department)":                      "Phòng Sản Phẩm (Product)",
    "Phòng Vận Tải Xuyên Biên Giới (Cross Border Department)":  "Phòng Vận Tải Xuyên Biên Giới",
    # Short names (fallback)
    "Giao Hàng Nặng":     "Freight Project",
    "Khối Công Nghệ":     "Technology Division",
    "Khối Khách Hàng":    "Customer Division",
    "Khối Nhân Lực":      "Human Resource Division",
    "Khối Tài Chính":     "Finance Division",
    "Khối Thị Trường":    "Market Division",
}

# Departments per division (for 3A/3B sub-questions)
HO_DIVISION_TO_DEPTS = {
    "Freight Project": [
        "Phòng Dự Án Kho", "Phòng Giải Pháp Vận Hành", "Phòng Quản Lý Chất Lượng",
    ],
    "Technology Division": [
        "Warehouse & Sorting Department", "Quality Engineering Department",
        "Customer Management Department", "Frontend & Common Services Department",
        "Network System Department", "Technology Operations Department",
        "System Operations Department", "Pick up & Delivery Department",
        "AIgility Department",
    ],
    "Customer Division": [
        "Phòng Phát Triển Kinh Doanh Khách Hàng Lớn (KA BD)",
        "Phòng Phát Triển Kinh Doanh Khách Hàng Vừa Và Nhỏ (SME)",
        "Phòng Tiếp Thị (Marketing)",
    ],
    "Human Resource Division": [
        "Compensation & Benefits Department", "Total Rewards Department",
        "Employee Experience Department", "Employee Well-Being Department",
        "Succession Pipeline Department", "Learning & Development Department",
        "Office Admin Department", "HRBP Freight", "HRBP Non-Tech",
        "HRBP Pro Tech", "HRBP Sorting Centers & Functional Department",
        "HRBP Regions Department",
        "HNO Region HR Team", "DSH Region HR Team", "TBB Region HR Team",
        "XBG Region HR Team", "TNT Region HR Team", "BTB Region HR Team",
        "TTB Region HR Team", "NTB Region HR Team", "DNB Region HR Team",
        "TNB Region HR Team", "TNG Region HR Team", "HCM Region HR Team",
        "ĐCL Region HR Team", "DTSC HR Team", "HYSC HR Team",
        "XASC HR Team", "M12 HR Team",
    ],
    "Finance Division": [
        "Phòng Kế Toán", "Phòng Quản Lý Tài sản & Hạ Tầng", "Phòng Tài Chính",
    ],
    "Market Division": [
        "Phòng Mạng Lưới (Network)", "Phòng Chiến Lược Vận Hành (OE)",
        "Phòng Phát Triển Mặt Bằng (Site Development)", "Phòng Hoạch Định Năng Lực (CP)",
        # Vùng + Sorting đặc biệt (Market Division cũng có Vùng trong 3A/3B form)
        "Vùng HNO", "Vùng DSH", "Vùng XBG", "Vùng DBB", "Vùng TBB", "Vùng TNT",
        "Vùng BTB", "Vùng TTB", "Vùng TNG", "Vùng NTB", "Vùng DNB", "Vùng TNB",
        "Vùng HCM", "Vùng ĐCL",
        "Xuyên Á Sorting", "M12 Sorting", "Đài Tư Sorting", "Hưng Yên Sorting",
    ],
}

# Danh sách canonical Division cho dropdown
HO_DIVISION_LIST = [
    "Freight Project",
    "Technology Division",
    "Customer Division",
    "Human Resource Division",
    "Finance Division",
    "Market Division",
    "Core AI & Data Platform Department",
    "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)",
    "General Management Department",
    "Phòng Kinh Doanh Khách Hàng Lớn (KA)",
    "Phòng Sản Phẩm (Product)",
    "Phòng Vận Tải Xuyên Biên Giới",
]

# Display names (VN) cho chart labels
HO_DIVISION_DISPLAY = {
    "Freight Project":                            "Dự Án Freight",
    "Technology Division":                        "Khối Công Nghệ",
    "Customer Division":                          "Khối Khách Hàng",
    "Human Resource Division":                    "Khối Nhân Lực",
    "Finance Division":                           "Khối Tài Chính",
    "Market Division":                            "Khối Thị Trường",
    "Core AI & Data Platform Department":         "Phòng AI Cốt Lõi",
    "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)": "Warehouse/Fulfillment",
    "General Management Department":              "Internal Audit & Legal & CEO",
    "Phòng Kinh Doanh Khách Hàng Lớn (KA)":     "KA Department",
    "Phòng Sản Phẩm (Product)":                  "Phòng Sản Phẩm",
    "Phòng Vận Tải Xuyên Biên Giới":             "Cross Border",
}


# ─────────────────────────────────────────────────────────────────────────────
# 5. SURVEY GROUP DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
SURVEY_GROUPS = ["2A", "2B", "3A", "3B"]

SURVEY_GROUP_LABELS = {
    "2A": "NV Vận hành Kho",
    "2B": "Quản lý Tuyến đầu",
    "3A": "NV Văn phòng HO",
    "3B": "Manager / Director HO",
    "1A": "Shipper (chưa có data)",
    "1B": "Tài xế GXT (chưa có data)",
}

# Cấp bậc hợp lệ theo từng nhóm
RANK_BY_GROUP = {
    "2A": ["Staff", "Officer", "Executive", "Specialist"],
    "2B": ["Team Leader - Trưởng nhóm", "Supervisor - Giám sát",
           "Deputy Manager - Phó phòng", "Manager - Trưởng phòng/ Quản lý khu vực"],
    "3A": ["Staff - Nhân viên", "Officer - Nhân viên chính thức",
           "Executive - Nhân viên cấp cao", "Specialist - Chuyên viên",
           "Senior Specialist - Chuyên viên cao cấp", "Expert - Chuyên gia",
           "Team Leader - Trưởng nhóm", "Supervisor - Giám sát"],
    "3B": ["Expert - Chuyên gia", "Manager - Quản lý",
           "Senior Manager - Quản lý cấp cao", "Director - Giám đốc",
           "Senior Director - Giám đốc cấp cao"],
}


# ─────────────────────────────────────────────────────────────────────────────
# 6. UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    """Normalize: lowercase, strip diacritics, keep alphanumeric only."""
    if not s:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


# Pre-computed normalized lookups
_NORM_VUNG_FORM  = {_norm(k): v for k, v in VUNG_FORM_TO_CANONICAL.items()}
_NORM_KTC_FORM   = {_norm(k): v for k, v in KTC_FORM_TO_CANONICAL.items()}
_NORM_WF_SECTION = {_norm(k): v for k, v in WF_SECTION_TO_VUNG.items()}
_NORM_HO_FORM    = {_norm(k): v for k, v in HO_DIVISION_FORM_TO_WF.items()}
_NORM_GXT_FORM   = {_norm(k): v for k, v in GXT_FORM_TO_WF_SECTION.items()}


def resolve_vung_from_form(form_value: str) -> str | None:
    """Chuẩn hóa giá trị form "Bạn thuộc Vùng nào?" → canonical Vùng."""
    if not form_value or str(form_value).strip() in ("", "nan", "None"):
        return None
    n = _norm(form_value)
    if n in _NORM_VUNG_FORM:
        return _NORM_VUNG_FORM[n]
    # Partial match
    for k, v in _NORM_VUNG_FORM.items():
        if k and (k in n or n in k):
            return v
    return None


def resolve_ktc_from_form(form_value: str) -> str | None:
    """Chuẩn hóa giá trị KTC form → canonical Sorting."""
    if not form_value or str(form_value).strip() in ("", "nan", "None"):
        return None
    n = _norm(form_value)
    if n in _NORM_KTC_FORM:
        return _NORM_KTC_FORM[n]
    for k, v in _NORM_KTC_FORM.items():
        if k and (k in n or n in k):
            return v
    return None


def resolve_vung_from_wf_section(section_name: str) -> str | None:
    """Map workforce section_name → canonical Vùng."""
    if not section_name:
        return None
    n = _norm(section_name)
    if n in _NORM_WF_SECTION:
        return _NORM_WF_SECTION[n]
    for k, v in _NORM_WF_SECTION.items():
        if k and (k in n or n in k):
            return v
    return None


def resolve_ho_division_from_form(form_value: str) -> str | None:
    """Map form division label → canonical workforce division_name."""
    if not form_value or str(form_value).strip() in ("", "nan", "None"):
        return None
    n = _norm(form_value)
    if n in _NORM_HO_FORM:
        return _NORM_HO_FORM[n]
    for k, v in _NORM_HO_FORM.items():
        if k and (k in n or n in k):
            return v
    return None


def resolve_gxt_section_from_form(form_value: str) -> str | None:
    """Map GXT bộ phận form → workforce section_name."""
    if not form_value or str(form_value).strip() in ("", "nan", "None"):
        return None
    n = _norm(form_value)
    if n in _NORM_GXT_FORM:
        return _NORM_GXT_FORM[n]
    for k, v in _NORM_GXT_FORM.items():
        if k and (k in n or n in k):
            return v
    return None


if __name__ == "__main__":
    print(f"✓ {len(VUNG_LIST)} Vùng/Sorting")
    print(f"✓ {len(HO_DIVISION_LIST)} HO Divisions")
    print(f"✓ resolve_vung_from_form('Vùng Hà Nội (HNO)') =", resolve_vung_from_form("Vùng Hà Nội (HNO)"))
    print(f"✓ resolve_ho_division_from_form('Khối Công Nghệ - Technology Division') =",
          resolve_ho_division_from_form("Khối Công Nghệ - Technology Division"))
    print(f"✓ resolve_ktc_from_form('KTC Xuyên Á') =", resolve_ktc_from_form("KTC Xuyên Á"))