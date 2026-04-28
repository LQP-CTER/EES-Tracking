"""
GHN EES 2026 — Survey Progress Dashboard
Kiến trúc mapping:
  Survey response value
    → sheet Mapping (survey_val → wf_col + wf_val)
    → JOIN với Workforce Data trên (wf_col == wf_val)
    → lấy toàn bộ thông tin nhân viên (division, department, section, team...)
    → dashboard group theo các cột đó
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import unicodedata, re

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
        "page_sub":        "Tiến độ tham gia khảo sát theo Division, Department và Section.",
        "updated":         "Cập nhật lần cuối",
        "refresh":         "Làm mới dữ liệu",
        "only_active":     "Chỉ nhân sự đang làm (status = 1)",
        "survey_group":    "Nhóm khảo sát",
        "division_lbl":    "Division",
        "dept_lbl":        "Department",
        "section_lbl":     "Section / Vùng",
        "date_range":      "Khoảng thời gian",
        "sidebar_note":    "HC từ workforce, ánh xạ qua sheet Mapping.<br>Filter: Division → Department → Section.",
        "viewing":         "Đang xem",
        "kpi_hc":          "Tổng Nhân Sự",    "kpi_hc_sub":      "HC của nhóm đã chọn",
        "kpi_done":        "Đã Tham Gia",      "kpi_done_sub":    "trên tổng HC",
        "kpi_pending":     "Chưa Tham Gia",    "kpi_pending_sub": "HC − Response",
        "kpi_today":       "Hôm Nay",          "kpi_today_sub":   "so với hôm qua",
        "tab_div":   "Theo Division",    "tab_dept":  "Theo Department",
        "tab_sec":   "Theo Section",     "tab_trend": "Xu hướng theo ngày",
        "sec_div":   "Tiến độ theo Division",
        "sec_dept":  "Tiến độ theo Department",
        "sec_sec":   "Tiến độ theo Section / Vùng",
        "sec_trend": "Response theo ngày — tích lũy & mới",
        "top_n_dept":"Top N phòng ban",  "top_n_sec": "Top N section",
        "col_hc":"HC", "col_done":"Đã nộp", "col_pending":"Chưa nộp",
        "col_rate":"Tỷ lệ", "col_total":"Tổng cộng",
        "chart_pct":"% Hoàn thành", "chart_avg":"TB",
        "chart_new":"Mới trong ngày", "chart_cum":"% Tích lũy",
        "chart_new_y":"Response mới / ngày", "chart_cum_y":"% Tích lũy",
        "no_data":"Không có dữ liệu", "no_ts":"Chưa có timestamp hợp lệ",
        "divisions":"divisions", "departments":"phòng ban", "sections":"sections",
        "group_labels": {
            "2A":"Nhóm Nhân viên Vận hành Kho",
            "2B":"Nhóm Quản lý Tuyến đầu",
            "3A":"Nhóm Nhân viên Văn phòng HO",
            "3B":"Manager / Director HO",
        },
        "footer":"Báo cáo Tiến độ Khảo sát · EX Team",
        "render":"Render",
    },
    "EN": {
        "page_sub":        "Survey participation progress by Division, Department and Section.",
        "updated":         "Last updated",
        "refresh":         "Refresh data",
        "only_active":     "Active employees only (status = 1)",
        "survey_group":    "Survey group",
        "division_lbl":    "Division",
        "dept_lbl":        "Department",
        "section_lbl":     "Section / Region",
        "date_range":      "Date range",
        "sidebar_note":    "HC from workforce, mapped via Mapping sheet.<br>Filter: Division → Department → Section.",
        "viewing":         "Viewing",
        "kpi_hc":          "Total Headcount",  "kpi_hc_sub":      "HC of selected groups",
        "kpi_done":        "Participated",      "kpi_done_sub":    "of total HC",
        "kpi_pending":     "Not Yet",           "kpi_pending_sub": "HC − Response",
        "kpi_today":       "Today",             "kpi_today_sub":   "vs yesterday",
        "tab_div":   "By Division",      "tab_dept":  "By Department",
        "tab_sec":   "By Section",       "tab_trend": "Daily Trend",
        "sec_div":   "Progress by Division",
        "sec_dept":  "Progress by Department",
        "sec_sec":   "Progress by Section / Region",
        "sec_trend": "Daily response — cumulative & new",
        "top_n_dept":"Top N departments", "top_n_sec":"Top N sections",
        "col_hc":"HC", "col_done":"Submitted", "col_pending":"Pending",
        "col_rate":"Rate", "col_total":"Total",
        "chart_pct":"% Completion", "chart_avg":"Avg",
        "chart_new":"New today", "chart_cum":"% Cumulative",
        "chart_new_y":"New responses / day", "chart_cum_y":"% Cumulative",
        "no_data":"No data available", "no_ts":"No valid timestamps found",
        "divisions":"divisions", "departments":"departments", "sections":"sections",
        "group_labels": {
            "2A":"Warehouse Operations Staff",
            "2B":"Frontline Managers",
            "3A":"HO Office Staff",
            "3B":"HO Manager / Director",
        },
        "footer":"Survey Progress Dashboard · EX Team",
        "render":"Render",
    },
}
ALL_GROUPS = ["2A", "2B", "3A", "3B"]

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
.block-container{{max-width:1320px;padding:0 2rem 3rem;}}
#MainMenu,footer,header{{visibility:hidden;}}
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
[data-testid="stSidebar"]{{background:{C['navy']};border-right:none;}}
[data-testid="stSidebar"] *{{color:rgba(255,255,255,0.85)!important;}}
[data-testid="stSidebar"] .stMultiSelect>label,
[data-testid="stSidebar"] .stCheckbox>label,
[data-testid="stSidebar"] .stDateInput>label{{
    color:rgba(255,255,255,0.5)!important;font-size:.68rem!important;
    font-weight:700!important;text-transform:uppercase!important;letter-spacing:.1em!important;}}
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="input"] input{{
    background:rgba(255,255,255,0.08)!important;
    border-color:rgba(255,255,255,0.12)!important;color:white!important;border-radius:4px!important;}}
[data-testid="stSidebar"] .stButton>button{{
    background:{C['orange']}!important;color:white!important;border:none!important;
    border-radius:4px!important;font-family:'SVN-Helvetica Now',sans-serif!important;
    font-size:.82rem!important;font-weight:700!important;letter-spacing:.08em!important;
    text-transform:uppercase!important;padding:.5rem .9rem!important;width:100%!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{background:{C['orange2']}!important;}}
.sb-logo{{font-family:'SVN-Helvetica Now',sans-serif;font-size:1.5rem;font-weight:700;
    color:white!important;letter-spacing:-.02em;text-transform:uppercase;
    padding:1.5rem 0 1rem;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:1rem;}}
.sb-logo span{{color:{C['orange']};}}
.sb-div{{border:none;border-top:1px solid rgba(255,255,255,0.08);margin:1rem 0;}}
.sb-note{{font-size:.65rem;color:rgba(255,255,255,.3);line-height:1.7;margin-top:.5rem;}}
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
    padding:8px 10px 10px;text-align:left;white-space:nowrap;background:transparent;}}
.dtbl th.r{{text-align:right;}}
.dtbl tbody tr{{border-bottom:1px solid {C['line']};transition:background .1s;}}
.dtbl tbody tr:hover{{background:{C['slate']};}}
.dtbl td{{padding:9px 10px;vertical-align:middle;color:{C['text']};}}
.dtbl td.r{{text-align:right;font-variant-numeric:tabular-nums;font-size:.82rem;}}
.dtbl td.nm{{font-weight:500;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.dtbl .foot td{{border-top:2px solid {C['navy']};padding-top:11px;font-weight:700;color:{C['navy']};background:transparent;}}
.dtbl .rnk{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.78rem;font-weight:700;
    color:{C['muted']};text-align:right;width:28px;}}
.prog-w{{height:5px;background:{C['line']};border-radius:1px;overflow:hidden;min-width:80px;}}
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
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════
WF_SHEET_ID = "1pyNwximXg0aZzahEroGdenxnUIRe1XWbnMy_YRULAn0"
SURVEY_IDS  = {
    "2A": "1AS22mEX2_kezYRGsWIDHGEXNQAKD4xG_4W8_jtBDA1o",
    "2B": "1hmATsOmJ9a1WmZsBMSlITC3UH7zAnLRYXqQ2an1ppNo",
    "3A": "1UFtIMOAqZj-uvidePYZiWLiYaq_Lg1rm0ttEJWYowb8",
    "3B": "1E7_G8znrD-ITdvs894e-QUg9AJl7SQS3D6FhyYkeUbc",
}

def _url(s): return f"https://docs.google.com/spreadsheets/d/{s}/edit"
def _norm(s):
    s = unicodedata.normalize("NFD", str(s).strip().lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))
def _clean(v):
    if v is None: return None
    s = str(v).strip()
    return None if s in ("","nan","None") else s
def _find_col(df, *kw):
    for col in df.columns:
        if any(k.lower() in col.lower() for k in kw): return col
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
@st.cache_data(ttl=600, show_spinner="Đang tải Workforce & Mapping…")
def load_workforce_and_mapping():
    """
    Load 2 sheet từ Google Sheet:
    1. "Workforce Data" → df_wf: toàn bộ nhân sự với tất cả cột
    2. "Mapping"        → 2 dict:
       - MAP_2AB: {survey_value → section_name_vn}
       - MAP_3AB: {survey_value → (wf_col, wf_val)}
    """
    conn = st.connection("workforce", type=GSheetsConnection)
    try:
        df_wf = conn.read(spreadsheet=_url(WF_SHEET_ID), worksheet="Workforce Data")
    except Exception:
        df_wf = conn.read(spreadsheet=_url(WF_SHEET_ID))

    try:
        df_map = conn.read(spreadsheet=_url(WF_SHEET_ID), worksheet="Mapping")
    except Exception:
        df_map = pd.DataFrame()

    # ── Chuẩn hóa cột workforce ──
    df_wf = df_wf.dropna(how="all").copy()
    df_wf.columns = [str(c).strip() for c in df_wf.columns]
    str_cols = ["division_name","division_name_vn","department_name","department_name_vn",
                "section_name","section_name_vn","team_name","team_name_vn",
                "bu_name","survey_group","jobtitle_name"]
    for col in str_cols:
        if col not in df_wf.columns: df_wf[col] = None
        df_wf[col] = df_wf[col].astype(str).str.strip().replace({"nan":None,"":None,"None":None})
    df_wf["status"] = pd.to_numeric(df_wf.get("status", pd.Series()), errors="coerce")

    # ── Parse Mapping sheet ──
    MAP_2AB: dict[str, str]           = {}  # sv_val → section_name_vn
    MAP_3AB: dict[str, tuple[str,str]]= {}  # sv_val → (wf_col, wf_val)

    if len(df_map) > 0:
        cols = list(df_map.columns)

        # 2A-2B: cột 0=Survey2A, 1=Survey2B, 2=WF_section_name_vn
        if len(cols) >= 3:
            sub2 = df_map.iloc[:, [0,1,2]].copy()
            sub2.columns = ["sv2a","sv2b","wf_sec_vn"]
            sub2 = sub2.dropna(subset=["wf_sec_vn"])
            sub2 = sub2[~sub2["sv2a"].astype(str).str.strip().isin(["Survey-2A",""])]
            for _, r in sub2.iterrows():
                wf = _clean(str(r["wf_sec_vn"]))
                if not wf: continue
                for sv_raw in [r["sv2a"], r["sv2b"]]:
                    sv = _clean(str(sv_raw))
                    if sv: MAP_2AB[sv] = wf

        # 3A-3B: cột 4=Survey3A3B, 5=WF_value, 6=WF_column
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
# JOIN SURVEY → MAPPING → WORKFORCE
# ══════════════════════════════════════════════════════════════
def enrich_survey_with_wf(
    df_sv_parsed: pd.DataFrame,
    df_wf: pd.DataFrame,
    MAP_2AB: dict,
    MAP_3AB: dict,
) -> pd.DataFrame:
    """
    Ánh xạ mỗi survey response sang đúng cột trong workforce rồi JOIN lấy
    thông tin division/department/section của nhân viên tương ứng.

    Kết quả: mỗi row survey được gắn thêm:
      wf_division, wf_department, wf_section_vn, wf_team

    Cách hoạt động:
      - 2A/2B: sv_label → MAP_2AB → section_name_vn →
               JOIN df_wf ON section_name_vn → lấy division/department/section của nhóm đó
      - 3A/3B: sv_label → MAP_3AB → (wf_col, wf_val) →
               JOIN df_wf WHERE df_wf[wf_col] == wf_val → lấy div/dept/section
    """
    if len(df_sv_parsed) == 0:
        df_sv_parsed["wf_division"]   = None
        df_sv_parsed["wf_department"] = None
        df_sv_parsed["wf_section_vn"] = None
        df_sv_parsed["wf_team"]       = None
        return df_sv_parsed

    results = []

    # Pre-build lookup: (wf_col, wf_val) → (division_name, department_name, section_name_vn, team_name)
    # Dùng first-match (representative row) cho mỗi key
    wf_lookup: dict[tuple, dict] = {}
    for _, row in df_wf.iterrows():
        for col in ["section_name_vn","department_name","department_name_vn",
                    "section_name","team_name","division_name","division_name_vn"]:
            v = _clean(str(row.get(col, "") or ""))
            if v:
                key = (col, v)
                if key not in wf_lookup:
                    wf_lookup[key] = {
                        "wf_division":   row.get("division_name"),
                        "wf_department": row.get("department_name"),
                        "wf_section_vn": row.get("section_name_vn"),
                        "wf_team":       row.get("team_name"),
                    }

    for _, row in df_sv_parsed.iterrows():
        sv_val   = _clean(str(row.get("sv_label", "") or ""))
        grp      = str(row.get("survey_group", ""))
        wf_info  = {"wf_division":None,"wf_department":None,"wf_section_vn":None,"wf_team":None}

        if sv_val:
            if grp in ("2A","2B"):
                # MAP_2AB: sv_val → section_name_vn
                sec_vn = MAP_2AB.get(sv_val)
                if not sec_vn:
                    # normalized fallback
                    sv_n = _norm(sv_val)
                    sec_vn = next((v for k,v in MAP_2AB.items() if _norm(k)==sv_n), None)
                if sec_vn:
                    info = wf_lookup.get(("section_name_vn", sec_vn))
                    if info: wf_info = info

            elif grp in ("3A","3B"):
                # MAP_3AB: sv_val → (wf_col, wf_val)
                mapping = MAP_3AB.get(sv_val)
                if not mapping:
                    sv_n = _norm(sv_val)
                    mapping = next((v for k,v in MAP_3AB.items() if _norm(k)==sv_n), None)
                if mapping:
                    wfc, wfv = mapping
                    info = wf_lookup.get((wfc, wfv))
                    if info: wf_info = info

        r = row.to_dict()
        r.update(wf_info)
        results.append(r)

    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════
# HC COMPUTATION — từ workforce trực tiếp (mẫu số chính xác)
# ══════════════════════════════════════════════════════════════
def compute_hc_by_col(df_wf_filtered: pd.DataFrame, group_col: str) -> pd.Series:
    """Đếm HC theo một cột workforce. Trả về Series indexed by cột đó."""
    return (df_wf_filtered[df_wf_filtered[group_col].notna()]
            .groupby(group_col).size().rename("hc"))


# ══════════════════════════════════════════════════════════════
# SURVEY PARSING (chỉ lấy timestamp + phòng ban)
# ══════════════════════════════════════════════════════════════
def _parse_survey_raw(df: pd.DataFrame, group: str) -> pd.DataFrame:
    """Parse raw Google Form response → chỉ lấy timestamp + sv_label."""
    rows = []
    col_ts   = _find_col(df,"timestamp","thời gian")
    col_pb   = _find_col(df,"phòng ban","phong ban")
    col_vung = _find_col(df,"thuộc vùng")
    col_ktc  = _find_col(df,"kct","ttct","ktc/")
    col_gxt  = _find_col(df,"bộ phận nào")
    col_wh   = _find_col(df,"warehouse","fulfillment","khl")
    col_dept = _find_col(df,"bạn thuộc","ban thuoc")

    for _, row in df.iterrows():
        ts = pd.to_datetime(row[col_ts], errors="coerce") if col_ts else pd.NaT

        if group in ("2A","2B"):
            pb  = _clean(row[col_pb]) if col_pb else None
            sv_label = None
            if pb:
                pl = pb.lower()
                if "warehouse" in pl or "fulfillment" in pl:
                    sv_label = _clean(row[col_wh]) if col_wh else pb
                elif "giao hàng nặng" in pl or "gxt" in pl:
                    sv_label = _clean(row[col_gxt]) if col_gxt else pb
                elif "kho trung chuyển" in pl or "trung tâm" in pl or "ktc" in pl:
                    sv_label = _clean(row[col_ktc]) if col_ktc else pb
                else:
                    sv_label = _clean(row[col_vung]) if col_vung else pb
        else:
            # 3A/3B: lấy giá trị từ câu "Bạn thuộc..."
            sv_label = _clean(row[col_dept]) if col_dept else None
            # fallback: câu "Phòng ban"
            if not sv_label and col_pb:
                sv_label = _clean(row[col_pb])

        rows.append({"timestamp": ts, "survey_group": group, "sv_label": sv_label})

    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def _load_raw_survey(group: str) -> tuple[pd.DataFrame, str | None]:
    try:
        conn = st.connection(f"survey_{group}", type=GSheetsConnection)
        df = conn.read(spreadsheet=_url(SURVEY_IDS[group]), worksheet="Form Responses 1")
    except Exception:
        try:
            conn = st.connection(f"survey_{group}", type=GSheetsConnection)
            df = conn.read(spreadsheet=_url(SURVEY_IDS[group]))
        except Exception as e:
            return pd.DataFrame(), str(e)[:150]
    return df.dropna(how="all"), None


@st.cache_data(ttl=600, show_spinner="Đang tải dữ liệu khảo sát…")
def load_all_surveys_enriched(
    _df_wf: pd.DataFrame,
    _map_2ab: dict,
    _map_3ab: dict,
) -> tuple[pd.DataFrame, list]:
    """
    Load tất cả survey groups, parse sv_label, enrich với workforce info.
    """
    parts, warnings = [], []
    for g in ALL_GROUPS:
        raw, err = _load_raw_survey(g)
        if err:   warnings.append(f"[{g}] {err}"); continue
        if len(raw) == 0: continue
        try:
            parsed = _parse_survey_raw(raw, g)
            parts.append(parsed)
        except Exception as e:
            warnings.append(f"[{g}] Parse error: {str(e)[:100]}")

    if not parts:
        empty = pd.DataFrame(columns=["timestamp","survey_group","sv_label",
                                       "wf_division","wf_department","wf_section_vn","wf_team"])
        empty["timestamp"] = pd.NaT
        return empty, warnings

    df_all = pd.concat(parts, ignore_index=True)
    df_all["timestamp"] = pd.to_datetime(df_all["timestamp"], errors="coerce")

    # Enrich: gắn division/department/section từ workforce
    df_enriched = enrich_survey_with_wf(df_all, _df_wf, _map_2ab, _map_3ab)
    return df_enriched, warnings


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
now_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
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

    # Language
    lang = st.session_state["lang"]
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Tiếng Việt", key="lv",
                     type="primary" if lang=="VI" else "secondary",
                     use_container_width=True):
            st.session_state["lang"] = "VI"; st.rerun()
    with c2:
        if st.button("English", key="le",
                     type="primary" if lang=="EN" else "secondary",
                     use_container_width=True):
            st.session_state["lang"] = "EN"; st.rerun()

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    if st.button(T("refresh")):
        st.cache_data.clear(); st.rerun()

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    only_act = st.checkbox(T("only_active"), value=True)

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    grp_labels = T("group_labels")
    sel_groups = st.multiselect(
        T("survey_group"), ALL_GROUPS, default=ALL_GROUPS,
        format_func=lambda g: f"{g}  ·  {grp_labels[g]}",
    )

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)

    # Cascade filter — dựa vào workforce đã filter theo survey_group
    wf_base = df_wf_raw.copy()
    if sel_groups: wf_base = wf_base[wf_base["survey_group"].isin(sel_groups)]
    if only_act:   wf_base = wf_base[wf_base["status"] == 1]

    div_opts  = sorted(x for x in wf_base["division_name"].dropna().unique() if x)
    sel_div   = st.multiselect(T("division_lbl"), div_opts)

    wf_tmp = wf_base[wf_base["division_name"].isin(sel_div)] if sel_div else wf_base
    dept_opts = sorted(x for x in wf_tmp["department_name"].dropna().unique() if x)
    sel_dept  = st.multiselect(T("dept_lbl"), dept_opts)

    if sel_dept: wf_tmp = wf_tmp[wf_tmp["department_name"].isin(sel_dept)]
    sec_opts = sorted(x for x in wf_tmp["section_name_vn"].dropna().unique() if x)
    sel_sec  = st.multiselect(T("section_lbl"), sec_opts)

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    if df_sv_raw["timestamp"].notna().any():
        ts_min = df_sv_raw["timestamp"].min().date()
        ts_max = df_sv_raw["timestamp"].max().date()
        date_rng = st.date_input(T("date_range"), (ts_min, ts_max),
                                  min_value=ts_min, max_value=ts_max)
    else:
        date_rng = None
    st.markdown(f'<p class="sb-note">{T("sidebar_note")}</p>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# APPLY FILTERS
# ══════════════════════════════════════════════════════════════
# Workforce (mẫu số HC)
df_wf = df_wf_raw.copy()
if sel_groups: df_wf = df_wf[df_wf["survey_group"].isin(sel_groups)]
if only_act:   df_wf = df_wf[df_wf["status"] == 1]
if sel_div:    df_wf = df_wf[df_wf["division_name"].isin(sel_div)]
if sel_dept:   df_wf = df_wf[df_wf["department_name"].isin(sel_dept)]
if sel_sec:    df_wf = df_wf[df_wf["section_name_vn"].isin(sel_sec)]

# Survey (tử số) — filter theo wf_* columns đã enrich
df_sv = df_sv_raw.copy()
if sel_groups: df_sv = df_sv[df_sv["survey_group"].isin(sel_groups)]
if sel_div:    df_sv = df_sv[df_sv["wf_division"].isin(sel_div)]
if sel_dept:   df_sv = df_sv[df_sv["wf_department"].isin(sel_dept)]
if sel_sec:    df_sv = df_sv[df_sv["wf_section_vn"].isin(sel_sec)]
if date_rng and isinstance(date_rng,(tuple,list)) and len(date_rng)==2:
    d0, d1 = date_rng
    df_sv = df_sv[(df_sv["timestamp"].dt.date>=d0) & (df_sv["timestamp"].dt.date<=d1)
                  | df_sv["timestamp"].isna()]


# ══════════════════════════════════════════════════════════════
# KPI
# ══════════════════════════════════════════════════════════════
today = datetime.now().date(); yesterday = today - timedelta(days=1)
total_hc  = len(df_wf)
total_rs  = len(df_sv)
pct_done  = (total_rs / total_hc * 100) if total_hc > 0 else 0
pending   = max(total_hc - total_rs, 0)
n_today = n_yest = 0
if df_sv["timestamp"].notna().any():
    _d = df_sv["timestamp"].dt.date
    n_today = int((_d == today).sum()); n_yest = int((_d == yesterday).sum())

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
    Resp = survey grouped by sv_col (đã enrich từ workforce)
    Merge → tính pct
    """
    hc = (df_wf[df_wf[wf_col].notna()]
          .groupby(wf_col).size().rename("hc").reset_index()
          .rename(columns={wf_col: label}))

    rs_col = sv_col if sv_col in df_sv.columns else None
    if rs_col and len(df_sv) > 0:
        rs = (df_sv[df_sv[rs_col].notna()]
              .groupby(rs_col).size().rename("responses").reset_index()
              .rename(columns={rs_col: label}))
    else:
        rs = pd.DataFrame(columns=[label, "responses"])

    out = hc.merge(rs, on=label, how="left")
    out["responses"] = out["responses"].fillna(0).astype(int)
    out["pending"]   = (out["hc"] - out["responses"]).clip(lower=0)
    out["pct"]       = (out["responses"] / out["hc"].replace(0,pd.NA) * 100).fillna(0).round(1)
    return out.sort_values("pct", ascending=False).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# CHART & TABLE HELPERS
# ══════════════════════════════════════════════════════════════
def render_chart(df, label_col, h=360):
    if len(df) == 0: return go.Figure()
    avg = df["pct"].mean()
    def bc(p): return C["green"] if p>=75 else C["blue"] if p>=40 else C["orange"] if p>0 else C["muted"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df[label_col], x=[100]*len(df), orientation="h",
        marker_color="rgba(220,224,232,0.45)", marker_line_width=0,
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Bar(
        y=df[label_col], x=df["pct"], orientation="h",
        marker_color=[bc(p) for p in df["pct"]], marker_line_width=0,
        text=[f"  {p:.1f}%" for p in df["pct"]],
        textposition="outside",
        textfont=dict(size=10, color=C["text"], family="SVN-Helvetica Now"),
        hovertemplate=(f"<b>%{{y}}</b><br>{T('chart_pct')}: %{{x:.1f}}%"
                       f"<br>{T('col_done')}: %{{customdata[0]:,}} / HC: %{{customdata[1]:,}}"
                       f"<extra></extra>"),
        customdata=list(zip(df["responses"], df["hc"])),
        showlegend=False,
    ))
    fig.add_vline(x=avg, line_dash="dot", line_color=C["orange"], line_width=1.5,
                  annotation_text=f"{T('chart_avg')}  {avg:.1f}%",
                  annotation_position="top",
                  annotation_font=dict(size=9, color=C["orange"], family="SVN-Helvetica Now"))
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white", height=h,
        margin=dict(l=260, r=120, t=24, b=24), barmode="overlay", bargap=0.32,
        font=dict(family="SVN-Helvetica Now", size=11, color=C["text"]),
        xaxis=dict(range=[0, min(max(df["pct"].max()+22, 110), 130)], dtick=25,
                   showgrid=True, gridcolor=C["line"], zeroline=False,
                   title=T("chart_pct"), title_font=dict(size=10, color=C["muted"]),
                   tickfont=dict(size=10, color=C["muted"])),
        yaxis=dict(showgrid=False, tickfont=dict(size=10, color=C["text"])),
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
    t_hc = int(df["hc"].sum()); t_rs = int(df["responses"].sum())
    t_pnd = int(df["pending"].sum())
    t_pct = (t_rs/t_hc*100) if t_hc>0 else 0
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
tab1, tab2, tab3, tab4 = st.tabs([
    T("tab_div"), T("tab_dept"), T("tab_sec"), T("tab_trend"),
])

# ─── TAB 1: DIVISION ──────────────────────────────────────────
with tab1:
    # HC: từ workforce → group division_name
    # Resp: từ survey enriched → group wf_division
    div_df = build_progress("division_name", "wf_division", "Division")
    def _t1():
        if len(div_df)==0:
            st.markdown(f'<div class="no-data">{T("no_data")}</div>', unsafe_allow_html=True); return
        c1,c2 = st.columns([55,45])
        with c1: st.plotly_chart(render_chart(div_df,"Division",h=max(340,len(div_df)*52+70)),use_container_width=True)
        with c2: st.markdown(render_table(div_df,"Division"),unsafe_allow_html=True)
    section_wrap(T("sec_div"),f"{len(div_df)} {T('divisions')} · HC {total_hc:,}",_t1)

# ─── TAB 2: DEPARTMENT ────────────────────────────────────────
with tab2:
    dept_df = build_progress("department_name", "wf_department", "Department")
    def _t2():
        if len(dept_df)==0:
            st.markdown(f'<div class="no-data">{T("no_data")}</div>', unsafe_allow_html=True); return
        n = st.slider(T("top_n_dept"),5,min(60,len(dept_df)),min(20,len(dept_df)),key="dn")
        show = dept_df.head(n)
        c1,c2 = st.columns([55,45])
        with c1: st.plotly_chart(render_chart(show,"Department",h=max(340,len(show)*48+70)),use_container_width=True)
        with c2: st.markdown(render_table(show,"Department"),unsafe_allow_html=True)
    section_wrap(T("sec_dept"),f"{len(dept_df)} {T('departments')}",_t2)

# ─── TAB 3: SECTION / VÙNG ────────────────────────────────────
with tab3:
    sec_df = build_progress("section_name_vn", "wf_section_vn", "Section")
    def _t3():
        if len(sec_df)==0:
            st.markdown(f'<div class="no-data">{T("no_data")}</div>', unsafe_allow_html=True); return
        n2 = st.slider(T("top_n_sec"),5,min(80,len(sec_df)),min(25,len(sec_df)),key="sn")
        show2 = sec_df.head(n2)
        c1,c2 = st.columns([55,45])
        with c1: st.plotly_chart(render_chart(show2,"Section",h=max(340,len(show2)*46+70)),use_container_width=True)
        with c2: st.markdown(render_table(show2,"Section"),unsafe_allow_html=True)
    section_wrap(T("sec_sec"),f"{len(sec_df)} {T('sections')}",_t3)

# ─── TAB 4: TREND ─────────────────────────────────────────────
with tab4:
    def _t4():
        if not df_sv["timestamp"].notna().any():
            st.markdown(f'<div class="no-data">{T("no_ts")}</div>',unsafe_allow_html=True); return
        tdf = df_sv.dropna(subset=["timestamp"]).copy()
        tdf["_d"] = tdf["timestamp"].dt.date
        daily = (tdf.groupby("_d").size().rename("new").reset_index()
                 .sort_values("_d").reset_index(drop=True))
        daily["cum"]     = daily["new"].cumsum()
        daily["pct_cum"] = (daily["cum"]/total_hc*100) if total_hc>0 else 0
        daily["lbl"]     = daily["_d"].apply(lambda d: d.strftime("%d/%m"))
        fig_t = make_subplots(specs=[[{"secondary_y":True}]])
        max_new = daily["new"].max() or 1
        fig_t.add_trace(go.Bar(
            x=daily["lbl"],y=daily["new"],
            marker_color=[f"rgba(0,111,173,{0.3+0.6*(v/max_new)})" for v in daily["new"]],
            marker_line_width=0,name=T("chart_new"),
            hovertemplate=f"<b>%{{x}}</b>  ·  %{{y:,}}<extra></extra>",
        ),secondary_y=False)
        fig_t.add_trace(go.Scatter(
            x=daily["lbl"],y=daily["pct_cum"],mode="lines+markers",
            line=dict(color=C["orange"],width=2.5,shape="spline"),
            marker=dict(size=6,color=C["orange"],line=dict(width=1.5,color="white")),
            name=T("chart_cum"),
            hovertemplate=f"<b>%{{x}}</b>  ·  %{{y:.1f}}%<extra></extra>",
        ),secondary_y=True)
        fig_t.update_layout(
            paper_bgcolor="white",plot_bgcolor="white",height=360,bargap=0.25,showlegend=True,
            margin=dict(l=40,r=70,t=16,b=52),
            font=dict(family="SVN-Helvetica Now",size=11,color=C["text"]),
            legend=dict(orientation="h",y=1.06,x=1,xanchor="right",
                        bgcolor="rgba(255,255,255,.9)",font=dict(size=11),
                        bordercolor=C["border"],borderwidth=1),
            xaxis=dict(type="category",tickangle=-45,showgrid=False,
                       tickfont=dict(size=10,color=C["muted"])),
        )
        fig_t.update_yaxes(title_text=T("chart_new_y"),title_font=dict(size=10,color=C["sub"]),
                           showgrid=True,gridcolor=C["line"],tickfont=dict(size=10,color=C["muted"]),secondary_y=False)
        fig_t.update_yaxes(title_text=T("chart_cum_y"),title_font=dict(size=10,color=C["sub"]),
                           range=[0,108],showgrid=False,tickfont=dict(size=10,color=C["muted"]),secondary_y=True)
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