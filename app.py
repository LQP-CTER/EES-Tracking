"""
═══════════════════════════════════════════════════════════════════════════
GHN EES 2026 — Survey Progress Dashboard
═══════════════════════════════════════════════════════════════════════════
Hierarchy:  Khối → [Vùng — chỉ Khối Thị Trường] → Phòng ban → Team

Kết nối:
  • Workforce Data  → Google Sheet (.streamlit/secrets.toml [connections.workforce])
  • 4 Survey Files  → 4 Google Sheet riêng (survey_2A, 2B, 3A, 3B)

Fallback URLs hardcoded bên dưới (khi secrets.toml trục trặc).
═══════════════════════════════════════════════════════════════════════════
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import unicodedata
import re

from org_hierarchy import (
    KHOI_LIST, KHOI_TO_DEPTS, DEPT_TO_KHOI, VUNG_LIST,
    resolve_khoi, resolve_vung,
)

KHOI_THI_TRUONG = "Khối Thị Trường"  # Khối duy nhất có Vùng

# ═══════════════════════════════════════════════════════════════════════════
# 1. PAGE CONFIG + BRAND + CSS
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="GHN EES 2026 · Survey Progress", page_icon="./img/Logo_EES.png",
                   layout="wide", initial_sidebar_state="expanded")

BRAND = {
    "NAVY":"#0A1F44","ORANGE":"#FF5200","BLUE":"#006FAD","BEIGE":"#F5F4F0",
    "BG":"#FFFFFF","TEXT":"#333333","MUTED":"#666666","BORDER":"#EAEAEA","GRID":"#EEEEEE",
    "AC":"#0A1F44","PY":"#999999","POS":"#006400","NEG":"#D32F2F",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
.stApp {{ background-color: #FFFFFF; }}
html, body, [class*="css"] {{ font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important; color:{BRAND['TEXT']}; }}
h1,h2,h3,h4 {{ color:{BRAND['NAVY']}!important; font-weight:700!important; letter-spacing:-0.01em; }}

[data-testid="stSidebar"] {{ background-color:{BRAND['BEIGE']}; border-right:1px solid {BRAND['BORDER']}; }}
[data-testid="stSidebar"] * {{ color:{BRAND['NAVY']}; }}
.stSelectbox label,.stMultiSelect label,.stDateInput label {{ font-size:0.72rem!important; font-weight:700!important;
    text-transform:uppercase; letter-spacing:0.08em; color:{BRAND['MUTED']}!important; }}
#MainMenu,footer,header {{ visibility:hidden; }}
.block-container {{ padding-top:1.5rem; padding-bottom:2rem; }}

.report-header {{ border-bottom:3px solid {BRAND['NAVY']}; padding-bottom:16px; margin-bottom:28px;
    display:flex; justify-content:space-between; align-items:flex-end; }}
.report-header .brand-tag {{ font-size:0.75rem; color:{BRAND['BLUE']}; text-transform:uppercase;
    font-weight:700; letter-spacing:0.12em; margin-bottom:6px; }}
.report-header h1 {{ font-size:2rem!important; font-weight:800!important; color:{BRAND['NAVY']}!important;
    line-height:1.1!important; margin:0!important; }}
.report-header h1 .accent {{ color:{BRAND['ORANGE']}; }}
.report-header .subtitle {{ font-size:0.88rem; color:{BRAND['MUTED']}; margin-top:6px; }}
.report-header .meta-label {{ font-size:0.7rem; color:{BRAND['MUTED']}; text-transform:uppercase;
    letter-spacing:0.08em; margin-bottom:4px; }}
.report-header .meta-value {{ font-size:0.85rem; font-weight:600; color:{BRAND['NAVY']}; }}

.kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px; }}
.kpi-card {{ background:#FFF; border:1px solid {BRAND['BORDER']}; border-top:3px solid {BRAND['NAVY']};
    padding:16px 20px; }}
.kpi-card .kpi-label {{ font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;
    color:{BRAND['MUTED']}; font-weight:700; margin-bottom:8px; }}
.kpi-card .kpi-value {{ font-size:2rem; font-weight:800; color:{BRAND['NAVY']}; line-height:1.1; }}
.kpi-card .kpi-sub {{ font-size:0.78rem; margin-top:8px; color:{BRAND['MUTED']}; }}
.kpi-card.done {{ border-top-color:{BRAND['POS']}; }} .kpi-card.done .kpi-value {{ color:{BRAND['POS']}; }}
.kpi-card.pending {{ border-top-color:{BRAND['ORANGE']}; }} .kpi-card.pending .kpi-value {{ color:{BRAND['ORANGE']}; }}
.kpi-card.growth {{ border-top-color:{BRAND['BLUE']}; }}
.delta-pos {{ color:{BRAND['POS']}; font-weight:700; }}
.delta-neg {{ color:{BRAND['NEG']}; font-weight:700; }}
.delta-neu {{ color:{BRAND['MUTED']}; font-weight:500; }}

.ibcs-section {{ background:#FFF; border:1px solid {BRAND['BORDER']}; padding:20px 24px; margin-bottom:18px; }}
.ibcs-section h3 {{ font-size:0.92rem!important; font-weight:700!important;
    border-bottom:2px solid {BRAND['NAVY']}; padding-bottom:8px; margin-bottom:14px!important;
    text-transform:uppercase; letter-spacing:0.05em; color:{BRAND['NAVY']}!important; }}
.section-msg {{ font-size:0.82rem; color:{BRAND['MUTED']}; margin:-8px 0 14px 0; font-style:italic; }}

.ibcs-table {{ width:100%; border-collapse:collapse; font-size:0.8rem; }}
.ibcs-table th {{ background:#F7F7F7; border-bottom:2px solid {BRAND['NAVY']}; padding:8px 10px;
    text-align:left; font-weight:700; text-transform:uppercase; font-size:0.7rem; letter-spacing:0.05em;
    color:{BRAND['MUTED']}; }}
.ibcs-table th.num {{ text-align:right; }}
.ibcs-table td {{ padding:7px 10px; border-bottom:1px solid #EEE; color:{BRAND['TEXT']}; }}
.ibcs-table td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.ibcs-table tr:hover {{ background:#FAFAFA; }}
.ibcs-table .pos {{ color:{BRAND['POS']}; font-weight:600; }}
.ibcs-table .neg {{ color:{BRAND['NEG']}; font-weight:600; }}
.ibcs-table .neutral {{ color:{BRAND['MUTED']}; font-weight:500; }}
.ibcs-table .total-row td {{ border-top:2px solid {BRAND['NAVY']}; font-weight:700; background:#F9F9F9; }}
.mini-bar-bg {{ background:#EEE; height:6px; border-radius:1px; position:relative; min-width:80px; }}
.mini-bar-fill {{ height:6px; border-radius:1px; position:absolute; top:0; left:0; }}

.status-msg {{ border-left:4px solid {BRAND['BLUE']}; background:#FBFBFB; padding:14px 18px;
    margin:16px 0; border-top:1px solid {BRAND['BORDER']}; border-right:1px solid {BRAND['BORDER']};
    border-bottom:1px solid {BRAND['BORDER']}; font-size:0.85rem; }}
.status-msg.warn {{ border-left-color:{BRAND['ORANGE']}; }}
.status-msg.err {{ border-left-color:{BRAND['NEG']}; }}
.status-msg strong {{ color:{BRAND['NAVY']}; display:block; margin-bottom:4px;
    text-transform:uppercase; letter-spacing:0.03em; font-size:0.78rem; }}

.report-footer {{ font-size:0.72rem; color:#AAA; text-align:center; padding:14px;
    border-top:1px solid {BRAND['BORDER']}; margin-top:24px; }}

.stButton > button {{ background:#FFF!important; color:{BRAND['NAVY']}!important;
    border:1px solid {BRAND['NAVY']}!important; border-radius:0!important; font-weight:600!important;
    text-transform:uppercase!important; font-size:0.75rem!important; letter-spacing:0.05em!important;
    padding:0.5rem 1rem!important; width:100%; transition:all 0.2s!important; }}
.stButton > button:hover {{ border-color:{BRAND['ORANGE']}!important; color:{BRAND['ORANGE']}!important; }}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 2. PLOTLY IBCS LAYOUT
# ═══════════════════════════════════════════════════════════════════════════
def ibcs_layout(**kwargs):
    base = dict(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11, color=BRAND["TEXT"]),
        margin=dict(l=50, r=20, t=30, b=40),
        xaxis=dict(showgrid=False, zeroline=True, zerolinecolor="#999", zerolinewidth=1,
                   tickfont=dict(size=10, color=BRAND["MUTED"])),
        yaxis=dict(showgrid=True, gridcolor=BRAND["GRID"], gridwidth=1,
                   zeroline=True, zerolinecolor="#999", zerolinewidth=1,
                   tickfont=dict(size=10, color=BRAND["MUTED"])),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=11, font_family="Inter"),
    )
    base.update(kwargs); return base


# ═══════════════════════════════════════════════════════════════════════════
# 3. COLUMN AUTO-MATCHER
# ═══════════════════════════════════════════════════════════════════════════
def _norm(s):
    if s is None: return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)

CANDIDATES = {
    "timestamp": ["timestamp","thoigian","thoigiandanhdau","submissiondate","submittime",
                  "daterecorded","ngaynop","ngaykhaosat","ngay","date","time"],
    "division":  ["khoi","khoivn","divisionnamevn","division","divisionname"],
    "region":    ["vung","region","buname","bu","mien","khuvuc","area"],
    "department":["phongban","departmentnamevn","department","departmentname","dept","phong"],
    "team":      ["team","teamnamevn","teamname","nhom"],
    "employee_id":["employeeid","idnhanvien","id","manhanvien","mnv","staffid"],
}

def find_col(df, key):
    nmap = {_norm(c): c for c in df.columns}
    for cand in CANDIDATES.get(key, []):
        if _norm(cand) in nmap: return nmap[_norm(cand)]
    for cand in CANDIDATES.get(key, []):
        cn = _norm(cand)
        if not cn: continue
        for nc, orig in nmap.items():
            if cn in nc or nc in cn: return orig
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 4. DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════
SURVEY_GROUPS = ["2A", "2B", "3A", "3B"]

FALLBACK_URLS = {
    "workforce": "https://docs.google.com/spreadsheets/d/1pyNwximXg0aZzahEroGdenxnUIRe1XWbnMy_YRULAn0/edit",
    "survey_2A": "https://docs.google.com/spreadsheets/d/1AS22mEX2_kezYRGsWIDHGEXNQAKD4xG_4W8_jtBDA1o/edit",
    "survey_2B": "https://docs.google.com/spreadsheets/d/1hmATsOmJ9a1WmZsBMSlITC3UH7zAnLRYXqQ2an1ppNo/edit",
    "survey_3A": "https://docs.google.com/spreadsheets/d/1UFtIMOAqZj-uvidePYZiWLiYaq_Lg1rm0ttEJWYowb8/edit",
    "survey_3B": "https://docs.google.com/spreadsheets/d/1E7_G8znrD-ITdvs894e-QUg9AJl7SQS3D6FhyYkeUbc/edit",
}

# Tên worksheet thực tế của từng connection
# ← SỬA ĐÂY nếu tab sheet survey có tên khác
WORKSHEET_NAMES = {
    "workforce": "Workforce Data",
    "survey_2A": "Form Responses 1",
    "survey_2B": "Form Responses 1",
    "survey_3A": "Form Responses 1",
    "survey_3B": "Form Responses 1",
}

def _get_url(conn_name):
    try:
        if "connections" in st.secrets and conn_name in st.secrets["connections"]:
            v = st.secrets["connections"][conn_name].get("spreadsheet", "")
            if v and "ID_SHEET" not in v and v.strip(): return v
    except Exception:
        pass
    return FALLBACK_URLS.get(conn_name, "")


def _canon_khoi(row):
    k = resolve_khoi(dept_name=row.get("department"), khoi_name=row.get("division"))
    return k or row.get("division")

def _canon_vung(row):
    if row.get("khoi_canonical") != KHOI_THI_TRUONG:
        return None
    return resolve_vung(row.get("region")) or row.get("region")


# ─── FIX: Chỉ gọi API 1 lần, TTL 10 phút để tránh rate limit ───────────────
@st.cache_data(ttl=600, show_spinner="Đang tải Workforce Data…")
def load_workforce():
    url = _get_url("workforce")
    if not url:
        raise ValueError("Workforce URL chưa được cấu hình — sửa secrets.toml hoặc FALLBACK_URLS.")

    # Truyền trực tiếp tham số spreadsheet=url cho kết nối
    conn = st.connection("workforce", type=GSheetsConnection)

    # Chỉ gọi 1 lần với tên worksheet đúng, fallback 1 lần nếu fail
    primary_ws = WORKSHEET_NAMES.get("workforce", "Workforce Data")
    df = None
    try:
        # THÊM spreadsheet=url để tránh lỗi "Spreadsheet must be specified" khi Streamlit không tự tìm thấy trong secrets.toml
        df = conn.read(spreadsheet=url, worksheet=primary_ws)
    except Exception:
        pass

    # Nếu tên chính không được, thử đọc sheet đầu tiên (1 lần duy nhất)
    if df is None or len(df) == 0:
        try:
            df = conn.read(spreadsheet=url)
        except Exception as e:
            raise ValueError(f"Không kết nối được Workforce sheet: {str(e)[:200]}")

    if df is None or len(df) == 0:
        raise ValueError(
            f"Sheet '{primary_ws}' trống hoặc không đọc được. "
            "Kiểm tra tên tab sheet trong Google Sheets và sửa WORKSHEET_NAMES['workforce'] trong app.py."
        )

    df = df.dropna(how="all")
    rename_map = {}
    for key in ["division","region","department","team","employee_id"]:
        col = find_col(df, key)
        if col: rename_map[col] = key
    df = df.rename(columns=rename_map)
    for c in ["division","region","department","team","employee_id"]:
        if c not in df.columns: df[c] = None
    for c in ["division","region","department","team"]:
        df[c] = df[c].astype(str).str.strip().replace({"nan":None,"":None,"None":None})

    df["khoi_canonical"] = df.apply(_canon_khoi, axis=1)
    df["vung_canonical"] = df.apply(_canon_vung, axis=1)
    return df


# ─── FIX: TTL 10 phút, gọi API 1 lần mỗi survey group ─────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def load_survey(group_name):
    conn_name = f"survey_{group_name}"
    url = _get_url(conn_name)
    if not url:
        return pd.DataFrame(), f"Chưa có URL cho nhóm {group_name}."
    try:
        conn = st.connection(conn_name, type=GSheetsConnection)
        primary_ws = WORKSHEET_NAMES.get(conn_name, "Form Responses 1")
        df = None

        # Thử tên chính xác trước
        try:
            # THÊM spreadsheet=url
            df = conn.read(spreadsheet=url, worksheet=primary_ws)
        except Exception:
            pass

        # Fallback: đọc sheet đầu tiên (1 lần)
        if df is None or len(df) == 0:
            try:
                # THÊM spreadsheet=url
                df = conn.read(spreadsheet=url)
            except Exception:
                pass

        if df is None:
            return pd.DataFrame(), f"Không đọc được {conn_name}."
    except Exception as e:
        return pd.DataFrame(), f"Không kết nối được {conn_name}: {str(e)[:150]}"

    df = df.dropna(how="all")
    if len(df) == 0: return df, None

    rename_map = {}
    for key in ["timestamp","division","region","department","team","employee_id"]:
        col = find_col(df, key)
        if col: rename_map[col] = key
    df = df.rename(columns=rename_map)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", dayfirst=True)
    else:
        df["timestamp"] = pd.NaT

    for c in ["division","region","department","team"]:
        if c not in df.columns: df[c] = None
        else: df[c] = df[c].astype(str).str.strip().replace({"nan":None,"":None,"None":None})

    df["khoi_canonical"] = df.apply(_canon_khoi, axis=1)
    df["vung_canonical"] = df.apply(_canon_vung, axis=1)
    df["survey_group"] = group_name
    return df, None


@st.cache_data(ttl=600, show_spinner="Đang tải toàn bộ khảo sát…")
def load_all_surveys():
    parts, warnings = [], []
    for g in SURVEY_GROUPS:
        part, err = load_survey(g)
        if err: warnings.append(err)
        elif len(part) > 0: parts.append(part)
    if parts:
        return pd.concat(parts, ignore_index=True), warnings
    return pd.DataFrame(columns=["timestamp","division","region","department","team",
                                  "employee_id","khoi_canonical","vung_canonical","survey_group"]), warnings


# ═══════════════════════════════════════════════════════════════════════════
# 5. HEADER
# ═══════════════════════════════════════════════════════════════════════════
now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
st.markdown(f"""
<div class="report-header">
  <div>
    <div class="brand-tag">GiaoHangNhanh · Internal</div>
    <h1><span class="accent">EES 2026</span> SURVEY PROGRESS</h1>
    <div class="subtitle">Báo cáo tiến độ khảo sát EES · Nhóm 2A · 2B · 3A · 3B</div>
  </div>
  <div style="text-align:right;">
    <div class="meta-label">Cập nhật lần cuối</div>
    <div class="meta-value">{now_str}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 6. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════
try:
    df_wf = load_workforce()
except Exception as e:
    st.markdown(f'<div class="status-msg err"><strong>Lỗi Workforce</strong>'
                f'<code>{str(e)[:300]}</code></div>', unsafe_allow_html=True)
    st.stop()

try:
    df_sv, warn_list = load_all_surveys()
except Exception as e:
    st.markdown(f'<div class="status-msg err"><strong>Lỗi Survey</strong>'
                f'<code>{str(e)[:300]}</code></div>', unsafe_allow_html=True)
    df_sv, warn_list = pd.DataFrame(), []


# ═══════════════════════════════════════════════════════════════════════════
# 7. SIDEBAR FILTERS
# ═══════════════════════════════════════════════════════════════════════════
st.sidebar.markdown(f"""
<div style='border-bottom:2px solid {BRAND["NAVY"]}; padding-bottom:10px; margin-bottom:14px;'>
<strong style='font-size:0.95rem;'>📊 BỘ LỌC BÁO CÁO</strong><br/>
<span style='font-size:0.72rem; color:#888;'>Report Filters</span>
</div>""", unsafe_allow_html=True)

if st.sidebar.button("🔄 Đồng bộ dữ liệu"):
    st.cache_data.clear(); st.rerun()

# Debug expander
with st.sidebar.expander("🔍 Debug Config", expanded=False):
    try:
        if "connections" in st.secrets:
            st.caption(f"**Secrets:** ✓ {', '.join(list(st.secrets['connections'].keys()))}")
        else:
            st.caption("**Secrets:** ⚠ không có [connections]")
    except Exception as e:
        st.caption(f"**Secrets:** ✗ {str(e)[:80]}")
    for cn in ["workforce"] + [f"survey_{g}" for g in SURVEY_GROUPS]:
        url = _get_url(cn)
        ws_name = WORKSHEET_NAMES.get(cn, "—")
        st.caption(f"• `{cn}` [{ws_name}]: {'✓' if url else '❌ trống'}")

def safe_unique(s):
    return sorted([x for x in s.dropna().unique() if str(x).strip() != ""])

# Nhóm khảo sát
sel_groups = st.sidebar.multiselect("NHÓM KHẢO SÁT", SURVEY_GROUPS, default=SURVEY_GROUPS)

# ─── KHỐI ─────────────────────────────────────────────────────────────
khoi_in_data = set(df_wf["khoi_canonical"].dropna().unique())
khoi_opts = [k for k in KHOI_LIST if k in khoi_in_data] + sorted(khoi_in_data - set(KHOI_LIST))
sel_khoi = st.sidebar.multiselect("KHỐI (DIVISION)", khoi_opts)

df_wf_f = df_wf.copy()
if sel_khoi:
    df_wf_f = df_wf_f[df_wf_f["khoi_canonical"].isin(sel_khoi)]

# ─── VÙNG (chỉ show khi Khối Thị Trường liên quan) ─────────────────────
is_ktt_relevant = (not sel_khoi) or (KHOI_THI_TRUONG in sel_khoi)
sel_vung = []
if is_ktt_relevant:
    vung_in_data = set(df_wf_f["vung_canonical"].dropna().unique())
    vung_opts = [v for v in VUNG_LIST if v in vung_in_data] + sorted(vung_in_data - set(VUNG_LIST))
    if vung_opts:
        sel_vung = st.sidebar.multiselect(
            "VÙNG (chỉ áp dụng Khối Thị Trường)", vung_opts,
            help="Vùng là cấp nằm trong Khối Thị Trường.",
        )
        if sel_vung:
            mask_ktt = df_wf_f["khoi_canonical"] == KHOI_THI_TRUONG
            df_wf_f = df_wf_f[~mask_ktt | df_wf_f["vung_canonical"].isin(sel_vung)]
else:
    st.sidebar.caption("ℹ️ Vùng chỉ áp dụng cho Khối Thị Trường.")

# ─── PHÒNG BAN ────────────────────────────────────────────────────────
dept_opts = safe_unique(df_wf_f["department"])
sel_dept = st.sidebar.multiselect("PHÒNG BAN", dept_opts)
if sel_dept:
    df_wf_f = df_wf_f[df_wf_f["department"].isin(sel_dept)]

# ─── TEAM ─────────────────────────────────────────────────────────────
team_opts = safe_unique(df_wf_f["team"]) if "team" in df_wf_f.columns else []
sel_team = st.sidebar.multiselect("TEAM", team_opts) if team_opts else []
if sel_team:
    df_wf_f = df_wf_f[df_wf_f["team"].isin(sel_team)]

# ─── Apply cùng filter cho survey ─────────────────────────────────────
df_sv_f = df_sv.copy() if len(df_sv) > 0 else df_sv
if len(df_sv_f) > 0:
    if sel_groups:
        df_sv_f = df_sv_f[df_sv_f["survey_group"].isin(sel_groups)]
    if sel_khoi:
        df_sv_f = df_sv_f[df_sv_f["khoi_canonical"].isin(sel_khoi)]
    if sel_vung:
        mask_ktt = df_sv_f["khoi_canonical"] == KHOI_THI_TRUONG
        df_sv_f = df_sv_f[~mask_ktt | df_sv_f["vung_canonical"].isin(sel_vung)]
    if sel_dept:
        df_sv_f = df_sv_f[df_sv_f["department"].isin(sel_dept)]
    if sel_team and "team" in df_sv_f.columns:
        df_sv_f = df_sv_f[df_sv_f["team"].isin(sel_team)]

# ─── Date range filter ────────────────────────────────────────────────
if len(df_sv_f) > 0 and df_sv_f["timestamp"].notna().any():
    ts_min = df_sv_f["timestamp"].min().date()
    ts_max = df_sv_f["timestamp"].max().date()
    date_range = st.sidebar.date_input(
        "KHOẢNG NGÀY KHẢO SÁT",
        value=(ts_min, ts_max), min_value=ts_min, max_value=ts_max,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        d0, d1 = date_range
        mask = (df_sv_f["timestamp"].dt.date >= d0) & (df_sv_f["timestamp"].dt.date <= d1)
        df_sv_f = df_sv_f[mask | df_sv_f["timestamp"].isna()]

# Legend
st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='font-size:0.75rem; line-height:1.8;'>
<strong style="font-size:0.72rem; letter-spacing:0.05em;">KÝ HIỆU IBCS</strong><br/>
<span style='display:inline-block; width:14px; height:10px; background:{BRAND["AC"]}; margin-right:4px; vertical-align:middle'></span> Hiện tại (AC)<br/>
<span style='display:inline-block; width:14px; height:10px; background:{BRAND["PY"]}; margin-right:4px; vertical-align:middle'></span> Kỳ trước (PY)<br/>
<span style='display:inline-block; width:14px; height:10px; background:{BRAND["POS"]}; margin-right:4px; vertical-align:middle'></span> Δ Positive<br/>
<span style='display:inline-block; width:14px; height:10px; background:{BRAND["NEG"]}; margin-right:4px; vertical-align:middle'></span> Δ Negative<br/>
</div>
""", unsafe_allow_html=True)

if warn_list:
    for w in warn_list:
        st.markdown(f'<div class="status-msg warn"><strong>Cảnh báo</strong>{w}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 8. KPI COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════
total_hc = int(df_wf_f["employee_id"].nunique()) if df_wf_f["employee_id"].notna().any() else len(df_wf_f)
total_done = len(df_sv_f)
total_pending = max(total_hc - total_done, 0)
pct_done = (total_done / total_hc * 100) if total_hc > 0 else 0.0

today = datetime.now().date()
yesterday = today - timedelta(days=1)
if "timestamp" in df_sv_f.columns and df_sv_f["timestamp"].notna().any():
    df_sv_f = df_sv_f.copy()
    df_sv_f["_date"] = df_sv_f["timestamp"].dt.date
    n_today = int((df_sv_f["_date"] == today).sum())
    n_yesterday = int((df_sv_f["_date"] == yesterday).sum())
else:
    n_today, n_yesterday = 0, 0
growth = n_today - n_yesterday

def fmt_delta(val, suffix=""):
    if val > 0: return f'<span class="delta-pos">▲ +{val:,}{suffix}</span>'
    if val < 0: return f'<span class="delta-neg">▼ {val:,}{suffix}</span>'
    return f'<span class="delta-neu">— 0{suffix}</span>'

st.markdown(f"""
<div class="kpi-grid">
<div class="kpi-card">
  <div class="kpi-label">👥 Tổng Nhân Sự</div>
  <div class="kpi-value">{total_hc:,}</div>
  <div class="kpi-sub">Headcount trong phạm vi bộ lọc</div>
</div>
<div class="kpi-card done">
  <div class="kpi-label">✅ Số Đã Làm</div>
  <div class="kpi-value">{total_done:,}</div>
  <div class="kpi-sub">Tổng response · {pct_done:.1f}% / Tổng HC</div>
</div>
<div class="kpi-card pending">
  <div class="kpi-label">⏳ Số Chưa Làm</div>
  <div class="kpi-value">{total_pending:,}</div>
  <div class="kpi-sub">Ước tính = HC − Response (aggregate)</div>
</div>
<div class="kpi-card growth">
  <div class="kpi-label">📈 Tăng Trưởng (Hôm Nay)</div>
  <div class="kpi-value">{n_today:,}</div>
  <div class="kpi-sub">{fmt_delta(growth)} so với hôm qua ({n_yesterday:,})</div>
</div>
</div>
""", unsafe_allow_html=True)

if len(df_sv) == 0:
    st.markdown(f"""
    <div class="status-msg warn">
      <strong>Chưa có dữ liệu khảo sát</strong>
      4 sheet survey (2A, 2B, 3A, 3B) chưa kết nối hoặc chưa có response.
      Kiểm tra <code>.streamlit/secrets.toml</code> có đủ 4 connection:
      <code>survey_2A</code>, <code>survey_2B</code>, <code>survey_3A</code>, <code>survey_3B</code>.
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════
# 9. SECTION — XU HƯỚNG ADOPTION THEO THỜI GIAN
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="ibcs-section">', unsafe_allow_html=True)
st.markdown("<h3>XU HƯỚNG ADOPTION THEO THỜI GIAN</h3>", unsafe_allow_html=True)

if df_sv_f["timestamp"].notna().any():
    tdf = df_sv_f.dropna(subset=["timestamp"]).copy()
    tdf["_date"] = tdf["timestamp"].dt.date
    daily = tdf.groupby("_date").size().rename("new_users").reset_index()
    daily = daily.sort_values("_date").reset_index(drop=True)
    daily["cum"] = daily["new_users"].cumsum()
    daily["pct"] = (daily["cum"] / total_hc * 100) if total_hc > 0 else 0
    daily["date_lbl"] = daily["_date"].apply(lambda d: d.strftime("%d/%m"))

    first_pct, last_pct = daily["pct"].iloc[0], daily["pct"].iloc[-1]
    trend_msg = (f'Tỷ lệ adoption tăng từ <b>{first_pct:.1f}%</b> lên <b>{last_pct:.1f}%</b> '
                 f'(+{last_pct-first_pct:.1f}pp) trong {len(daily)} kỳ báo cáo')
    st.markdown(f'<p class="section-msg">{trend_msg}</p>', unsafe_allow_html=True)

    fig_t = make_subplots(specs=[[{"secondary_y": True}]])
    fig_t.add_trace(go.Bar(
        x=daily["date_lbl"], y=daily["new_users"],
        name="User mới", marker_color=BRAND["PY"], marker_line=dict(width=0),
        opacity=0.6,
        hovertemplate="<b>%{x}</b><br>User mới: %{y:,}<extra></extra>",
    ), secondary_y=False)
    fig_t.add_trace(go.Scatter(
        x=daily["date_lbl"], y=daily["pct"],
        name="% Adoption", mode="lines+markers+text",
        line=dict(color=BRAND["NAVY"], width=2.5),
        marker=dict(size=5, color=BRAND["NAVY"]),
        text=[f"{v:.1f}%" for v in daily["pct"]],
        textposition="top center", textfont=dict(size=9, color=BRAND["NAVY"]),
        hovertemplate="<b>%{x}</b><br>Adoption: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)

    fig_t.update_layout(
        **ibcs_layout(height=380, margin=dict(l=50, r=50, t=20, b=50), showlegend=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        bargap=0.3,
    )
    fig_t.update_xaxes(type="category", tickangle=-45)
    fig_t.update_yaxes(title_text="User mới (người)", secondary_y=False, showgrid=False)
    fig_t.update_yaxes(title_text="Tỷ lệ Adoption (%)", secondary_y=True, range=[0, 105],
                        showgrid=True, gridcolor=BRAND["GRID"])
    st.plotly_chart(fig_t, use_container_width=True)
else:
    st.info("Chưa có cột timestamp hợp lệ trong data survey.")

st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 10. SECTION — PHÂN TÍCH THEO KHỐI · TỶ LỆ ADOPTION
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="ibcs-section">', unsafe_allow_html=True)
st.markdown("<h3>PHÂN TÍCH THEO KHỐI (DIVISION) · TỶ LỆ ADOPTION</h3>", unsafe_allow_html=True)

if df_sv_f["timestamp"].notna().any():
    sv_today = df_sv_f[df_sv_f["timestamp"].dt.date <= today]
    sv_yest  = df_sv_f[df_sv_f["timestamp"].dt.date <= yesterday]
else:
    sv_today = df_sv_f.copy()
    sv_yest  = df_sv_f.iloc[0:0]

wf_by_khoi = df_wf_f.groupby("khoi_canonical").size().rename("hc")
sv_today_k = sv_today.groupby("khoi_canonical").size().rename("ac") if len(sv_today) else pd.Series(dtype=int, name="ac")
sv_yest_k  = sv_yest.groupby("khoi_canonical").size().rename("py") if len(sv_yest) else pd.Series(dtype=int, name="py")
khoi_df = pd.concat([wf_by_khoi, sv_today_k, sv_yest_k], axis=1).fillna(0).astype(int)
khoi_df["pct_ac"] = (khoi_df["ac"] / khoi_df["hc"].replace(0, pd.NA) * 100).fillna(0).round(1)
khoi_df["pct_py"] = (khoi_df["py"] / khoi_df["hc"].replace(0, pd.NA) * 100).fillna(0).round(1)
khoi_df["delta_pct"] = (khoi_df["pct_ac"] - khoi_df["pct_py"]).round(1)
khoi_df["delta_abs"] = khoi_df["ac"] - khoi_df["py"]
khoi_df = khoi_df.reset_index()
khoi_df = khoi_df.rename(columns={khoi_df.columns[0]: "name"})
khoi_df = khoi_df[khoi_df["name"].notna()]
khoi_df = khoi_df.sort_values("pct_ac", ascending=True).reset_index(drop=True)

if len(khoi_df) > 0:
    top = khoi_df.sort_values("pct_ac", ascending=False).iloc[0]
    bot = khoi_df.sort_values("pct_ac", ascending=True).iloc[0]
    msg = f'Khối cao nhất: <b>{top["name"]}</b> ({top["pct_ac"]:.1f}%) · Thấp nhất: <b>{bot["name"]}</b> ({bot["pct_ac"]:.1f}%)'
    st.markdown(f'<p class="section-msg">{msg}</p>', unsafe_allow_html=True)

    col_chart, col_tbl = st.columns([3, 2])

    with col_chart:
        fig_k = go.Figure()
        fig_k.add_trace(go.Bar(
            y=khoi_df["name"], x=khoi_df["pct_py"], orientation="h",
            name=f"Kỳ trước ({yesterday.strftime('%d/%m')})",
            marker_color=BRAND["PY"], marker_line=dict(width=0),
            text=[f"{v:.1f}%" for v in khoi_df["pct_py"]],
            textposition="outside", textfont=dict(size=9, color="#999"),
            hovertemplate="<b>%{y}</b><br>Kỳ trước: %{x:.1f}%<extra></extra>",
        ))
        fig_k.add_trace(go.Bar(
            y=khoi_df["name"], x=khoi_df["pct_ac"], orientation="h",
            name=f"Hiện tại ({today.strftime('%d/%m')})",
            marker_color=BRAND["NAVY"], marker_line=dict(width=0),
            text=[f"{v:.1f}%" for v in khoi_df["pct_ac"]],
            textposition="outside", textfont=dict(size=9, color=BRAND["NAVY"]),
            hovertemplate="<b>%{y}</b><br>Hiện tại: %{x:.1f}%<extra></extra>",
        ))
        fig_k.update_layout(
            **ibcs_layout(
                height=max(320, len(khoi_df) * 45 + 80),
                margin=dict(l=220, r=60, t=10, b=30),
                barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        )
        fig_k.update_xaxes(range=[0, 105], dtick=25, showgrid=True, gridcolor=BRAND["GRID"])
        fig_k.update_yaxes(showgrid=False, tickfont=dict(size=10))
        st.plotly_chart(fig_k, use_container_width=True)

    with col_tbl:
        rows = ""
        sorted_k = khoi_df.sort_values("pct_ac", ascending=False)
        for _, r in sorted_k.iterrows():
            if r["delta_pct"] > 0: dc, ds = "pos", "+"
            elif r["delta_pct"] < 0: dc, ds = "neg", ""
            else: dc, ds = "neutral", ""
            bar_w = min(r["pct_ac"], 100)
            rows += f"""
<tr>
<td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{r['name']}">{r['name']}</td>
<td class="num">{int(r['hc']):,}</td>
<td class="num">{int(r['ac']):,}</td>
<td class="num" style="font-weight:600">{r['pct_ac']:.1f}%</td>
<td><div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{bar_w}%;background:{BRAND['NAVY']};"></div></div></td>
<td class="num {dc}">{ds}{r['delta_pct']:.1f}pp</td>
<td class="num {dc}">{ds}{int(r['delta_abs']):,}</td>
</tr>"""
        t_hc = int(sorted_k["hc"].sum()); t_ac = int(sorted_k["ac"].sum()); t_py = int(sorted_k["py"].sum())
        t_pct_ac = (t_ac/t_hc*100) if t_hc > 0 else 0
        t_pct_py = (t_py/t_hc*100) if t_hc > 0 else 0
        t_dpct = t_pct_ac - t_pct_py; t_dabs = t_ac - t_py
        if t_dpct > 0: tdc, tds = "pos", "+"
        elif t_dpct < 0: tdc, tds = "neg", ""
        else: tdc, tds = "neutral", ""
        rows += f"""
<tr class="total-row">
<td><strong>TỔNG</strong></td>
<td class="num">{t_hc:,}</td>
<td class="num">{t_ac:,}</td>
<td class="num" style="font-weight:700">{t_pct_ac:.1f}%</td>
<td></td>
<td class="num {tdc}">{tds}{t_dpct:.1f}pp</td>
<td class="num {tdc}">{tds}{t_dabs:,}</td>
</tr>"""

        st.markdown(f"""
<table class="ibcs-table">
<thead><tr>
<th>Khối</th><th class="num">HC</th><th class="num">Active</th><th class="num">%</th>
<th style="min-width:80px"></th><th class="num">Δ%</th><th class="num">Δ Abs</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
""", unsafe_allow_html=True)
else:
    st.info("Không đủ dữ liệu theo Khối.")

st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 11. SECTION — CHI TIẾT PHÂN BỔ (DRILL-DOWN TABLE)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="ibcs-section">', unsafe_allow_html=True)
st.markdown("<h3>CHI TIẾT PHÂN BỔ (DRILL-DOWN TABLE)</h3>", unsafe_allow_html=True)

breakdown_level = st.selectbox(
    "Phân tích theo cấp:",
    ["Khối", "Khối › Vùng (Khối Thị Trường)", "Khối › Phòng Ban",
     "Khối › Vùng › Phòng Ban", "Khối › Phòng Ban › Team"],
    label_visibility="collapsed",
)

GROUP_MAP = {
    "Khối": ["khoi_canonical"],
    "Khối › Vùng (Khối Thị Trường)": ["khoi_canonical", "vung_canonical"],
    "Khối › Phòng Ban": ["khoi_canonical", "department"],
    "Khối › Vùng › Phòng Ban": ["khoi_canonical", "vung_canonical", "department"],
    "Khối › Phòng Ban › Team": ["khoi_canonical", "department", "team"],
}
group_cols = GROUP_MAP[breakdown_level]

wf_bd = df_wf_f.groupby(group_cols, dropna=False).size().rename("hc")
sv_today_bd = sv_today.groupby(group_cols, dropna=False).size().rename("ac") if len(sv_today) else pd.Series(dtype=int, name="ac")
sv_yest_bd  = sv_yest.groupby(group_cols, dropna=False).size().rename("py") if len(sv_yest) else pd.Series(dtype=int, name="py")

bd = pd.concat([wf_bd, sv_today_bd, sv_yest_bd], axis=1).fillna(0).astype(int)
bd["pending"] = (bd["hc"] - bd["ac"]).clip(lower=0)
bd["pct_ac"] = (bd["ac"] / bd["hc"].replace(0, pd.NA) * 100).fillna(0).round(1)
bd["pct_py"] = (bd["py"] / bd["hc"].replace(0, pd.NA) * 100).fillna(0).round(1)
bd["delta_pct"] = (bd["pct_ac"] - bd["pct_py"]).round(1)
bd["delta_abs"] = bd["ac"] - bd["py"]
bd = bd.reset_index().sort_values("pct_ac", ascending=False).reset_index(drop=True)

if len(bd) > 0:
    rows = ""
    for idx, r in bd.iterrows():
        if r["delta_pct"] > 0: dc, ds = "pos", "+"
        elif r["delta_pct"] < 0: dc, ds = "neg", ""
        else: dc, ds = "neutral", ""
        bar_w = min(r["pct_ac"], 100)
        name_parts = [str(r[c]) for c in group_cols if pd.notna(r[c]) and str(r[c]).strip()]
        disp = " › ".join(name_parts) if name_parts else "Chưa xác định"
        rows += f"""
<tr>
<td class="num" style="color:#aaa; font-size:0.7rem">{idx+1}</td>
<td style="max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{disp}">{disp}</td>
<td class="num">{int(r['hc']):,}</td>
<td class="num">{int(r['ac']):,}</td>
<td class="num" style="color:#888">{int(r['pending']):,}</td>
<td class="num" style="font-weight:600">{r['pct_ac']:.1f}%</td>
<td><div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{bar_w}%;background:{BRAND['NAVY']};"></div></div></td>
<td class="num" style="color:#888">{r['pct_py']:.1f}%</td>
<td class="num {dc}">{ds}{r['delta_pct']:.1f}pp</td>
<td class="num {dc}">{ds}{int(r['delta_abs']):,}</td>
</tr>"""
    t_hc = int(bd["hc"].sum()); t_ac = int(bd["ac"].sum()); t_py = int(bd["py"].sum())
    t_pending = t_hc - t_ac
    t_pct_ac = (t_ac/t_hc*100) if t_hc > 0 else 0
    t_pct_py = (t_py/t_hc*100) if t_hc > 0 else 0
    t_dpct = t_pct_ac - t_pct_py; t_dabs = t_ac - t_py
    if t_dpct > 0: tdc, tds = "pos", "+"
    elif t_dpct < 0: tdc, tds = "neg", ""
    else: tdc, tds = "neutral", ""
    rows += f"""
<tr class="total-row">
<td></td>
<td><strong>TỔNG CỘNG</strong></td>
<td class="num">{t_hc:,}</td>
<td class="num">{t_ac:,}</td>
<td class="num" style="color:#888">{t_pending:,}</td>
<td class="num" style="font-weight:700">{t_pct_ac:.1f}%</td>
<td></td>
<td class="num" style="color:#888">{t_pct_py:.1f}%</td>
<td class="num {tdc}">{tds}{t_dpct:.1f}pp</td>
<td class="num {tdc}">{tds}{t_dabs:,}</td>
</tr>"""

    st.markdown(f"""
<div style="overflow-x:auto;">
<table class="ibcs-table">
<thead>
<tr>
<th class="num" style="width:30px">#</th>
<th>{breakdown_level}</th>
<th class="num">HC</th>
<th class="num">Active</th>
<th class="num">Chưa</th>
<th class="num">% AC</th>
<th style="min-width:100px"></th>
<th class="num">% PY</th>
<th class="num">Δ%</th>
<th class="num">Δ Abs</th>
</tr>
</thead>
<tbody>{rows}</tbody>
</table>
</div>
""", unsafe_allow_html=True)
else:
    st.info("Không có dữ liệu cho cấu hình drill-down hiện tại.")

st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 12. SECTION — MATRIX KHỐI THỊ TRƯỜNG × VÙNG (chỉ show khi có data)
# ═══════════════════════════════════════════════════════════════════════════
df_ktt_wf = df_wf_f[df_wf_f["khoi_canonical"] == KHOI_THI_TRUONG]
df_ktt_sv = df_sv_f[df_sv_f["khoi_canonical"] == KHOI_THI_TRUONG]

if len(df_ktt_wf) > 0 and df_ktt_wf["vung_canonical"].notna().any():
    st.markdown('<div class="ibcs-section">', unsafe_allow_html=True)
    st.markdown("<h3>MATRIX · KHỐI THỊ TRƯỜNG × VÙNG</h3>", unsafe_allow_html=True)
    st.markdown('<p class="section-msg">Heatmap tỷ lệ hoàn thành theo Vùng (chỉ áp dụng cho Khối Thị Trường)</p>',
                unsafe_allow_html=True)

    wf_v = df_ktt_wf.groupby("vung_canonical").size().rename("hc")
    sv_v = df_ktt_sv.groupby("vung_canonical").size().rename("ac") if len(df_ktt_sv) else pd.Series(dtype=int, name="ac")
    mx = pd.concat([wf_v, sv_v], axis=1).fillna(0).astype(int)
    mx["pct"] = (mx["ac"] / mx["hc"].replace(0, pd.NA) * 100).fillna(0).round(1)
    mx = mx.reset_index()
    mx = mx.rename(columns={mx.columns[0]: "vung"})
    order_map = {v: i for i, v in enumerate(VUNG_LIST)}
    mx["_ord"] = mx["vung"].map(lambda v: order_map.get(v, 999))
    mx = mx.sort_values("_ord").reset_index(drop=True)
    mx = mx[mx["vung"].notna() & (mx["vung"].astype(str).str.strip() != "")]

    fig_mat = go.Figure(data=go.Heatmap(
        z=[mx["pct"].values],
        x=mx["vung"], y=[KHOI_THI_TRUONG],
        colorscale=[[0.0, "#FFFFFF"], [0.25, "#FFE0CC"], [0.5, "#FF9966"],
                    [0.75, BRAND["ORANGE"]], [1.0, BRAND["NAVY"]]],
        zmin=0, zmax=100,
        text=[[f"{int(mx.iloc[i]['ac'])}/{int(mx.iloc[i]['hc'])}<br><b>{mx.iloc[i]['pct']:.0f}%</b>"
                for i in range(len(mx))]],
        texttemplate="%{text}", textfont=dict(size=10, family="Inter"),
        hovertemplate="<b>%{x}</b><br>Đã làm: %{z:.1f}%<extra></extra>",
        colorbar=dict(title=dict(text="% Hoàn thành", font=dict(size=10)),
                      thickness=12, len=0.7, tickfont=dict(size=9)),
    ))
    fig_mat.update_layout(**ibcs_layout(height=200, margin=dict(l=180, r=40, t=20, b=60)))
    fig_mat.update_xaxes(side="top", tickangle=-25, tickfont=dict(size=10))
    fig_mat.update_yaxes(tickfont=dict(size=10))
    st.plotly_chart(fig_mat, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="report-footer">
<strong>GHN EES 2026</strong> · Survey Progress Dashboard ·
Built with IBCS standards · Developed by <b>EX Team</b> ·
Last render: {now_str}
</div>
""", unsafe_allow_html=True)