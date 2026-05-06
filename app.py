"""
GHN EES 2026 — Survey Progress Dashboard
Fix:
  1. wf_lookup tìm trên TẤT CẢ cột string của workforce (không chỉ section_name_vn)
  2. Duy nhất 1 định nghĩa _find_col
  3. MAP_2AB: sau khi map survey_val → wf_sec_vn, join WF trên tất cả cột string để lấy đúng division/dept
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta, timezone
import unicodedata, re

# ══════════════════════════════════════════════════════════════
ICT = timezone(timedelta(hours=7))
# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="GHN EES 2026 · Survey Progress",
    page_icon="./img/Logo_EES.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

C = {
    "navy":   "#0A1F44", "navy2":  "#132A5C",
    "orange": "#FF5200", "orange2":"#CC4100",
    "blue":   "#006FAD",
    "slate":  "#F0F2F5", "bg":     "#FFFFFF",
    "text":   "#2E3440", "sub":    "#5A6272",
    "muted":  "#9BA3B2", "border": "#DDE1E8",
    "line":   "#E8EAF0",
    "green":  "#0D6E3A", "green2": "#E6F4ED",
    "red":    "#C0392B", "red2":   "#FDECEA",
}

LANG = {
    "VI": {
        "page_sub":       "Tiến độ tham gia khảo sát theo Division, Department và Section.",
        "updated":        "Cập nhật lần cuối",
        "refresh":        "Làm mới",
        "auto_refresh":   "Tự động làm mới mỗi 15 phút",
        "only_active":    "Chỉ nhân sự đang làm (status = 1)",
        "survey_group":   "Nhóm khảo sát",
        "division_lbl":   "Division",
        "dept_lbl":       "Department",
        "section_lbl":    "Section / Vùng",
        "date_range":     "Khoảng thời gian",
        "sidebar_note":   "Filter: Division → Department → Section.",
        "viewing":        "Đang xem",
        "kpi_hc":         "Tổng Nhân Sự",    "kpi_hc_sub":      "HC của nhóm đã chọn",
        "kpi_done":       "Đã Tham Gia",      "kpi_done_sub":    "trên tổng HC",
        "kpi_pending":    "Chưa Tham Gia",    "kpi_pending_sub": "HC − Response",
        "kpi_today":      "Hôm Nay",          "kpi_today_sub":   "so với hôm qua",
        "tab_div":  "Theo Division",    "tab_dept":  "Theo Department",
        "tab_sec":  "Theo Section",     "tab_trend": "Xu hướng theo ngày",
        "sec_div":  "Tiến độ theo Division",
        "sec_dept": "Tiến độ theo Department",
        "sec_sec":  "Tiến độ theo Section / Vùng",
        "sec_trend":"Response theo ngày — tích lũy & mới",
        "top_n_dept":"Top N phòng ban",  "top_n_sec": "Top N section",
        "col_hc":"HC", "col_done":"Đã làm", "col_pending":"Chưa làm",
        "col_rate":"Tỷ lệ", "col_total":"Tổng cộng",
        "chart_pct":"% Hoàn thành", "chart_avg":"TB",
        "chart_new":"Mới trong ngày", "chart_cum":"% Tích lũy",
        "chart_new_y":"Response mới / ngày", "chart_cum_y":"% Tích lũy",
        "no_data":"Không có dữ liệu", "no_ts":"Chưa có timestamp hợp lệ",
        "divisions":"divisions", "departments":"phòng ban", "sections":"sections",
        "tab_dist": "Phân bổ",
        "sec_dist": "Phân bố tỷ lệ tham gia theo Phòng ban",
        "dist_rate": "Tỷ lệ tham gia",
        "dist_dept_cnt": "Số lượng phòng ban",
        "dist_stats": "Thống kê Phòng Ban",
        "dist_total": "Tổng số phòng ban",
        "dist_mean": "Trung bình (Mean)",
        "dist_median": "Trung vị (Median)",
        "dist_exc": "Hoàn thành xuất sắc",
        "dist_poor": "Chưa đạt tiến độ",
        "dist_unit": "đơn vị",
        "dist_hover": "Phòng ban",
        "group_labels": {
            "1A":"Nhóm NV Giao nhận",
            "1B":"Nhóm Tài xế Vận tải",
            "2A":"Nhóm Nhân viên Vận hành Kho",
            "2B":"Nhóm Quản lý Tuyến đầu",
            "3A":"Nhóm Nhân viên Văn phòng HO",
            "3B":"Manager / Director HO",
        },
        "footer":"Báo cáo Tiến độ Khảo sát · EX Team",
        "render":"Render",
    },
    "EN": {
        "page_sub":       "Survey participation progress by Division, Department and Section.",
        "updated":        "Last updated",
        "refresh":        "Refresh",
        "auto_refresh":   "Auto-refreshes every 15 mins",
        "only_active":    "Active employees only (status = 1)",
        "survey_group":   "Survey group",
        "division_lbl":   "Division",
        "dept_lbl":       "Department",
        "section_lbl":    "Section / Region",
        "date_range":     "Date range",
        "sidebar_note":   "HC from workforce, mapped via Mapping sheet.<br>Filter: Division → Department → Section.",
        "viewing":        "Viewing",
        "kpi_hc":         "Total Headcount",  "kpi_hc_sub":      "HC of selected groups",
        "kpi_done":       "Participated",      "kpi_done_sub":    "of total HC",
        "kpi_pending":    "Not Yet",           "kpi_pending_sub": "HC − Response",
        "kpi_today":      "Today",             "kpi_today_sub":   "vs yesterday",
        "tab_div":  "By Division",      "tab_dept":  "By Department",
        "tab_sec":  "By Section",       "tab_job":   "By Job Title", "tab_trend": "Daily Trend",
        "sec_div":  "Progress by Division",
        "sec_dept": "Progress by Department",
        "sec_sec":  "Progress by Section / Region",
        "sec_job":  "Progress by Job Title",
        "sec_trend":"Daily response — cumulative & new",
        "top_n_dept":"Top N departments", "top_n_sec":"Top N sections",
        "col_hc":"HC", "col_done":"Submitted", "col_pending":"Pending",
        "col_rate":"Rate", "col_total":"Total",
        "chart_pct":"% Completion", "chart_avg":"Avg",
        "chart_new":"New today", "chart_cum":"% Cumulative",
        "chart_new_y":"New responses / day", "chart_cum_y":"% Cumulative",
        "no_data":"No data available", "no_ts":"No valid timestamps found",
        "divisions":"divisions", "departments":"departments", "sections":"sections",
        "tab_dist": "Distribution",
        "sec_dist": "Participation Distribution by Department",
        "dist_rate": "Participation Rate",
        "dist_dept_cnt": "Number of Departments",
        "dist_stats": "Department Statistics",
        "dist_total": "Total Departments",
        "dist_mean": "Mean",
        "dist_median": "Median",
        "dist_exc": "Excellent",
        "dist_poor": "Behind Schedule",
        "dist_unit": "units",
        "dist_hover": "Departments",
        "group_labels": {
            "1A":"Delivery Staff",
            "1B":"Truck Drivers",
            "2A":"Warehouse Operations Staff",
            "2B":"Frontline Managers",
            "3A":"HO Office Staff",
            "3B":"HO Manager / Director",
        },
        "footer":"Survey Progress Dashboard · EX Team",
        "render":"Render",
    },
}
ALL_GROUPS = ["1A", "1B", "2A", "2B", "3A", "3B"]

if "lang" not in st.session_state:
    st.session_state["lang"] = "VI"

def T(key):
    return LANG[st.session_state["lang"]][key]


# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@font-face {{
  font-family:'SVN-Helvetica Now';font-style:normal;font-weight:400;font-display:swap;
  src:url('./app/static/fonts/SVN-HelveticaNowDisplay-Regular.ttf') format('truetype');
}}
@font-face {{
  font-family:'SVN-Helvetica Now';font-style:normal;font-weight:500;font-display:swap;
  src:url('./app/static/fonts/SVN-HelveticaNowDisplay-Medium.ttf') format('truetype');
}}
@font-face {{
  font-family:'SVN-Helvetica Now';font-style:normal;font-weight:700;font-display:swap;
  src:url('./app/static/fonts/SVN-HelveticaNowDisplay-Bold.ttf') format('truetype');
}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"],.stApp{{
    background-color:{C['slate']}!important;color:{C['text']}!important;color-scheme:light!important;}}
[data-testid="stHeader"]{{background-color:transparent!important;}}
html,body,[class*="css"]{{font-family:'SVN-Helvetica Now',system-ui,sans-serif!important;
    color:{C['text']}!important;-webkit-font-smoothing:antialiased;}}
.stApp{{background:{C['slate']};}}
.block-container{{max-width:100%;padding:0 2rem 3rem;}}
#MainMenu,footer{{visibility:hidden;}}
[data-testid="stSidebar"][aria-expanded="false"]{{
    margin-left:0!important;min-width:0!important;width:0!important;overflow:hidden!important;}}
[data-testid="collapsedControl"]{{
    display:flex!important;visibility:visible!important;position:fixed!important;
    top:.5rem!important;left:.5rem!important;z-index:999999!important;
    color:{C['navy']}!important;background:{C['bg']}!important;
    border:1px solid {C['border']}!important;border-radius:6px!important;
    box-shadow:0 2px 8px rgba(0,0,0,.1)!important;padding:4px!important;}}
[data-testid="collapsedControl"] button{{color:{C['navy']}!important;}}
[data-testid="collapsedControl"] svg{{fill:{C['navy']}!important;stroke:{C['navy']}!important;}}
[data-testid="stSidebar"]{{background:#f8fafc;border-right:1px solid {C['border']};}}
[data-testid="stSidebar"] *{{color:{C['navy']}!important;}}
[data-testid="stSidebar"] .stMultiSelect>label,
[data-testid="stSidebar"] .stCheckbox>label,
[data-testid="stSidebar"] .stDateInput>label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
    color:{C['sub']}!important;font-size:.68rem!important;
    font-weight:700!important;text-transform:uppercase!important;letter-spacing:.1em!important;
}}
[data-testid="stSidebar"] [data-testid="stPills"] button {{
    font-family:'SVN-Helvetica Now',sans-serif!important;
    font-weight:600!important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="input"] input,
[data-testid="stSidebar"] [data-baseweb="base-input"]{{
    background:white!important;
    border-color:{C['line']}!important;color:{C['navy']}!important;border-radius:4px!important;}}
[data-testid="stSidebar"] .stButton>button[kind="secondary"],
[data-testid="stSidebar"] .stButton>button[kind="primary"]{{
    background:white!important;color:{C['navy']}!important;border:1px solid {C['line']}!important;
    border-radius:4px!important;font-family:'SVN-Helvetica Now',sans-serif!important;
    font-size:.75rem!important;font-weight:600!important;
    padding:.3rem .6rem!important;width:100%!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{border-color:{C['orange']}!important;color:{C['orange']}!important;}}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{{background:{C['orange']}!important;color:white!important;border-color:{C['orange']}!important;}}
[data-testid="stSidebar"] .stButton>button[kind="tertiary"]{{
    padding:0!important; min-height:0!important; line-height:1!important; border:none!important;
    color:{C['muted']}!important; font-size:1.2rem!important; margin-top:0.15rem!important; background:transparent!important;}}
[data-testid="stSidebar"] .stButton>button[kind="tertiary"]:hover{{color:{C['orange']}!important; border:none!important;}}
.sb-logo{{font-family:'SVN-Helvetica Now',sans-serif;font-size:1.5rem;font-weight:700;
    color:{C['navy']}!important;letter-spacing:-.02em;text-transform:uppercase;
    padding:1.5rem 0 1rem;border-bottom:1px solid {C['line']};margin-bottom:1rem;}}
.sb-logo span{{color:{C['orange']}!important;}}
.sb-div{{border:none;border-top:1px solid {C['line']};margin:1rem 0;}}
.sb-note{{font-size:.65rem;color:{C['sub']};line-height:1.7;margin-top:.5rem;}}
.stTabs [data-baseweb="tab-list"]{{background:transparent!important;
    border-bottom:2px solid {C['line']}!important;gap:0!important;padding:0!important;}}
.stTabs [data-baseweb="tab"]{{
    font-family:'SVN-Helvetica Now',sans-serif!important;font-size:.82rem!important;
    font-weight:700!important;letter-spacing:.08em!important;text-transform:uppercase!important;
    color:{C['muted']}!important;padding:.85rem 1.5rem!important;
    border-bottom:3px solid transparent!important;margin-bottom:-2px!important;
    transition:all .2s!important;background:transparent!important;}}
.stTabs [aria-selected="true"]{{color:{C['navy']}!important;border-bottom-color:{C['orange']}!important;}}
.stTabs [data-baseweb="tab-panel"]{{padding:0!important;background:transparent!important;}}
[data-testid="stSlider"]>label{{
    font-size:.72rem!important;font-weight:600!important;
    text-transform:uppercase!important;letter-spacing:.1em!important;color:{C['sub']}!important;}}
.site-header{{background:{C['navy']};padding:0;margin:0 -2rem 2rem;
    display:flex;align-items:stretch;min-height:120px;position:relative;overflow:hidden;}}
.site-header::before{{content:"";position:absolute;top:0;left:0;right:0;bottom:0;
    background:linear-gradient(135deg,{C['navy2']} 0%,{C['navy']} 60%);z-index:0;}}
.site-header::after{{content:"";position:absolute;right:-60px;top:-40px;
    width:320px;height:220px;background:{C['orange']};opacity:.06;border-radius:50%;z-index:0;}}
.hdr-accent{{width:5px;background:{C['orange']};flex-shrink:0;position:relative;z-index:1;}}
.hdr-body{{padding:28px 40px;flex:1;position:relative;z-index:1;
    display:flex;justify-content:space-between;align-items:flex-end;}}
.hdr-label{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.72rem;font-weight:700;
    letter-spacing:.2em;text-transform:uppercase;color:{C['orange']};margin-bottom:10px;}}
.hdr-title{{font-family:'SVN-Helvetica Now',sans-serif;
    font-size:clamp(2.2rem,4vw,3rem);font-weight:700;color:white;
    line-height:1;letter-spacing:-.02em;text-transform:uppercase;margin:0 0 10px;}}
.hdr-title .acc{{color:{C['orange']};}}
.hdr-desc{{font-size:.88rem;color:rgba(255,255,255,0.5);font-weight:400;max-width:540px;line-height:1.6;}}
.hdr-meta{{text-align:right;}}
.hdr-meta .ml{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.65rem;
    letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.35);margin-bottom:4px;}}
.hdr-meta .mv{{font-size:.85rem;font-weight:500;color:rgba(255,255,255,.75);}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;
    background:{C['border']};border:1px solid {C['border']};margin-bottom:2rem;}}
.kpi-cell{{background:{C['bg']};padding:22px 26px;position:relative;}}
.kpi-cell::before{{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:{C['border']};}}
.kpi-cell.kc-navy::before{{background:{C['navy']};}}
.kpi-cell.kc-blue::before{{background:{C['blue']};}}
.kpi-cell.kc-orange::before{{background:{C['orange']};}}
.kpi-cell.kc-green::before{{background:{C['green']};}}
.kpi-lbl{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.7rem;font-weight:700;
    letter-spacing:.14em;text-transform:uppercase;color:{C['muted']};margin-bottom:12px;}}
.kpi-val{{font-family:'SVN-Helvetica Now',sans-serif;font-size:3rem;font-weight:700;
    line-height:1;letter-spacing:-.03em;color:{C['navy']};margin-bottom:6px;}}
.kpi-cell.kc-blue .kpi-val  {{color:{C['blue']};}}
.kpi-cell.kc-orange .kpi-val{{color:{C['orange']};}}
.kpi-cell.kc-green .kpi-val {{color:{C['green']};}}
.kpi-sub{{font-size:.8rem;color:{C['sub']};font-weight:400;line-height:1.4;}}
.dp{{color:{C['green']};font-weight:700;}} .dn{{color:{C['red']};font-weight:700;}} .dz{{color:{C['muted']};}}
.scard{{background:{C['bg']};border:1px solid {C['border']};margin-bottom:1.5rem;}}
.scard-head{{padding:16px 26px;border-bottom:1px solid {C['line']};
    display:flex;align-items:center;gap:.8rem;}}
.scard-head .sh-t{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.78rem;
    font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:{C['navy']};white-space:nowrap;}}
.scard-head .sh-r{{flex:1;height:1px;background:{C['line']};}}
.scard-head .sh-meta{{font-size:.75rem;color:{C['muted']};white-space:nowrap;}}
.scard-body{{padding:22px 26px;}}
.dtbl{{width:100%;border-collapse:collapse;font-size:.83rem;}}
.dtbl thead tr{{border-bottom:2px solid {C['navy']};}}
.dtbl th{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.68rem;font-weight:700;
    letter-spacing:.12em;text-transform:uppercase;color:{C['sub']};
    padding:8px 6px 10px;text-align:left;white-space:nowrap;background:transparent;}}
.dtbl th.r{{text-align:right;}}
.dtbl tbody tr{{border-bottom:1px solid {C['line']};transition:background .1s;}}
.dtbl tbody tr:hover{{background:{C['slate']};}}
.dtbl td{{padding:8px 6px;vertical-align:middle;color:{C['text']};}}
.dtbl td.r{{text-align:right;font-variant-numeric:tabular-nums;font-size:.82rem;}}
.dtbl td.nm{{font-weight:500;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.dtbl .foot td{{border-top:2px solid {C['navy']};padding-top:11px;font-weight:700;color:{C['navy']};background:transparent;}}
.dtbl .rnk{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.78rem;font-weight:700;
    color:{C['muted']};text-align:right;width:28px;}}
.prog-w{{height:5px;background:{C['line']};border-radius:1px;overflow:hidden;min-width:60px;}}
.prog-f{{height:5px;border-radius:1px;transition:width .3s ease;}}
.pbg{{display:inline-block;font-family:'SVN-Helvetica Now',sans-serif;font-size:.82rem;
    font-weight:700;letter-spacing:.03em;padding:2px 8px;border-radius:2px;}}
.bg-g{{background:{C['green2']};color:{C['green']};}}
.bg-b{{background:#E8F4FD;color:{C['blue']};}}
.bg-r{{background:{C['red2']};color:{C['red']};}}
.bg-z{{background:{C['slate']};color:{C['muted']};}}
.no-data{{text-align:center;padding:48px 20px;color:{C['muted']};
    font-family:'SVN-Helvetica Now',sans-serif;font-size:1rem;
    letter-spacing:.1em;text-transform:uppercase;}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS — duy nhất 1 định nghĩa mỗi hàm
# ══════════════════════════════════════════════════════════════
WF_SHEET_ID = "1pyNwximXg0aZzahEroGdenxnUIRe1XWbnMy_YRULAn0"
SURVEY_IDS  = {
    "2A": "1AS22mEX2_kezYRGsWIDHGEXNQAKD4xG_4W8_jtBDA1o",
    "2B": "1hmATsOmJ9a1WmZsBMSlITC3UH7zAnLRYXqQ2an1ppNo",
    "3A": "1UFtIMOAqZj-uvidePYZiWLiYaq_Lg1rm0ttEJWYowb8",
    "3B": "1E7_G8znrD-ITdvs894e-QUg9AJl7SQS3D6FhyYkeUbc",
}

# Các cột string trong workforce — thứ tự ưu tiên khi search
WF_STR_COLS = [
    "section_name_vn", "section_name",
    "department_name_vn", "department_name",
    "team_name_vn", "team_name",
    "division_name_vn", "division_name",
]

def _url(s): return f"https://docs.google.com/spreadsheets/d/{s}/edit"

def _norm(s):
    s = unicodedata.normalize("NFD", str(s).strip().lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))

def _clean(v):
    if v is None: return None
    s = str(v).strip()
    return None if s in ("", "nan", "None") else s

def _find_col(df: pd.DataFrame, *keywords) -> str | None:
    """Tìm cột đầu tiên trong df có chứa bất kỳ keyword nào (case-insensitive)."""
    for col in df.columns:
        cl = col.lower()
        if any(k.lower() in cl for k in keywords):
            return col
    return None

def pct_badge(p):
    if p>=75: return f'<span class="pbg bg-g">{p:.1f}%</span>'
    if p>=40: return f'<span class="pbg bg-b">{p:.1f}%</span>'
    if p>0:   return f'<span class="pbg bg-r">{p:.1f}%</span>'
    return '<span class="pbg bg-z">—</span>'

def prog_bar(p):
    w = min(p, 100)
    col = C["green"] if p>=75 else C["blue"] if p>=40 else C["orange"] if p>0 else C["line"]
    return f'<div class="prog-w"><div class="prog-f" style="width:{w}%;background:{col}"></div></div>'

def delta_html(v):
    if v>0: return f'<span class="dp">+{v:,}</span>'
    if v<0: return f'<span class="dn">{v:,}</span>'
    return '<span class="dz">—</span>'


# ══════════════════════════════════════════════════════════════
# LOAD WORKFORCE + MAPPING
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=43200, show_spinner="Đang tải Workforce & Mapping…")
def load_workforce_and_mapping() -> tuple[pd.DataFrame, dict, dict]:
    export_url = f"https://docs.google.com/spreadsheets/d/{WF_SHEET_ID}/export?format=xlsx"
    try:
        df_wf = pd.read_excel(export_url, sheet_name="Workforce Data")
        df_map = pd.read_excel(export_url, sheet_name="Mapping")
    except Exception as e:
        st.error(f"Lỗi tải Workforce: {e}")
        df_wf = pd.DataFrame()
        df_map = pd.DataFrame()

    # ── Chuẩn hóa workforce ──
    df_wf = df_wf.dropna(how="all").copy()
    df_wf.columns = [str(c).strip() for c in df_wf.columns]
    for col in WF_STR_COLS + ["bu_name", "survey_group", "jobtitle_name"]:
        if col not in df_wf.columns: df_wf[col] = None
        df_wf[col] = df_wf[col].astype(str).str.strip().replace({"nan":None,"":None,"None":None})
    df_wf["status"] = pd.to_numeric(df_wf.get("status", pd.Series()), errors="coerce")

    # ── Hierarchical Fill to resolve missing classifications ──
    for c_div, c_dept, c_sec in [
        ("division_name_vn", "department_name_vn", "section_name_vn"),
        ("division_name", "department_name", "section_name")
    ]:
        if c_div in df_wf.columns and c_dept in df_wf.columns:
            df_wf[c_dept] = df_wf[c_dept].fillna(df_wf[c_div])
        if c_dept in df_wf.columns and c_sec in df_wf.columns:
            df_wf[c_sec] = df_wf[c_sec].fillna(df_wf[c_dept])

    # Bắt buộc ép Vận hành GXT về Giao Hàng Nặng (Vận hành B2B)
    mask_gxt = (
        df_wf.get("department_name_vn", pd.Series(dtype=str)).str.contains("Vận hành GXT", case=False, na=False) |
        df_wf.get("section_name_vn", pd.Series(dtype=str)).str.contains("Vận hành GXT", case=False, na=False) |
        df_wf.get("department_name", pd.Series(dtype=str)).str.contains("Vận hành GXT", case=False, na=False) |
        df_wf.get("section_name", pd.Series(dtype=str)).str.contains("Vận hành GXT", case=False, na=False) |
        df_wf.get("team_name_vn", pd.Series(dtype=str)).str.contains("Vận hành GXT", case=False, na=False) |
        df_wf.get("team_name", pd.Series(dtype=str)).str.contains("Vận hành GXT", case=False, na=False)
    )
    if "division_name" in df_wf.columns:
        df_wf.loc[mask_gxt, "division_name"] = "Giao Hàng Nặng (Vận hành B2B)"
    if "division_name_vn" in df_wf.columns:
        df_wf.loc[mask_gxt, "division_name_vn"] = "Giao Hàng Nặng (Vận hành B2B)"

    # ── Parse Mapping sheet ──
    MAP_2AB: dict[str, str]            = {}  # sv_val → wf_value (tìm trên tất cả cột)
    MAP_3AB: dict[str, tuple[str,str]] = {}  # sv_val → (wf_col, wf_val)

    if len(df_map) > 0:
        cols = list(df_map.columns)

        # 2A-2B: col0=Survey2A, col1=Survey2B, col2=WF_value
        if len(cols) >= 3:
            sub2 = df_map.iloc[:, [0,1,2]].copy()
            sub2.columns = ["sv2a","sv2b","wf_val"]
            sub2 = sub2.dropna(subset=["wf_val"])
            sub2 = sub2[~sub2["sv2a"].astype(str).str.strip().isin(["Survey-2A",""])]
            for _, r in sub2.iterrows():
                wf = _clean(str(r["wf_val"]))
                if not wf: continue
                for sv_raw in [r["sv2a"], r["sv2b"]]:
                    sv = _clean(str(sv_raw))
                    if sv: MAP_2AB[sv] = wf

        # 3A-3B: col4=Survey, col5=WF_value, col6=WF_column
        if len(cols) >= 7:
            sub3 = df_map.iloc[:, [4,5,6]].copy()
            sub3.columns = ["sv","wf_val","wf_col"]
            sub3 = sub3.dropna(subset=["sv","wf_val","wf_col"])
            sub3 = sub3[~sub3["sv"].astype(str).str.strip().isin(["Survey-3A-3B",""])]
            for _, r in sub3.iterrows():
                sv  = _clean(str(r["sv"]))
                wfv = _clean(str(r["wf_val"]))
                wfc = _clean(str(r["wf_col"]))
                if sv and wfv and wfc:
                    MAP_3AB[sv] = (wfc, wfv)

    return df_wf, MAP_2AB, MAP_3AB


# ══════════════════════════════════════════════════════════════
# BUILD WF LOOKUP — tìm trên TẤT CẢ cột string
# ══════════════════════════════════════════════════════════════
def build_wf_lookup(df_wf: pd.DataFrame) -> tuple[dict, dict]:
    """
    Build two lookups:
    1. Exact lookup: (column, value) -> dict of wf info
    2. Fallback lookup: value -> dict of wf info (first match)
    """
    lookup_exact = {}
    lookup_fallback = {}

    for col in WF_STR_COLS:
        if col not in df_wf.columns: continue
        grp = df_wf[df_wf[col].notna()].groupby(col, dropna=False)
        for val, rows in grp:
            v = str(val).strip()
            if not v or v in ("nan","None",""): continue
            
            r0 = rows.iloc[0]
            info = {
                "wf_division":   r0.get("division_name"),
                "wf_division_vn": r0.get("division_name_vn"),
                "wf_department": r0.get("department_name"),
                "wf_department_vn": r0.get("department_name_vn"),
                "wf_section":    r0.get("section_name"),
                "wf_section_vn": r0.get("section_name_vn"),
                "wf_team":       r0.get("team_name"),
            }
            
            v_norm = _norm(v)
            if (col, v_norm) not in lookup_exact:
                lookup_exact[(col, v_norm)] = info
                
            if v_norm not in lookup_fallback:
                lookup_fallback[v_norm] = info
                
    return lookup_exact, lookup_fallback


# ══════════════════════════════════════════════════════════════
# ENRICH SURVEY → WORKFORCE INFO
# ══════════════════════════════════════════════════════════════
def enrich_survey(df_sv: pd.DataFrame, MAP_2AB: dict, MAP_3AB: dict,
                  lookup_exact: dict, lookup_fallback: dict) -> pd.DataFrame:
    """
    Gắn wf_division/wf_department/wf_section_vn/wf_team vào mỗi row survey.

    Flow:
      2A/2B: sv_label → MAP_2AB → wf_value → lookup_fallback → thông tin WF
      3A/3B: sv_label → MAP_3AB → (wf_col, wf_val) → lookup_exact(wf_col, wf_val) → thông tin WF
    """
    if len(df_sv) == 0:
        for c in ["wf_division","wf_division_vn","wf_department","wf_department_vn","wf_section","wf_section_vn","wf_team"]:
            df_sv[c] = None
        return df_sv

    # Normalized lookup cho fuzzy match
    map2ab_norm = {_norm(k): v for k, v in MAP_2AB.items()}
    map3ab_norm = {_norm(k): v for k, v in MAP_3AB.items()}

    rows = []
    for _, row in df_sv.iterrows():
        sv_val = _clean(str(row.get("sv_label","") or ""))
        grp    = str(row.get("survey_group",""))
        wf_info = {}

        if sv_val:
            sv_norm = _norm(sv_val)
            if grp in ("2A","2B"):
                # MAP_2AB: sv_val → wf_value → lookup
                wf_val = map2ab_norm.get(sv_norm)
                if wf_val:
                    wf_info = lookup_fallback.get(_norm(wf_val), {})
                else:
                    wf_info = lookup_fallback.get(sv_norm, {})

            elif grp in ("3A","3B"):
                candidates = [sv_val]
                if "-" in sv_val: candidates.append(sv_val.split("-")[0].strip())
                if "(" in sv_val: candidates.append(sv_val.split("(")[0].strip())
                
                for cand in candidates:
                    c_norm = _norm(cand)
                    mapping = map3ab_norm.get(c_norm)
                    if mapping:
                        wf_col, wf_val = mapping
                        wf_col_norm = wf_col.strip()
                        wf_info = lookup_exact.get((wf_col_norm, _norm(wf_val)))
                        if not wf_info:
                            wf_info = lookup_fallback.get(_norm(wf_val), {})
                    else:
                        wf_info = lookup_fallback.get(c_norm, {})
                    
                    if wf_info:
                        break

        r = row.to_dict()
        r.update({
            "wf_division":   wf_info.get("wf_division"),
            "wf_division_vn":wf_info.get("wf_division_vn"),
            "wf_department": wf_info.get("wf_department"),
            "wf_department_vn":wf_info.get("wf_department_vn"),
            "wf_section":    wf_info.get("wf_section"),
            "wf_section_vn": wf_info.get("wf_section_vn"),
            "wf_team":       wf_info.get("wf_team"),
        })
        rows.append(r)

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# SURVEY PARSING — chỉ extract timestamp + sv_label
# ══════════════════════════════════════════════════════════════
def _parse_2ab(df: pd.DataFrame, group: str) -> pd.DataFrame:
    """
    2A/2B form structure (exact cols from demo):
      col[7]  'Phòng Ban bạn đang làm việc?' → loại (Vùng / GXT / KTC / Warehouse)
      col[8]  'Bạn thuộc Vùng nào?'          → Vùng cụ thể
      col[9]  'Bạn thuộc KCT/TTCT nào?'      → KTC cụ thể
      col[10] 'Bạn thuộc bộ phận nào?'       → GXT bộ phận
      col[11] 'Warehouse/Fulfillment (KHL)'   → WH bộ phận
    sv_label = giá trị sub-question (cụ thể nhất)
    """
    col_ts   = _find_col(df, "timestamp", "thời gian")
    col_pb   = _find_col(df, "phòng ban")
    col_vung = _find_col(df, "vùng nào")
    col_ktc  = _find_col(df, "ktc", "ttct", "tttc")
    col_gxt  = _find_col(df, "bộ phận nào")
    col_wh   = _find_col(df, "warehouse", "fulfillment", "khl")

    rows = []
    for _, row in df.iterrows():
        ts = pd.to_datetime(row[col_ts], errors="coerce", dayfirst=False) if col_ts else pd.NaT
        pb = _clean(row[col_pb]) if col_pb else None
        sv_label = None

        if pb:
            pl = pb.lower()
            if "warehouse" in pl or "fulfillment" in pl:
                sv_label = _clean(row[col_wh]) if col_wh else None
            elif "giao hàng nặng" in pl or "gxt" in pl:
                sv_label = _clean(row[col_gxt]) if col_gxt else None
            elif ("kho trung chuyển" in pl or "ktc" in pl or "tttc" in pl) \
                    and "vùng" not in pl and "bưu cục" not in pl:
                # Chỉ vào nhánh KTC khi KHÔNG phải "Vùng (Bưu Cục, KTC thuộc Vùng)"
                sv_label = _clean(row[col_ktc]) if col_ktc else None
            else:
                # Vùng (bưu cục, KTC thuộc Vùng) hoặc bất kỳ trường hợp còn lại
                sv_label = _clean(row[col_vung]) if col_vung else None
                
            # Nếu user không điền sub-question hoặc sub-question rỗng, lấy chính pb làm sv_label
            if not sv_label:
                sv_label = pb

        rows.append({"timestamp": ts, "survey_group": group, "sv_label": sv_label})
    return pd.DataFrame(rows)


def _parse_3ab(df: pd.DataFrame, group: str) -> pd.DataFrame:
    """
    3A/3B form structure (exact cols from demo):
      col[7]  'Phòng Ban bạn đang làm việc?' → Division lớn (Khối CT, Khối NL...)
      col[8]  'Bạn thuộc?'                   → Department/Section cụ thể bên trong Division đó
      col[9..13] 'Bạn thuộc?.1 ... .5'       → Sub-sub questions cho các Division khác nhau

    sv_label ưu tiên: col[8] 'Bạn thuộc?' (đây là dept/section cụ thể nhất)
    Nếu không có → fallback col[7] 'Phòng Ban' (tên Division)
    """
    col_ts  = _find_col(df, "timestamp", "thời gian")
    
    # Tìm tất cả các cột Division (phòng ban, khối)
    pb_cols = [
        c for c in df.columns 
        if ("phòng ban" in c.lower() or "khối" in c.lower())
        and "cơ cấu" not in c.lower()
        and "khối lượng" not in c.lower()
    ]

    # col 8..13: 'Bạn thuộc?' và các biến thể .1 .2 .3 .4 .5
    # Tìm tất cả cột "Bạn thuộc?" (không phải câu hỏi survey về gắn bó)
    thuoc_cols = [
        c for c in df.columns
        if "bạn thuộc" in c.lower() and "gắn bó" not in c.lower()
        and "thuộc về" not in c.lower()
    ]

    rows = []
    for _, row in df.iterrows():
        ts = pd.to_datetime(row[col_ts], errors="coerce", dayfirst=False) if col_ts else pd.NaT

        # Lấy giá trị từ các cột "Bạn thuộc?" — lấy giá trị không null đầu tiên
        sv_label = None
        for col in thuoc_cols:
            v = _clean(row[col])
            if v:
                sv_label = v
                break

        # Fallback: lấy Division lớn từ các cột phòng ban / khối
        if not sv_label:
            for c_pb in pb_cols:
                v = _clean(row[c_pb])
                if v:
                    sv_label = v
                    break

        rows.append({"timestamp": ts, "survey_group": group, "sv_label": sv_label})
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def _load_raw_survey(group: str) -> tuple[pd.DataFrame, str | None]:
    if group not in SURVEY_IDS:
        return pd.DataFrame(), None
        
    try:
        conn = st.connection(f"survey_{group}", type=GSheetsConnection)
        df = conn.read(spreadsheet=_url(SURVEY_IDS[group]), worksheet="Form Responses 1", ttl=0)
    except Exception:
        try:
            conn = st.connection(f"survey_{group}", type=GSheetsConnection)
            df = conn.read(spreadsheet=_url(SURVEY_IDS[group]), ttl=0)
        except Exception as e:
            return pd.DataFrame(), str(e)[:150]
    return df.dropna(how="all"), None


@st.cache_data(ttl=600, show_spinner="Đang tải dữ liệu khảo sát…")
def load_all_surveys_enriched(
    _df_wf: pd.DataFrame,
    _map_2ab: dict,
    _map_3ab: dict,
) -> tuple[pd.DataFrame, list]:
    parts, warn_msgs = [], []
    for g in ALL_GROUPS:
        raw, err = _load_raw_survey(g)
        if err:   warn_msgs.append(f"[{g}] {err}"); continue
        if len(raw) == 0: continue
        try:
            parsed = _parse_2ab(raw, g) if g in ("2A","2B") else _parse_3ab(raw, g)
            parts.append(parsed)
        except Exception as e:
            warn_msgs.append(f"[{g}] Parse error: {str(e)[:100]}")

    if not parts:
        empty = pd.DataFrame(columns=["timestamp","survey_group","sv_label",
                                       "wf_division","wf_department","wf_section_vn","wf_team"])
        empty["timestamp"] = pd.NaT
        return empty, warn_msgs

    df_all = pd.concat(parts, ignore_index=True)
    df_all["timestamp"] = pd.to_datetime(df_all["timestamp"], errors="coerce", dayfirst=False)

    # Build WF lookup từ tất cả cột string
    lookup_exact, lookup_fallback = build_wf_lookup(_df_wf)

    # Enrich
    df_enriched = enrich_survey(df_all, _map_2ab, _map_3ab, lookup_exact, lookup_fallback)
    return df_enriched, warn_msgs


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
now_str = datetime.now(ICT).strftime("%d/%m/%Y  %H:%M")
st.markdown(f"""
<div class="site-header">
  <div class="hdr-accent"></div>
  <div class="hdr-body">
    <div>
      <div class="hdr-label">Giao Hàng Nhanh · Employee Experience · 2026</div>
      <div class="hdr-title">EES Race <span class="acc">2026</span></div>
      <div class="hdr-desc">{T('page_sub')}</div>
    </div>
    <div class="hdr-meta">
      <div class="ml">{T('updated')}</div>
      <div class="mv">{now_str}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════
df_wf_raw, MAP_2AB, MAP_3AB = load_workforce_and_mapping()
df_sv_raw, warnings = load_all_surveys_enriched(df_wf_raw, MAP_2AB, MAP_3AB)
for w in warnings: st.warning(w)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sb-logo">GHN <span>EES</span></div>', unsafe_allow_html=True)

    lang = st.session_state["lang"]
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Tiếng Việt", key="lv",
                     type="primary" if lang=="VI" else "secondary"):
            st.session_state["lang"] = "VI"; st.rerun()
    with c2:
        if st.button("English", key="le",
                     type="primary" if lang=="EN" else "secondary"):
            st.session_state["lang"] = "EN"; st.rerun()

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st_autorefresh(interval=15 * 60 * 1000, key="data_autorefresh")
    c1, c2 = st.columns([0.85, 0.15], gap="small", vertical_alignment="center")
    with c1:
        st.markdown(f'<div style="font-size:0.75rem; color:{C["sub"]}; margin-top: 0.2rem; text-align: right;"><span style="color:{C["green"]}">●</span> {T("auto_refresh")}</div>', unsafe_allow_html=True)
    with c2:
        if st.button("↻", key="refresh_btn", help=T("refresh"), type="tertiary"):
            st.cache_data.clear()
            st.rerun()

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    grp_labels = T("group_labels")
    if "sg_val" not in st.session_state:
        st.session_state.sg_val = ALL_GROUPS

    def update_sg():
        st.session_state.sg_val = st.session_state.get("sel_groups_widget", st.session_state.get("sg_val", ALL_GROUPS))

    sel_groups = st.pills(
        T("survey_group"), ALL_GROUPS, selection_mode="multi", default=st.session_state.sg_val,
        format_func=lambda g: f"{g}  ·  {grp_labels[g]}",
        key="sel_groups_widget",
        on_change=update_sg
    )

    wf_base = df_wf_raw.copy()
    wf_base = wf_base[wf_base["status"] == 1]
    if sel_groups: wf_base = wf_base[wf_base["survey_group"].isin(sel_groups)]

    div_opts  = sorted(x for x in wf_base["division_name"].dropna().unique() if x)
    sel_div   = st.multiselect(T("division_lbl"), div_opts, key="sel_div_widget")

    is_only_3b = bool(sel_groups) and list(sel_groups) == ["3B"]
    
    sel_dept = []
    sel_sec  = []
    
    if not is_only_3b:
        wf_tmp = wf_base[wf_base["division_name"].isin(sel_div)] if sel_div else wf_base
        dept_opts = sorted(x for x in wf_tmp["department_name"].dropna().unique() if x)
        sel_dept  = st.multiselect(T("dept_lbl"), dept_opts, key="sel_dept_widget")

        if sel_dept: wf_tmp = wf_tmp[wf_tmp["department_name"].isin(sel_dept)]
        sec_opts = sorted(x for x in wf_tmp["section_name_vn"].dropna().unique() if x)
        sel_sec  = st.multiselect(T("section_lbl"), sec_opts, key="sel_sec_widget")

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    if df_sv_raw["timestamp"].notna().any():
        ts_min = df_sv_raw["timestamp"].min().date()
        ts_max = df_sv_raw["timestamp"].max().date()
        date_rng = st.date_input(T("date_range"), (ts_min, ts_max),
                                  min_value=ts_min, max_value=ts_max, key="date_rng_widget")
    else:
        date_rng = None
        
    st.markdown(f'<p class="sb-note">{T("sidebar_note")}</p>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# APPLY FILTERS
# ══════════════════════════════════════════════════════════════
df_wf = df_wf_raw.copy()
df_wf = df_wf[df_wf["status"] == 1]
if sel_groups: df_wf = df_wf[df_wf["survey_group"].isin(sel_groups)]
if sel_div:    df_wf = df_wf[df_wf["division_name"].isin(sel_div)]
if sel_dept:   df_wf = df_wf[df_wf["department_name"].isin(sel_dept)]
if sel_sec:    df_wf = df_wf[df_wf["section_name_vn"].isin(sel_sec)]

df_sv = df_sv_raw.copy()
if sel_groups: df_sv = df_sv[df_sv["survey_group"].isin(sel_groups)]
if sel_div:    df_sv = df_sv[df_sv["wf_division"].isin(sel_div)]
if sel_dept:   df_sv = df_sv[df_sv["wf_department"].isin(sel_dept)]
if sel_sec:    df_sv = df_sv[df_sv["wf_section_vn"].isin(sel_sec)]
if date_rng and isinstance(date_rng,(tuple,list)) and len(date_rng)==2:
    d0, d1 = date_rng
    d0_ts = pd.Timestamp(d0)
    d1_ts = pd.Timestamp(d1) + pd.Timedelta(days=1, microseconds=-1)
    df_sv = df_sv[(df_sv["timestamp"] >= d0_ts) & (df_sv["timestamp"] <= d1_ts)
                  | df_sv["timestamp"].isna()]
# ══════════════════════════════════════════════════════════════
# KPI
# ══════════════════════════════════════════════════════════════
today = datetime.now(ICT).date(); yesterday = today - timedelta(days=1)
total_hc = len(df_wf); total_rs = len(df_sv)
pct_done = (total_rs/total_hc*100) if total_hc>0 else 0
pending  = max(total_hc-total_rs, 0)
n_today = n_yest = 0
if df_sv["timestamp"].notna().any():
    _d = df_sv["timestamp"].dt.date
    n_today = int((_d==today).sum()); n_yest = int((_d==yesterday).sum())

grp_lbl = ", ".join([f"{g} · {T('group_labels')[g]}" for g in (sel_groups or ALL_GROUPS)])
st.markdown(f"""
<div style="background:{C['bg']};border:1px solid {C['border']};border-left:4px solid {C['orange']};
    padding:10px 20px;margin-bottom:20px;font-size:.82rem;color:{C['sub']};">
  <strong style="color:{C['navy']};font-size:.82rem;letter-spacing:.06em;text-transform:uppercase;">
    {T('viewing')}:</strong>&nbsp;{grp_lbl}
</div>
<div class="kpi-grid">
  <div class="kpi-cell kc-navy">
    <div class="kpi-lbl">{T('kpi_hc')}</div>
    <div class="kpi-val">{total_hc:,}</div>
    <div class="kpi-sub">{T('kpi_hc_sub')}</div>
  </div>
  <div class="kpi-cell kc-blue">
    <div class="kpi-lbl">{T('kpi_done')}</div>
    <div class="kpi-val">{total_rs:,}</div>
    <div class="kpi-sub">{pct_done:.1f}% {T('kpi_done_sub')}</div>
  </div>
  <div class="kpi-cell kc-orange">
    <div class="kpi-lbl">{T('kpi_pending')}</div>
    <div class="kpi-val">{pending:,}</div>
    <div class="kpi-sub">{T('kpi_pending_sub')}</div>
  </div>
  <div class="kpi-cell kc-green">
    <div class="kpi-lbl">{T('kpi_today')}</div>
    <div class="kpi-val">{n_today:,}</div>
    <div class="kpi-sub">{delta_html(n_today-n_yest)} {T('kpi_today_sub')} ({n_yest:,})</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PROGRESS TABLE BUILDER
# ══════════════════════════════════════════════════════════════
def build_progress(wf_col: str, sv_col: str, label: str) -> pd.DataFrame:
    """
    HC   = workforce grouped by wf_col
    Resp = survey enriched grouped by sv_col (wf_* columns)
    """
    df_wf[wf_col] = df_wf[wf_col].fillna("Chưa xác định").astype(str).str.strip().replace({"nan":"Chưa xác định", "None":"Chưa xác định", "":"Chưa xác định"})
    if sv_col in df_sv.columns:
        df_sv[sv_col] = df_sv[sv_col].fillna("Chưa xác định").astype(str).str.strip().replace({"nan":"Chưa xác định", "None":"Chưa xác định", "":"Chưa xác định"})

    hc = (df_wf[df_wf[wf_col].notna()]
          .groupby(wf_col).size().rename("hc").reset_index()
          .rename(columns={wf_col: label}))

    if sv_col in df_sv.columns and len(df_sv) > 0:
        rs = (df_sv[df_sv[sv_col].notna()]
              .groupby(sv_col).size().rename("responses").reset_index()
              .rename(columns={sv_col: label}))
    else:
        rs = pd.DataFrame(columns=[label, "responses"])

    out = hc.merge(rs, on=label, how="outer")
    out["hc"]        = out["hc"].fillna(0).astype(int)
    out["responses"] = out["responses"].fillna(0).astype(int)
    out["pending"]   = (out["hc"] - out["responses"]).clip(lower=0)
    out["pct"]       = out.apply(lambda r: (r["responses"] / r["hc"] * 100) if r["hc"] > 0 else 100.0 if r["responses"] > 0 else 0.0, axis=1).round(1)
    
    # Filter out 'Chưa xác định' so it never shows in charts
    out = out[out[label] != "Chưa xác định"]
    
    return out.sort_values(["responses", "hc"], ascending=[False, False]).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# CHART & TABLE HELPERS
# ══════════════════════════════════════════════════════════════
def render_chart(df, label_col, h=360):
    if len(df)==0: return go.Figure()
    fig = go.Figure()
    # Sort descending so the largest is at the top (with autorange='reversed')
    df_sorted = df.copy()
    
    fig.add_trace(go.Bar(
        y=df_sorted[label_col], x=df_sorted["responses"],
        orientation="h", name=T("col_done"),
        marker_color=C["navy"],
        text=[f"{int(v):,}" if v>0 else "" for v in df_sorted["responses"]],
        textposition="inside",
        textfont=dict(size=10, color="white", family="SVN-Helvetica Now"),
        hovertemplate="<b>%{y}</b><br>Đã tham gia: %{x:,}<extra></extra>",
    ))
    
    fig.add_trace(go.Bar(
        y=df_sorted[label_col], x=df_sorted["pending"],
        orientation="h", name=T("col_pending"),
        marker_color="#f3f4f6",
        marker_line=dict(color="#d1d5db", width=1),
        text=[f"{int(v):,}" if v>0 else "" for v in df_sorted["pending"]],
        textposition="inside",
        textfont=dict(size=10, color=C["sub"], family="SVN-Helvetica Now"),
        hovertemplate="<b>%{y}</b><br>Chưa tham gia: %{x:,}<extra></extra>",
    ))
    
    for _, r in df_sorted.iterrows():
        fig.add_annotation(
            x=r["hc"], y=r[label_col],
            text=f" {r['pct']:.1f}%",
            xanchor="left", showarrow=False,
            font=dict(size=11, color=C["navy"], family="SVN-Helvetica Now", weight="bold")
        )
        
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white", height=h,
        margin=dict(l=260, r=60, t=20, b=24), barmode="stack", bargap=0.35,
        font=dict(family="SVN-Helvetica Now", size=11, color=C["text"]),
        xaxis=dict(showgrid=True, gridcolor=C["line"], zeroline=False,
                   title_font=dict(size=10, color=C["muted"]), tickfont=dict(size=10, color=C["muted"])),
        yaxis=dict(showgrid=False, tickfont=dict(size=10, color=C["text"]), autorange="reversed"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10))
    )
    return fig

def render_table(df, label_col):
    rows = ""
    for i, r in df.iterrows():
        rows += f"""
<tr>
  <td class="rnk">{i+1}</td>
  <td class="nm" title="{r[label_col]}">{r[label_col]}</td>
  <td class="r">{int(r['hc']):,}</td>
  <td class="r">{int(r['responses']):,}</td>
  <td class="r" style="color:{C['sub']}">{int(r['pending']):,}</td>
  <td class="r">{pct_badge(r['pct'])}</td>
  <td style="min-width:90px;padding-left:4px">{prog_bar(r['pct'])}</td>
</tr>"""
    t_hc=int(df["hc"].sum()); t_rs=int(df["responses"].sum())
    t_pnd=int(df["pending"].sum())
    t_pct=(t_rs/t_hc*100) if t_hc>0 else 0
    rows += f"""
<tr class="foot">
  <td></td><td>{T('col_total')}</td>
  <td class="r">{t_hc:,}</td><td class="r">{t_rs:,}</td>
  <td class="r">{t_pnd:,}</td>
  <td class="r">{pct_badge(t_pct)}</td><td></td>
</tr>"""
    return f"""<div style="overflow-x:auto"><table class="dtbl">
<thead><tr>
  <th class="r">#</th><th>{label_col}</th>
  <th class="r">{T('col_hc')}</th><th class="r">{T('col_done')}</th>
  <th class="r">{T('col_pending')}</th><th class="r">{T('col_rate')}</th><th></th>
</tr></thead><tbody>{rows}</tbody></table></div>"""

def section_wrap(title, meta, fn):
    st.markdown(f"""
    <div class="scard">
      <div class="scard-head">
        <span class="sh-t">{title}</span><span class="sh-r"></span>
        <span class="sh-meta">{meta}</span>
      </div><div class="scard-body">
    """, unsafe_allow_html=True)
    fn()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
if is_only_3b:
    tab1, tab4 = st.tabs([
        T("tab_div"), T("tab_trend"),
    ])
    tab2 = tab3 = tab_dist = None
else:
    tab1, tab2, tab3, tab_dist, tab4 = st.tabs([
        T("tab_div"), T("tab_dept"), T("tab_sec"), T("tab_dist"), T("tab_trend"),
    ])

if lang == "VI":
    c_div_wf, c_div_sv = "division_name_vn", "wf_division_vn"
    c_dep_wf, c_dep_sv = "department_name_vn", "wf_department_vn"
    c_sec_wf, c_sec_sv = "section_name_vn", "wf_section_vn"
else:
    c_div_wf, c_div_sv = "division_name", "wf_division"
    c_dep_wf, c_dep_sv = "department_name", "wf_department"
    c_sec_wf, c_sec_sv = "section_name", "wf_section"

with tab1:
    div_df = build_progress(c_div_wf, c_div_sv, "Division")
    def _t1():
        if len(div_df)==0:
            st.markdown(f'<div class="no-data">{T("no_data")}</div>',unsafe_allow_html=True); return
        c1,c2=st.columns([40,60])
        with c1: st.plotly_chart(render_chart(div_df,"Division",h=max(340,len(div_df)*52+70)),use_container_width=True)
        with c2: st.markdown(render_table(div_df,"Division"),unsafe_allow_html=True)
    section_wrap(T("sec_div"),f"{len(div_df)} {T('divisions')} · HC {total_hc:,}",_t1)

if tab2:
    with tab2:
        dept_df = build_progress(c_dep_wf, c_dep_sv, "Department")
        def _t2():
            if len(dept_df)==0:
                st.markdown(f'<div class="no-data">{T("no_data")}</div>',unsafe_allow_html=True); return
            c1,c2=st.columns([40,60])
            with c1: st.plotly_chart(render_chart(dept_df,"Department",h=max(340,len(dept_df)*48+70)),use_container_width=True)
            with c2: st.markdown(render_table(dept_df,"Department"),unsafe_allow_html=True)
        section_wrap(T("sec_dept"),f"{len(dept_df)} {T('departments')}",_t2)

if tab3:
    with tab3:
        sec_df = build_progress(c_sec_wf, c_sec_sv, "Section")
        def _t3():
            if len(sec_df)==0:
                st.markdown(f'<div class="no-data">{T("no_data")}</div>',unsafe_allow_html=True); return
            c1,c2=st.columns([40,60])
            with c1: st.plotly_chart(render_chart(sec_df,"Section",h=max(340,len(sec_df)*46+70)),use_container_width=True)
            with c2: st.markdown(render_table(sec_df,"Section"),unsafe_allow_html=True)
        section_wrap(T("sec_sec"),f"{len(sec_df)} {T('sections')} · HC {total_hc:,}",_t3)

if tab_dist:
    with tab_dist:
        dept_dist_df = build_progress(c_dep_wf, c_dep_sv, "Department")
        def _t_dist():
            if len(dept_dist_df) == 0:
                st.markdown(f'<div class="no-data">{T("no_data")}</div>',unsafe_allow_html=True); return
            
            bins = [0, 25, 50, 75, 100.1]
            labels = ["0-25%", "26-50%", "51-75%", "76-100%"]
            dept_dist_df["bucket"] = pd.cut(dept_dist_df["pct"], bins=bins, labels=labels, right=False)
            bucket_counts = dept_dist_df["bucket"].value_counts().reindex(labels, fill_value=0)
            
            col_hist, col_stats = st.columns([65, 35])
            with col_hist:
                fig_hist = go.Figure()
                hist_colors = [C["red"], C["orange"], C["blue"], C["green"]]
                fig_hist.add_trace(go.Bar(
                    x=labels, y=bucket_counts.values,
                    marker_color=hist_colors,
                    text=[f"{int(v)}" for v in bucket_counts.values],
                    textposition="outside",
                    textfont=dict(size=11, color=C["text"], family="SVN-Helvetica Now"),
                    hovertemplate=f"<b>%{{x}}</b><br>{T('dist_hover')}: %{{y}}<extra></extra>",
                ))
                fig_hist.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white", height=320,
                    margin=dict(l=40, r=20, t=20, b=40), bargap=0.2,
                    font=dict(family="SVN-Helvetica Now", size=11, color=C["text"]),
                    xaxis=dict(title_text=T("dist_rate")),
                    yaxis=dict(title_text=T("dist_dept_cnt"), dtick=5)
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
            with col_stats:
                mean_p = dept_dist_df["pct"].mean()
                median_p = dept_dist_df["pct"].median()
                st.markdown(f"""
                <div style="padding:20px; background:{C['bg']}; border:1px solid {C['border']}; border-radius:4px; line-height:2.2; font-size:.85rem;">
                    <strong style="font-size:.75rem; text-transform:uppercase; color:{C['sub']};">{T('dist_stats')}</strong><br/>
                    {T('dist_total')}: <strong style="color:{C['text']}">{len(dept_dist_df)}</strong><br/>
                    {T('dist_mean')}: <strong style="color:{C['navy']}">{mean_p:.1f}%</strong><br/>
                    {T('dist_median')}: <strong style="color:{C['navy']}">{median_p:.1f}%</strong><br/>
                    {T('dist_exc')} (≥75%): <strong style="color:{C['green']}">{len(dept_dist_df[dept_dist_df['pct'] >= 75])}</strong> {T('dist_unit')}<br/>
                    {T('dist_poor')} (<50%): <strong style="color:{C['red']}">{len(dept_dist_df[dept_dist_df['pct'] < 50])}</strong> {T('dist_unit')}
                </div>
                """, unsafe_allow_html=True)
        section_wrap(T("sec_dist"), "", _t_dist)

with tab4:
    def _t4():
        if not df_sv["timestamp"].notna().any():
            st.markdown(f'<div class="no-data">{T("no_ts")}</div>',unsafe_allow_html=True); return
        tdf=df_sv.dropna(subset=["timestamp"]).copy()
        tdf["_d"]=tdf["timestamp"].dt.date
        daily=(tdf.groupby("_d").size().rename("new").reset_index()
               .sort_values("_d").reset_index(drop=True))
        daily["cum"]=daily["new"].cumsum()
        daily["pct_cum"]=(daily["cum"]/total_hc*100) if total_hc>0 else 0
        daily["lbl"]=daily["_d"].apply(lambda d:d.strftime("%d/%m"))
        
        fig_t=make_subplots(specs=[[{"secondary_y":True}]])
        fig_t.add_trace(go.Bar(
            x=daily["lbl"],y=daily["new"],
            marker_color="#9ca3af",
            marker_line_width=0,name=T("chart_new"),
            opacity=0.6,
            hovertemplate=f"<b>%{{x}}</b><br>{T('chart_new')}: %{{y:,}}<extra></extra>",
        ),secondary_y=False)
        fig_t.add_trace(go.Scatter(
            x=daily["lbl"],y=daily["pct_cum"],
            mode="lines+markers+text",
            line=dict(color=C["navy"],width=2.5),
            marker=dict(size=5,color=C["navy"]),
            text=[f"{v:.1f}%" for v in daily["pct_cum"]],
            textposition="top center",
            textfont=dict(size=9,color=C["text"]),
            name=T("chart_cum"),
            hovertemplate=f"<b>%{{x}}</b><br>{T('chart_cum')}: %{{y:.1f}}%<extra></extra>",
        ),secondary_y=True)
        
        fig_t.update_layout(
            paper_bgcolor="white",plot_bgcolor="white",height=380,bargap=0.3,showlegend=True,
            margin=dict(l=40,r=50,t=16,b=50),
            font=dict(family="SVN-Helvetica Now",size=11,color=C["text"]),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,
                        bgcolor="rgba(0,0,0,0)",font=dict(size=10)),
            xaxis=dict(type="category",tickangle=-45,showgrid=False,
                       tickfont=dict(size=10,color=C["muted"])),
        )
        fig_t.update_yaxes(title_text=T("chart_new_y"),title_font=dict(size=10,color=C["sub"]),
                           showgrid=False,tickfont=dict(size=10,color=C["muted"]),secondary_y=False)
        fig_t.update_yaxes(title_text=T("chart_cum_y"),title_font=dict(size=10,color=C["sub"]),
                           range=[0,105],showgrid=True,gridcolor="#eee",tickfont=dict(size=10,color=C["muted"]),secondary_y=True)
        st.plotly_chart(fig_t,use_container_width=True)
    section_wrap(T("sec_trend"),"",_t4)


# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:2rem;padding:18px 0;border-top:1px solid {C['border']};
     display:flex;justify-content:space-between;align-items:center;
     font-size:.72rem;color:{C['muted']};font-family:'SVN-Helvetica Now',sans-serif;">
  <span>
    <strong style="color:{C['navy']};font-size:.85rem;font-weight:700;letter-spacing:.04em;">GHN EES 2026</strong>
    &nbsp;·&nbsp; {T('footer')}
  </span>
  <span>{T('render')}: {now_str}</span>
</div>
""", unsafe_allow_html=True)