"""
═══════════════════════════════════════════════════════════════════════════
GHN Organization Hierarchy — Canonical Mapping
═══════════════════════════════════════════════════════════════════════════
Nguồn: List_Departments.xlsx (12 Khối, 75 quan hệ Khối ↔ Phòng ban)

Module này cung cấp 3 thứ:
  1. KHOI_LIST           : Danh sách 12 Khối canonical (thứ tự hiển thị)
  2. DEPT_TO_KHOI        : dict {phòng ban → khối}  — để fill ngược workforce
  3. KHOI_TO_DEPTS       : dict {khối → [phòng ban,...]}
  4. VUNG_LIST           : Danh sách 14 Vùng + 4 Sorting center
  5. resolve_khoi()      : Hàm suy ra Khối từ tên Phòng ban (có fuzzy)
═══════════════════════════════════════════════════════════════════════════
"""
import unicodedata
import re

# ─── DỮ LIỆU CANONICAL (dump từ List_Departments.xlsx) ──────────────────────
KHOI_TO_DEPTS = {
    "Dự Án Freight": [
        "Phòng Dự Án Kho",
        "Phòng Giải Pháp Vận Hành",
        "Phòng Quản Lý Chất Lượng",
    ],
    "Khối Công Nghệ": [
        "Warehouse & Sorting Department",
        "Quality Engineering Department",
        "Customer Management Department",
        "Frontend & Common Services Department",
        "Network System Department",
        "Technology Operations Department",
        "System Operations Department",
        "Pick up & Delivery Department",
        "AIgility Department",
    ],
    "Khối Khách Hàng": [
        "Phòng Phát Triển Kinh Doanh Khách Hàng Lớn (KA BD)",
        "Phòng Phát Triển Kinh Doanh Khách Hàng Vừa Và Nhỏ (SME)",
        "Phòng Tiếp Thị (Marketing)",
    ],
    "Khối Nhân Lực": [
        "Compensation & Benefits Department",
        "Total Rewards Department",
        "Employee Experience Department",
        "Employee Well-Being Department",
        "Succession Pipeline Department",
        "Learning & Development Department",
        "Office Admin Department",
        "HRBP Freight",
        "HRBP Non-Tech",
        "HRBP Pro Tech",
        "HRBP Sorting Centers & Functional Department",
        "HRBP Regions Department",
        "HNO Region HR Team",
        "DSH Region HR Team",
        "TBB Region HR Team",
        "XBG Region HR Team",
        "TNT Region HR Team",
        "BTB Region HR Team",
        "TTB Region HR Team",
        "NTB Region HR Team",
        "DNB Region HR Team",
        "TNB Region HR Team",
        "TNG Region HR Team",
        "HCM Region HR Team",
        "ĐCL Region HR Team",
        "DTSC HR Team",
        "HYSC HR Team",
        "XASC HR Team",
        "M12 HR Team",
    ],
    "Khối Tài Chính": [
        "Phòng Kế Toán",
        "Phòng Quản Lý Tài sản & Hạ Tầng",
        "Phòng Tài Chính",
    ],
    "Khối Thị Trường": [
        "Phòng Mạng Lưới (Network)",
        "Phòng Chiến Lược Vận Hành (OE)",
        "Phòng Phát Triển Mặt Bằng (Site Development)",
        "Phòng Hoạch Định Năng Lực (CP)",
    ],
    "Phòng AI Cốt Lõi & Nền Tảng Dữ Liệu": [
        "Phòng AI Cốt Lõi & Nền Tảng Dữ Liệu",
    ],
    "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)": [
        "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)",
    ],
    "Internal Audit & Legal & CEO Office": [
        "Phòng Kiểm Toán Nội Bộ",
        "Phòng Pháp Chế",
        "Phòng Quản Trị",
        "Internal Audit & Legal & CEO Office",
    ],
    "Phòng Kinh Doanh Khách Hàng Lớn (KA)": [
        "Phòng Kinh Doanh Khách Hàng Lớn (KA)",
        "PHÒNG KINH DOANH KHÁCH HÀNG LỚN",
    ],
    "Phòng Sản Phẩm (Product)": [
        "Phòng Sản Phẩm (Product)",
        "Phòng Sản Phẩm",
    ],
    "Phòng Vận Tải Xuyên Biên Giới": [
        "Phòng Vận Tải Xuyên Biên Giới",
    ],
    "Phòng Công Nghệ & Sản Phẩm Giao Hàng Nặng (GXT)": [
        "Phòng Công Nghệ & Sản Phẩm Giao Hàng Nặng",
    ],
}

# Thứ tự hiển thị Khối trong dropdown / charts
KHOI_LIST = list(KHOI_TO_DEPTS.keys())

# Danh sách Vùng (thuộc Khối Thị Trường theo file nhưng là chiều độc lập khi lọc)
VUNG_LIST = [
    "Vùng HNO", "Vùng DSH", "Vùng XBG", "Vùng DBB",
    "Vùng TBB", "Vùng TNT", "Vùng BTB", "Vùng TTB",
    "Vùng TNG", "Vùng NTB", "Vùng DNB", "Vùng TNB",
    "Vùng HCM", "Vùng ĐCL",
    "Xuyên Á Sorting", "M12 Sorting", "Đài Tư Sorting", "Hưng Yên Sorting",
]

# ─── Reverse index: Phòng ban → Khối ────────────────────────────────────────
DEPT_TO_KHOI = {}
for khoi, depts in KHOI_TO_DEPTS.items():
    for d in depts:
        DEPT_TO_KHOI[d] = khoi


# ─── Fuzzy resolver ─────────────────────────────────────────────────────────
def _norm(s):
    """Normalize: lowercase, strip diacritics, keep alphanumeric only."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

# Pre-compute normalized lookup
_NORM_DEPT_TO_KHOI = {_norm(d): k for d, k in DEPT_TO_KHOI.items()}
_NORM_KHOI_TO_CANONICAL = {_norm(k): k for k in KHOI_LIST}


def resolve_khoi(dept_name=None, khoi_name=None):
    """
    Suy ra tên Khối canonical từ input.
    - Nếu khoi_name khớp chính xác (sau normalize) → trả về canonical
    - Nếu dept_name khớp chính xác → trả về Khối chứa phòng đó
    - Không khớp → trả về None
    """
    # Ưu tiên khoi_name nếu có
    if khoi_name is not None and str(khoi_name).strip():
        n = _norm(khoi_name)
        if n in _NORM_KHOI_TO_CANONICAL:
            return _NORM_KHOI_TO_CANONICAL[n]
    # Fall back: dept_name
    if dept_name is not None and str(dept_name).strip():
        n = _norm(dept_name)
        if n in _NORM_DEPT_TO_KHOI:
            return _NORM_DEPT_TO_KHOI[n]
    return None


def resolve_vung(vung_input):
    """Chuẩn hóa tên Vùng về canonical (hoặc None)."""
    if vung_input is None or str(vung_input).strip() == "":
        return None
    
    vi = str(vung_input).strip()
    vi = vi.replace("Cụm Kho Trung Chuyển ", "").replace("KTC ", "").replace("TTTC ", "")
    n = _norm(vi)
    
    for v in VUNG_LIST:
        if _norm(v) == n or n in _norm(v) or _norm(v) in n:
            return v
    return None


if __name__ == "__main__":
    # Self-check
    print(f"✓ Loaded {len(KHOI_LIST)} Khối, {len(DEPT_TO_KHOI)} Phòng ban mappings, {len(VUNG_LIST)} Vùng")
    # Test resolver
    print("\nTest resolve_khoi:")
    print("  'phong ke toan' →", resolve_khoi(dept_name="phong ke toan"))
    print("  'Khối Công Nghệ' →", resolve_khoi(khoi_name="Khối Công Nghệ"))
    print("  'HRBP Freight' →", resolve_khoi(dept_name="HRBP Freight"))
    print("\nTest resolve_vung:")
    print("  'HNO' →", resolve_vung("HNO"))
    print("  'vùng hcm' →", resolve_vung("vùng hcm"))