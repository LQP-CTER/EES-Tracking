"""
GHN EES 2026 — Survey Progress Dashboard
Logic: Workforce có cột survey_group → filter HC đúng nhóm → tính tỷ lệ response
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

GROUP_LABELS = {
    "2A": "Nhóm Nhân viên Vận hành Kho",
    "2B": "Nhóm Quản lý Tuyến đầu",
    "3A": "Nhóm Nhân viên Văn phòng HO",
    "3B": "Manager / Director HO",
}
ALL_GROUPS = list(GROUP_LABELS.keys())

st.markdown(f"""
<style>
/* ── Custom Font ── */
@font-face {{
  font-family: 'SVN-Helvetica Now';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('./app/static/fonts/SVN-HelveticaNowDisplay-Regular.ttf') format('truetype');
}}
@font-face {{
  font-family: 'SVN-Helvetica Now';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('./app/static/fonts/SVN-HelveticaNowDisplay-Medium.ttf') format('truetype');
}}
@font-face {{
  font-family: 'SVN-Helvetica Now';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('./app/static/fonts/SVN-HelveticaNowDisplay-Bold.ttf') format('truetype');
}}

/* ── Force Light Theme ── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"], .stApp {{
    background-color: {C['slate']} !important;
    color: {C['text']} !important;
    color-scheme: light !important;
}}
[data-testid="stHeader"] {{
    background-color: transparent !important;
}}

/* ── Base Typography ── */
html,body,[class*="css"]{{font-family:'SVN-Helvetica Now',system-ui,sans-serif!important;color:{C['text']}!important;-webkit-font-smoothing:antialiased;}}
.stApp{{background:{C['slate']};}}
.block-container{{max-width:1320px;padding:0 2rem 3rem;}}
#MainMenu,footer,header{{visibility:hidden;}}

/* ── Sidebar Toggle Fix ── */
[data-testid="stSidebar"][aria-expanded="false"] {{
    margin-left: 0 !important;
    min-width: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
}}
[data-testid="collapsedControl"] {{
    display: flex !important;
    visibility: visible !important;
    position: fixed !important;
    top: 0.5rem !important;
    left: 0.5rem !important;
    z-index: 999999 !important;
    color: {C['navy']} !important;
    background: {C['bg']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 6px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    padding: 4px !important;
}}
[data-testid="collapsedControl"] button {{
    color: {C['navy']} !important;
}}
[data-testid="collapsedControl"] svg {{
    fill: {C['navy']} !important;
    stroke: {C['navy']} !important;
}}

/* Sidebar */
[data-testid="stSidebar"]{{background:{C['navy']};border-right:none;}}
[data-testid="stSidebar"] *{{color:rgba(255,255,255,0.85)!important;}}
[data-testid="stSidebar"] .stMultiSelect>label,
[data-testid="stSidebar"] .stCheckbox>label,
[data-testid="stSidebar"] .stDateInput>label{{
    color:rgba(255,255,255,0.5)!important;font-size:.68rem!important;
    font-weight:700!important;text-transform:uppercase!important;letter-spacing:.1em!important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="input"] input{{
    background:rgba(255,255,255,0.08)!important;
    border-color:rgba(255,255,255,0.12)!important;color:white!important;border-radius:4px!important;
}}
[data-testid="stSidebar"] .stButton>button{{
    background:{C['orange']}!important;color:white!important;border:none!important;
    border-radius:4px!important;font-family:'SVN-Helvetica Now',sans-serif!important;
    font-size:.85rem!important;font-weight:700!important;letter-spacing:.12em!important;
    text-transform:uppercase!important;padding:.55rem 1rem!important;width:100%!important;
}}
[data-testid="stSidebar"] .stButton>button:hover{{background:{C['orange2']}!important;}}
.sb-logo{{font-family:'SVN-Helvetica Now',sans-serif;font-size:1.5rem;font-weight:700;
    color:white!important;letter-spacing:-.02em;text-transform:uppercase;
    padding:1.5rem 0 1rem;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:1.5rem;}}
.sb-logo span{{color:{C['orange']};}}
.sb-div{{border:none;border-top:1px solid rgba(255,255,255,0.08);margin:1.2rem 0;}}
.sb-note{{font-size:.65rem;color:rgba(255,255,255,.3);line-height:1.7;margin-top:.5rem;}}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{{background:transparent!important;
    border-bottom:2px solid {C['line']}!important;gap:0!important;padding:0!important;}}
.stTabs [data-baseweb="tab"]{{
    font-family:'SVN-Helvetica Now',sans-serif!important;font-size:.85rem!important;
    font-weight:700!important;letter-spacing:.1em!important;text-transform:uppercase!important;
    color:{C['muted']}!important;padding:.9rem 1.6rem!important;
    border-bottom:3px solid transparent!important;margin-bottom:-2px!important;
    transition:all .2s!important;background:transparent!important;
}}
.stTabs [aria-selected="true"]{{color:{C['navy']}!important;border-bottom-color:{C['orange']}!important;}}
.stTabs [data-baseweb="tab-panel"]{{padding:0!important;background:transparent!important;}}
[data-testid="stSlider"]>label{{
    font-size:.72rem!important;font-weight:600!important;
    text-transform:uppercase!important;letter-spacing:.1em!important;color:{C['sub']}!important;
}}

/* Header */
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
.hdr-desc{{font-size:.88rem;color:rgba(255,255,255,0.5);font-weight:400;
    letter-spacing:.01em;max-width:540px;line-height:1.6;}}
.hdr-meta{{text-align:right;}}
.hdr-meta .ml{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.65rem;
    letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.35);margin-bottom:4px;}}
.hdr-meta .mv{{font-size:.85rem;font-weight:500;color:rgba(255,255,255,.75);}}

/* Group Selector Pills (filter bar) */
.filter-bar{{
    background:{C['bg']};border:1px solid {C['border']};
    padding:14px 20px;margin-bottom:20px;
    display:flex;align-items:center;gap:12px;flex-wrap:wrap;
}}
.filter-label{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.72rem;
    font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:{C['muted']};}}

/* KPI Grid */
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;
    background:{C['border']};border:1px solid {C['border']};margin-bottom:2rem;}}
.kpi-cell{{background:{C['bg']};padding:22px 26px;position:relative;}}
.kpi-cell::before{{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:{C['border']};}}
.kpi-cell.kc-navy::before  {{background:{C['navy']};}}
.kpi-cell.kc-blue::before  {{background:{C['blue']};}}
.kpi-cell.kc-orange::before{{background:{C['orange']};}}
.kpi-cell.kc-green::before {{background:{C['green']};}}
.kpi-lbl{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.7rem;font-weight:700;
    letter-spacing:.14em;text-transform:uppercase;color:{C['muted']};margin-bottom:12px;}}
.kpi-val{{font-family:'SVN-Helvetica Now',sans-serif;font-size:3rem;font-weight:700;
    line-height:1;letter-spacing:-.03em;color:{C['navy']};margin-bottom:6px;}}
.kpi-cell.kc-blue .kpi-val  {{color:{C['blue']};}}
.kpi-cell.kc-orange .kpi-val{{color:{C['orange']};}}
.kpi-cell.kc-green .kpi-val {{color:{C['green']};}}
.kpi-sub{{font-size:.8rem;color:{C['sub']};font-weight:400;line-height:1.4;}}
.dp{{color:{C['green']};font-weight:700;}} .dn{{color:{C['red']};font-weight:700;}} .dz{{color:{C['muted']};}}

/* Section Card */
.scard{{background:{C['bg']};border:1px solid {C['border']};margin-bottom:1.5rem;}}
.scard-head{{padding:16px 26px;border-bottom:1px solid {C['line']};
    display:flex;align-items:center;gap:.8rem;}}
.scard-head .sh-t{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.78rem;
    font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:{C['navy']};
    white-space:nowrap;}}
.scard-head .sh-r{{flex:1;height:1px;background:{C['line']};}}
.scard-head .sh-meta{{font-size:.75rem;color:{C['muted']};white-space:nowrap;}}
.scard-body{{padding:22px 26px;}}

/* Data Table */
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
.dtbl td.nm{{font-weight:500;max-width:260px;overflow:hidden;
    text-overflow:ellipsis;white-space:nowrap;}}
.dtbl .foot td{{border-top:2px solid {C['navy']};padding-top:11px;
    font-weight:700;color:{C['navy']};background:transparent;}}
.dtbl .rnk{{font-family:'SVN-Helvetica Now',sans-serif;font-size:.78rem;
    font-weight:700;color:{C['muted']};text-align:right;width:28px;}}
.prog-w{{height:5px;background:{C['line']};border-radius:1px;overflow:hidden;min-width:80px;}}
.prog-f{{height:5px;border-radius:1px;transition:width .3s ease;}}
.pbg{{display:inline-block;font-family:'SVN-Helvetica Now',sans-serif;font-size:.82rem;
    font-weight:700;letter-spacing:.03em;padding:2px 8px;border-radius:2px;}}
.bg-g{{background:{C['green2']};color:{C['green']};}}
.bg-b{{background:#E8F4FD;color:{C['blue']};}}
.bg-r{{background:{C['red2']};color:{C['red']};}}
.bg-z{{background:{C['slate']};color:{C['muted']};}}

/* No-data state */
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

def _url(sid): return f"https://docs.google.com/spreadsheets/d/{sid}/edit"
def _norm(s):
    s = unicodedata.normalize("NFD", str(s).strip().lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))
def _clean(v):
    if v is None: return None
    s = str(v).strip()
    return None if s in ("", "nan", "None") else s
def _find_col(df, *kw):
    for col in df.columns:
        if any(k.lower() in col.lower() for k in kw): return col
    return None

def pct_badge(p):
    if p >= 75: return f'<span class="pbg bg-g">{p:.1f}%</span>'
    if p >= 40: return f'<span class="pbg bg-b">{p:.1f}%</span>'
    if p  > 0:  return f'<span class="pbg bg-r">{p:.1f}%</span>'
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
# LOAD WORKFORCE  (có cột survey_group từ GAS)
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=600, show_spinner="Đang tải Workforce…")
def load_workforce():
    try:
        conn = st.connection("workforce", type=GSheetsConnection)
        df = conn.read(spreadsheet=_url(WF_SHEET_ID), worksheet="Workforce Data")
    except Exception:
        conn = st.connection("workforce", type=GSheetsConnection)
        df = conn.read(spreadsheet=_url(WF_SHEET_ID))

    df = df.dropna(how="all").copy()
    df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]

    rename = {}
    for c in df.columns:
        n = _norm(c)
        if n in ("employeeid","id") and "employee_id" not in rename.values(): rename[c]="employee_id"
        elif n=="status":          rename[c]="status"
        elif n=="jobtitlename":    rename[c]="jobtitle_en"
        elif n=="divisionname":    rename[c]="division_name"
        elif n=="departmentname":  rename[c]="department_name"
        elif n=="sectionname":     rename[c]="section_name"
        elif n=="teamname":        rename[c]="team_name"
        elif n=="buname":          rename[c]="bu_name"
        elif n=="surveygroup":     rename[c]="survey_group"
    df = df.rename(columns=rename)

    for col in ["employee_id","status","jobtitle_en","division_name",
                "department_name","section_name","team_name","bu_name","survey_group"]:
        if col not in df.columns: df[col]=None

    for col in ["division_name","department_name","section_name",
                "team_name","bu_name","survey_group","jobtitle_en"]:
        df[col] = df[col].astype(str).str.strip().replace({"nan":None,"":None,"None":None})

    df["status"] = pd.to_numeric(df["status"], errors="coerce")
    return df


# ══════════════════════════════════════════════════════════════
# SURVEY PARSING
# ══════════════════════════════════════════════════════════════
_VUNG = {
    "hno":"HNO Region","dsh":"DSH Region","xbg":"XBG Region","dbb":"DBB Region",
    "tbb":"TBB Region","tnt":"TNT Region","btb":"BTB Region","ttb":"TTB Region",
    "tng":"TNG Region","ntb":"NTB Region","dnb":"DNB Region","tnb":"TNB Region",
    "hcm":"HCM Region","dcl":"ĐCL Region","ecl":"ĐCL Region",
}
def map_vung(v):
    if not v: return None
    n = _norm(v)
    for code, r in _VUNG.items():
        if code in n: return r
    return None

def map_ktc(v):
    if not v: return None
    n = _norm(v)
    if "xuyena" in n: return "Xuyen A Sorting Centers"
    if "m12" in n: return "M12 Sorting Centers"
    if "daitu" in n or "duongxa" in n: return "Dai Tu Sorting Centers"
    if "hungyen" in n: return "Hung Yen Sorting Centers"
    return None

def map_gxt(v):
    if not v: return None
    n = _norm(v)
    if "hn" in n and "hcm" not in n and "mien" not in n: return "B2B Operations Department - HN"
    if "bac1" in n: return "B2B Operations Department - North 1"
    if "bac2" in n: return "B2B Operations Department - North 2"
    if "bac3" in n: return "B2B Operations Department - North 3"
    if "trung" in n: return "B2B Operations Department - Central"
    if "dong" in n: return "B2B Operations Department - Eastern"
    if "tay" in n and "hcm" not in n: return "B2B Operations Department - Western"
    if "hcm" in n: return "B2B Operations Department - HCM"
    return None

def map_ho_div(v):
    if not v: return None
    n = _norm(v)
    if "freight" in n: return "Freight Project"
    if "technology" in n or "congngh" in n: return "Technology Division"
    if "customer" in n or "khhang" in n: return "Customer Division"
    if "humanresource" in n or "nhanluc" in n: return "Human Resource Division"
    if "finance" in n or "taichinh" in n: return "Finance Division"
    if "market" in n or "thitrng" in n: return "Market Division"
    if "coreai" in n or ("ai" in n and "data" in n): return "Core AI & Data Platform Department"
    if "warehouse" in n or "fulfillment" in n: return "Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)"
    if "audit" in n or "legal" in n or "ceo" in n: return "General Management Department"
    if "product" in n: return "Product Department"
    if "crossborder" in n: return "Cross Border Transport Department"
    return None

def parse_2ab(df, group):
    rows = []
    col_ts   = _find_col(df, "timestamp","thời gian")
    col_pb   = _find_col(df, "phòng ban","phong ban")
    col_vung = _find_col(df, "thuộc vùng")
    col_ktc  = _find_col(df, "kct","ttct","ktc/")
    col_gxt  = _find_col(df, "bộ phận nào")
    for _, row in df.iterrows():
        ts  = pd.to_datetime(row[col_ts], errors="coerce") if col_ts else pd.NaT
        pb  = _clean(row[col_pb]) if col_pb else None
        div=dept=sec=None
        if pb:
            pl=pb.lower()
            if "warehouse" in pl or "fulfillment" in pl:
                div="Phòng Dịch Vụ Kho Vận (Warehouse/ Fulfillment)"; dept="Phòng Dịch Vụ Kho Vận"
            elif "giao hàng nặng" in pl or "gxt" in pl:
                div="Freight Project"; dept="B2B Operations Department"
                sec=map_gxt(_clean(row[col_gxt]) if col_gxt else None)
            elif "kho trung chuyển" in pl or "trung tâm" in pl or "ktc" in pl:
                div="Market Division"; dept="Sorting Centers"
                sec=map_ktc(_clean(row[col_ktc]) if col_ktc else None)
            else:
                div="Market Division"; dept="Region"
                sec=map_vung(_clean(row[col_vung]) if col_vung else None)
        rows.append({"timestamp":ts,"survey_group":group,"division_wf":div,"department_wf":dept,"section_wf":sec})
    return pd.DataFrame(rows)

def parse_3ab(df, group):
    rows = []
    col_ts  = _find_col(df,"timestamp","thời gian")
    col_div = _find_col(df,"phòng ban","phong ban")
    col_dept= _find_col(df,"bạn thuộc","ban thuoc","bộ phận")
    for _, row in df.iterrows():
        ts      = pd.to_datetime(row[col_ts],errors="coerce") if col_ts else pd.NaT
        div_raw = _clean(row[col_div]) if col_div else None
        dept_r  = _clean(row[col_dept]) if col_dept else None
        rows.append({"timestamp":ts,"survey_group":group,
                     "division_wf":map_ho_div(div_raw),"department_wf":dept_r,"section_wf":None})
    return pd.DataFrame(rows)

@st.cache_data(ttl=600, show_spinner=False)
def load_survey(group):
    try:
        conn=st.connection(f"survey_{group}",type=GSheetsConnection)
        df=conn.read(spreadsheet=_url(SURVEY_IDS[group]),worksheet="Form Responses 1")
    except Exception:
        try:
            conn=st.connection(f"survey_{group}",type=GSheetsConnection)
            df=conn.read(spreadsheet=_url(SURVEY_IDS[group]))
        except Exception as e: return pd.DataFrame(),str(e)[:150]
    df=df.dropna(how="all")
    if len(df)==0: return pd.DataFrame(),None
    try:
        return (parse_2ab(df,group) if group in("2A","2B") else parse_3ab(df,group)),None
    except Exception as e: return pd.DataFrame(),str(e)

@st.cache_data(ttl=600, show_spinner="Đang tải dữ liệu khảo sát…")
def load_all_surveys():
    parts,warnings=[],[]
    for g in ALL_GROUPS:
        part,err=load_survey(g)
        if err: warnings.append(f"[{g}] {err}")
        elif len(part)>0: parts.append(part)
    if parts:
        df=pd.concat(parts,ignore_index=True)
        df["timestamp"]=pd.to_datetime(df["timestamp"],errors="coerce")
        return df,warnings
    empty=pd.DataFrame(columns=["timestamp","survey_group","division_wf","department_wf","section_wf"])
    empty["timestamp"]=pd.NaT
    return empty,warnings


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
now_str=datetime.now().strftime("%d/%m/%Y  %H:%M")
st.markdown(f"""
<div class="site-header">
  <div class="hdr-accent"></div>
  <div class="hdr-body">
    <div>
      <div class="hdr-label">Giao Hàng Nhanh · Employee Experience · 2026</div>
      <div class="hdr-title">EES Race <span class="acc">2026</span></div>
      <div class="hdr-desc">Tiến độ tham gia khảo sát theo Division, Department và Section — phân tích theo nhóm khảo sát.</div>
    </div>
    <div class="hdr-meta">
      <div class="ml">Cập nhật lần cuối</div>
      <div class="mv">{now_str}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════
df_wf_raw=load_workforce()
df_sv_raw,warnings=load_all_surveys()
for w in warnings: st.warning(w)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sb-logo">GHN <span>EES</span></div>',unsafe_allow_html=True)
    if st.button("Làm mới dữ liệu"):
        st.cache_data.clear(); st.rerun()

    st.markdown('<hr class="sb-div">',unsafe_allow_html=True)

    bu_opts=sorted(x for x in df_wf_raw["bu_name"].dropna().unique() if x)
    sel_bu=st.multiselect("Business Unit",bu_opts,default=bu_opts)
    only_act=st.checkbox("Chỉ nhân sự đang làm (status = 1)",value=True)

    st.markdown('<hr class="sb-div">',unsafe_allow_html=True)

    # Nhóm khảo sát — KEY FILTER
    sel_groups=st.multiselect(
        "Nhóm khảo sát",ALL_GROUPS,default=ALL_GROUPS,
        format_func=lambda g:f"{g}  ·  {GROUP_LABELS[g]}",
    )

    st.markdown('<hr class="sb-div">',unsafe_allow_html=True)

    # Cascade filter (chỉ show data thuộc nhóm đã chọn)
    wf_grp = df_wf_raw[df_wf_raw["survey_group"].isin(sel_groups)] if sel_groups else df_wf_raw
    if sel_bu: wf_grp=wf_grp[wf_grp["bu_name"].isin(sel_bu)]

    div_opts=sorted(x for x in wf_grp["division_name"].dropna().unique() if x)
    sel_div=st.multiselect("Division",div_opts)

    wf_tmp=wf_grp[wf_grp["division_name"].isin(sel_div)] if sel_div else wf_grp
    dept_opts=sorted(x for x in wf_tmp["department_name"].dropna().unique() if x)
    sel_dept=st.multiselect("Department",dept_opts)

    if sel_dept: wf_tmp=wf_tmp[wf_tmp["department_name"].isin(sel_dept)]
    sec_opts=sorted(x for x in wf_tmp["section_name"].dropna().unique() if x)
    sel_sec=st.multiselect("Section / Vùng",sec_opts)

    st.markdown('<hr class="sb-div">',unsafe_allow_html=True)

    if df_sv_raw["timestamp"].notna().any():
        ts_min=df_sv_raw["timestamp"].min().date()
        ts_max=df_sv_raw["timestamp"].max().date()
        date_rng=st.date_input("Khoảng thời gian",(ts_min,ts_max),
                               min_value=ts_min,max_value=ts_max)
    else: date_rng=None

    st.markdown(
        '<p class="sb-note">HC được tính từ nhân sự có survey_group tương ứng.<br>'
        'Filter cascade: Division → Department → Section.</p>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# APPLY FILTERS — HC từ workforce
# ══════════════════════════════════════════════════════════════
# Bước 1: Lọc workforce theo survey_group (quan trọng nhất)
df_wf = df_wf_raw.copy()
if sel_groups: df_wf=df_wf[df_wf["survey_group"].isin(sel_groups)]
if sel_bu:     df_wf=df_wf[df_wf["bu_name"].isin(sel_bu)]
if only_act:   df_wf=df_wf[df_wf["status"]==1]
if sel_div:    df_wf=df_wf[df_wf["division_name"].isin(sel_div)]
if sel_dept:   df_wf=df_wf[df_wf["department_name"].isin(sel_dept)]
if sel_sec:    df_wf=df_wf[df_wf["section_name"].isin(sel_sec)]

# Bước 2: Lọc survey responses theo nhóm
df_sv=df_sv_raw.copy()
if sel_groups: df_sv=df_sv[df_sv["survey_group"].isin(sel_groups)]
if sel_div:    df_sv=df_sv[df_sv["division_wf"].isin(sel_div)|df_sv["division_wf"].isna()]
if date_rng and isinstance(date_rng,(tuple,list)) and len(date_rng)==2:
    d0,d1=date_rng
    df_sv=df_sv[(df_sv["timestamp"].dt.date>=d0)&(df_sv["timestamp"].dt.date<=d1)
                |df_sv["timestamp"].isna()]


# ══════════════════════════════════════════════════════════════
# KPI
# ══════════════════════════════════════════════════════════════
today=datetime.now().date(); yesterday=today-timedelta(days=1)
total_hc=len(df_wf); total_rs=len(df_sv)
pct_done=(total_rs/total_hc*100) if total_hc>0 else 0
pending=max(total_hc-total_rs,0)
n_today=n_yest=0
if df_sv["timestamp"].notna().any():
    _d=df_sv["timestamp"].dt.date
    n_today=int((_d==today).sum()); n_yest=int((_d==yesterday).sum())

# Hiển thị nhóm đang chọn
grp_lbl=", ".join([f"{g} · {GROUP_LABELS[g]}" for g in (sel_groups or ALL_GROUPS)])
st.markdown(f"""
<div style="background:{C['bg']};border:1px solid {C['border']};
    border-left:4px solid {C['orange']};padding:10px 20px;margin-bottom:20px;
    font-size:.82rem;color:{C['sub']};">
  <strong style="color:{C['navy']};font-family:'SVN-Helvetica Now',sans-serif;
    font-size:.85rem;letter-spacing:.08em;text-transform:uppercase;">Đang xem:</strong>
  &nbsp;{grp_lbl}
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-cell kc-navy">
    <div class="kpi-lbl">Tổng Nhân Sự</div>
    <div class="kpi-val">{total_hc:,}</div>
    <div class="kpi-sub">HC của nhóm đã chọn</div>
  </div>
  <div class="kpi-cell kc-blue">
    <div class="kpi-lbl">Đã Tham Gia</div>
    <div class="kpi-val">{total_rs:,}</div>
    <div class="kpi-sub">{pct_done:.1f}% trên tổng HC</div>
  </div>
  <div class="kpi-cell kc-orange">
    <div class="kpi-lbl">Chưa Tham Gia</div>
    <div class="kpi-val">{pending:,}</div>
    <div class="kpi-sub">HC − Response</div>
  </div>
  <div class="kpi-cell kc-green">
    <div class="kpi-lbl">Hôm Nay</div>
    <div class="kpi-val">{n_today:,}</div>
    <div class="kpi-sub">{delta_html(n_today-n_yest)} so với hôm qua ({n_yest:,})</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# CORE HELPERS
# ══════════════════════════════════════════════════════════════
def build_df(wf, sv, wf_col, sv_col, label):
    hc=(wf.groupby(wf_col,dropna=False).size().rename("hc"))
    rs=(sv[sv[sv_col].notna()].groupby(sv_col).size().rename("responses")
        if len(sv)>0 else pd.Series(dtype=int,name="responses"))
    out=pd.concat([hc,rs],axis=1).fillna(0).astype(int).reset_index()
    out.columns=[label,"hc","responses"]
    out=out[out[label].notna()]
    out["pending"]=(out["hc"]-out["responses"]).clip(lower=0)
    out["pct"]=(out["responses"]/out["hc"].replace(0,pd.NA)*100).fillna(0).round(1)
    return out.sort_values("pct",ascending=False).reset_index(drop=True)

def render_chart(df, label_col, h=360):
    avg=df["pct"].mean()
    def bc(p): return C["green"] if p>=75 else C["blue"] if p>=40 else C["orange"] if p>0 else C["muted"]
    fig=go.Figure()
    fig.add_trace(go.Bar(
        y=df[label_col],x=[100]*len(df),orientation="h",
        marker_color="rgba(220,224,232,0.45)",marker_line_width=0,
        hoverinfo="skip",showlegend=False,
    ))
    fig.add_trace(go.Bar(
        y=df[label_col],x=df["pct"],orientation="h",
        marker_color=[bc(p) for p in df["pct"]],marker_line_width=0,
        text=[f"  {p:.1f}%" for p in df["pct"]],
        textposition="outside",
        textfont=dict(size=10,color=C["text"],family="SVN-Helvetica Now"),
        hovertemplate="<b>%{y}</b><br>%{x:.1f}%  ·  %{customdata[0]:,} / %{customdata[1]:,}<extra></extra>",
        customdata=list(zip(df["responses"],df["hc"])),
        showlegend=False,
    ))
    fig.add_vline(x=avg,line_dash="dot",line_color=C["orange"],line_width=1.5,
                  annotation_text=f"TB  {avg:.1f}%",annotation_position="top",
                  annotation_font=dict(size=9,color=C["orange"],family="Barlow Condensed"))
    fig.update_layout(
        paper_bgcolor="white",plot_bgcolor="white",height=h,
        margin=dict(l=260,r=120,t=24,b=24),barmode="overlay",bargap=0.32,
        font=dict(family="SVN-Helvetica Now",size=11,color=C["text"]),
        xaxis=dict(range=[0,min(max(df["pct"].max()+22,110),130)],dtick=25,
                   showgrid=True,gridcolor=C["line"],zeroline=False,
                   title="% Hoàn thành",title_font=dict(size=10,color=C["muted"]),
                   tickfont=dict(size=10,color=C["muted"])),
        yaxis=dict(showgrid=False,tickfont=dict(size=10,color=C["text"])),
    )
    return fig

def render_table(df, label_col):
    rows=""
    for i,r in df.iterrows():
        rows+=f"""
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
    rows+=f"""
<tr class="foot">
  <td></td><td>Total</td>
  <td class="r">{t_hc:,}</td><td class="r">{t_rs:,}</td>
  <td class="r">{t_pnd:,}</td>
  <td class="r">{pct_badge(t_pct)}</td><td></td>
</tr>"""
    return f"""<div style="overflow-x:auto">
<table class="dtbl">
<thead><tr>
  <th class="r">#</th><th>{label_col}</th>
  <th class="r">HC</th><th class="r">Đã nộp</th>
  <th class="r">Chưa nộp</th><th class="r">Tỷ lệ</th><th></th>
</tr></thead><tbody>{rows}</tbody></table></div>"""

def section_wrap(title, meta, content_fn):
    st.markdown(f"""
    <div class="scard">
      <div class="scard-head">
        <span class="sh-t">{title}</span>
        <span class="sh-r"></span>
        <span class="sh-meta">{meta}</span>
      </div>
      <div class="scard-body">
    """, unsafe_allow_html=True)
    content_fn()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tab1,tab2,tab3,tab4=st.tabs([
    "Theo Division","Theo Department","Theo Section / Vùng","Xu hướng theo ngày"
])

# ─── TAB 1: DIVISION ──────────────────────────────────────────
with tab1:
    div_df=build_df(df_wf,df_sv,"division_name","division_wf","Division")
    def _t1():
        if len(div_df)==0:
            st.markdown('<div class="no-data">Không có dữ liệu</div>',unsafe_allow_html=True); return
        c1,c2=st.columns([55,45])
        with c1: st.plotly_chart(render_chart(div_df,"Division",h=max(340,len(div_df)*52+70)),use_container_width=True)
        with c2: st.markdown(render_table(div_df,"Division"),unsafe_allow_html=True)
    section_wrap("Tiến độ theo Division",f"{len(div_df)} divisions · HC {total_hc:,}",_t1)

# ─── TAB 2: DEPARTMENT ────────────────────────────────────────
with tab2:
    dept_df=build_df(df_wf,df_sv,"department_name","department_wf","Department")
    def _t2():
        if len(dept_df)==0:
            st.markdown('<div class="no-data">Không có dữ liệu</div>',unsafe_allow_html=True); return
        n=st.slider("Top N phòng ban",5,min(60,len(dept_df)),min(20,len(dept_df)),key="dn")
        show=dept_df.head(n)
        c1,c2=st.columns([55,45])
        with c1: st.plotly_chart(render_chart(show,"Department",h=max(340,len(show)*48+70)),use_container_width=True)
        with c2: st.markdown(render_table(show,"Department"),unsafe_allow_html=True)
    section_wrap("Tiến độ theo Department",f"{len(dept_df)} departments",_t2)

# ─── TAB 3: SECTION / VÙNG ───────────────────────────────────
with tab3:
    sec_df=build_df(df_wf,df_sv,"section_name","section_wf","Section")
    def _t3():
        if len(sec_df)==0:
            st.markdown('<div class="no-data">Không có dữ liệu</div>',unsafe_allow_html=True); return
        n2=st.slider("Top N section",5,min(80,len(sec_df)),min(25,len(sec_df)),key="sn")
        show2=sec_df.head(n2)
        c1,c2=st.columns([55,45])
        with c1: st.plotly_chart(render_chart(show2,"Section",h=max(340,len(show2)*46+70)),use_container_width=True)
        with c2: st.markdown(render_table(show2,"Section"),unsafe_allow_html=True)
    section_wrap("Tiến độ theo Section / Vùng",f"{len(sec_df)} sections",_t3)

# ─── TAB 4: TREND ─────────────────────────────────────────────
with tab4:
    def _t4():
        if not df_sv["timestamp"].notna().any():
            st.markdown('<div class="no-data">Chưa có timestamp hợp lệ</div>',unsafe_allow_html=True); return
        tdf=df_sv.dropna(subset=["timestamp"]).copy()
        tdf["_d"]=tdf["timestamp"].dt.date
        daily=(tdf.groupby("_d").size().rename("new").reset_index()
               .sort_values("_d").reset_index(drop=True))
        daily["cum"]=daily["new"].cumsum()
        daily["pct_cum"]=(daily["cum"]/total_hc*100) if total_hc>0 else 0
        daily["lbl"]=daily["_d"].apply(lambda d:d.strftime("%d/%m"))

        fig_t=make_subplots(specs=[[{"secondary_y":True}]])
        max_new=daily["new"].max() or 1
        fig_t.add_trace(go.Bar(
            x=daily["lbl"],y=daily["new"],
            marker_color=[f"rgba(0,111,173,{0.3+0.6*(v/max_new)})" for v in daily["new"]],
            marker_line_width=0,name="Mới trong ngày",
            hovertemplate="<b>%{x}</b>  ·  %{y:,} mới<extra></extra>",
        ),secondary_y=False)
        fig_t.add_trace(go.Scatter(
            x=daily["lbl"],y=daily["pct_cum"],mode="lines+markers",
            line=dict(color=C["orange"],width=2.5,shape="spline"),
            marker=dict(size=6,color=C["orange"],line=dict(width=1.5,color="white")),
            name="% Tích lũy",
            hovertemplate="<b>%{x}</b>  ·  %{y:.1f}%<extra></extra>",
        ),secondary_y=True)
        fig_t.update_layout(
            paper_bgcolor="white",plot_bgcolor="white",
            height=360,bargap=0.25,showlegend=True,
            margin=dict(l=40,r=70,t=16,b=52),
            font=dict(family="SVN-Helvetica Now",size=11,color=C["text"]),
            legend=dict(orientation="h",y=1.06,x=1,xanchor="right",
                        bgcolor="rgba(255,255,255,.9)",font=dict(size=11),
                        bordercolor=C["border"],borderwidth=1),
            xaxis=dict(type="category",tickangle=-45,showgrid=False,
                       tickfont=dict(size=10,color=C["muted"])),
        )
        fig_t.update_yaxes(title_text="Response mới / ngày",
                           title_font=dict(size=10,color=C["sub"]),
                           showgrid=True,gridcolor=C["line"],
                           tickfont=dict(size=10,color=C["muted"]),secondary_y=False)
        fig_t.update_yaxes(title_text="% Tích lũy",
                           title_font=dict(size=10,color=C["sub"]),
                           range=[0,108],showgrid=False,
                           tickfont=dict(size=10,color=C["muted"]),secondary_y=True)
        st.plotly_chart(fig_t,use_container_width=True)
    section_wrap("Response theo ngày — tích lũy & mới","",_t4)


# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:2rem;padding:18px 0;border-top:1px solid {C['border']};
     display:flex;justify-content:space-between;align-items:center;
     font-size:.72rem;color:{C['muted']};font-family:'SVN-Helvetica Now',sans-serif;">
  <span>
    <strong style="color:{C['navy']};font-family:'SVN-Helvetica Now',sans-serif;
      font-size:.85rem;font-weight:700;letter-spacing:.04em;">GHN EES 2026</strong>
    &nbsp;·&nbsp; Survey Progress Dashboard &nbsp;·&nbsp; EX Team
  </span>
  <span>Render: {now_str}</span>
</div>
""", unsafe_allow_html=True)