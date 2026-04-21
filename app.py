import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

# 1. CẤU HÌNH TRANG (Page Config)
st.set_page_config(
    page_title="GHN EES 2026 | Báo cáo Trạng thái",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM CSS - ĐẲNG CẤP IBCS x GHN BRAND
st.markdown("""
<style>
    /* Tổng thể: Nền trắng tinh khiết, font chữ hiện đại, rõ nét */
    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Ẩn Header mặc định của Streamlit để giao diện sạch hơn */
    header {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Tùy chỉnh Sidebar: Nền Beige nhạt của Landing Page, viền siêu mảnh */
    [data-testid="stSidebar"] {
        background-color: #F5F4F0;
        border-right: 1px solid #EAEAEA;
    }
    [data-testid="stSidebar"] * {
        color: #0A1F44 !important;
    }
    
    /* Nút bấm (Button): Phẳng, góc cạnh, chuyên nghiệp */
    .stButton > button {
        background-color: #FFFFFF !important;
        color: #0A1F44 !important;
        border: 1px solid #0A1F44 !important;
        border-radius: 0px !important; /* IBCS ưu tiên góc vuông */
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.05em !important;
        padding: 0.6rem 1.2rem !important;
        width: 100%;
        transition: all 0.2s ease-in-out !important;
    }
    /* Hiệu ứng Hover mượt mà với Cam GHN */
    .stButton > button:hover {
        border-color: #FF5200 !important;
        color: #FF5200 !important;
        box-shadow: 0 2px 8px rgba(255, 82, 0, 0.1) !important;
    }

    /* Thẻ Metric (KPI): Thiết kế chuẩn báo cáo tài chính */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-top: 3px solid #0A1F44; /* Thanh định vị thị giác */
        border-left: 1px solid #EAEAEA;
        border-right: 1px solid #EAEAEA;
        border-bottom: 1px solid #EAEAEA;
        padding: 1rem 1.5rem;
    }
    [data-testid="stMetricValue"] {
        color: #0A1F44 !important;
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #666666 !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.02em !important;
        margin-bottom: 0.5rem;
    }
    
    /* Bảng dữ liệu (Dataframe) */
    [data-testid="stDataFrame"] {
        border: 1px solid #EAEAEA !important;
    }
</style>
""", unsafe_allow_html=True)

# Lấy thời gian hiện tại cho báo cáo
current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# 3. HEADER THEO CHUẨN BÁO CÁO (FORMAL REPORT HEADER)
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #0A1F44; padding-bottom: 15px; margin-bottom: 30px;">
    <div>
        <div style="font-size: 0.85rem; color: #006FAD; text-transform: uppercase; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 8px;">
            GiaoHangNhanh • Internal
        </div>
        <div style="font-size: 2.2rem; font-weight: 800; color: #0A1F44; line-height: 1.1; letter-spacing: -0.02em;">
            <span style="color: #FF5200;">EES 2026</span> DASHBOARD
        </div>
        <div style="font-size: 0.95rem; color: #555555; margin-top: 6px; font-weight: 400;">
            Báo cáo giám sát luồng dữ liệu khảo sát trực tuyến
        </div>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 0.75rem; color: #888888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
            Cập nhật lần cuối
        </div>
        <div style="font-size: 0.9rem; font-weight: 600; color: #0A1F44;">
            {current_time}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 4. SIDEBAR - BẢNG ĐIỀU KHIỂN UI/UX
st.sidebar.markdown("""
<div style='font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #0A1F44; margin-bottom: 20px; border-bottom: 1px solid #EAEAEA; padding-bottom: 10px;'>
    Tác vụ quản trị
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("Đồng bộ dữ liệu"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("""
<div style="font-size: 0.8rem; color: #666666; line-height: 1.6; margin-top: 20px; background-color: #FFFFFF; padding: 12px; border-left: 3px solid #006FAD;">
    <strong>Cơ chế đồng bộ:</strong><br>
    Hệ thống sẽ xóa bộ nhớ đệm và truy xuất trực tiếp tập dữ liệu mới nhất từ Google Sheets.
</div>
""", unsafe_allow_html=True)

# Hàm hiển thị thông báo IBCS (Đẹp, phẳng, tối giản)
def ibcs_message(title, text, msg_type="info"):
    colors = {
        "info": "#006FAD",    
        "warning": "#FF5200", 
        "error": "#D32F2F",   
        "success": "#0A1F44"  
    }
    color = colors.get(msg_type, "#0A1F44")
    st.markdown(f"""
    <div style="border-left: 4px solid {color}; background-color: #FBFBFB; padding: 16px 20px; margin: 20px 0; border-top: 1px solid #EAEAEA; border-right: 1px solid #EAEAEA; border-bottom: 1px solid #EAEAEA;">
        <div style="font-weight: 700; font-size: 0.95rem; color: {color}; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.02em;">{title}</div>
        <div style="font-size: 0.9rem; color: #444444; line-height: 1.5;">{text}</div>
    </div>
    """, unsafe_allow_html=True)

# 5. HÀM KẾT NỐI VÀ TẢI DỮ LIỆU
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
    df = df.dropna(how="all")
    return df

# 6. KHUNG HIỂN THỊ CHÍNH
try:
    with st.spinner("Đang trích xuất dữ liệu từ máy chủ..."):
        df = load_data()
    
    if df.empty:
        ibcs_message("Cảnh báo dữ liệu", "Kết nối Google Sheets thành công. Tuy nhiên, tập dữ liệu gốc hiện tại đang trống (0 bản ghi).", "warning")
    else:
        # Khung KPI
        st.markdown("<div style='font-size: 1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #0A1F44; margin-bottom: 15px;'>Tổng quan luồng dữ liệu</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Tổng số bản ghi", value=f"{len(df):,}")
        with col2:
            st.metric(label="Trạng thái kết nối", value="Ổn định")
        with col3:
            st.metric(label="Cấu trúc cột", value=f"{len(df.columns)} Cột")
            
        st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)
        
        # Tiêu đề bảng dữ liệu
        st.markdown("""
        <div style="border-bottom: 1px solid #EAEAEA; padding-bottom: 8px; margin-bottom: 15px;">
            <span style='font-size: 1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #0A1F44;'>Chi tiết dữ liệu gốc (Raw Data)</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Cấu hình hiển thị bảng
        st.dataframe(
            df, 
            use_container_width=True,
            hide_index=True,
            height=400 # Cố định chiều cao để UX cuộn tốt hơn
        )
        
        # Nút xuất dữ liệu
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        csv = df.to_csv(index=False).encode('utf-8')
        
        # Đặt nút tải về vào cột nhỏ để kiểm soát độ rộng theo chuẩn UX
        dl_col, _ = st.columns([2, 8])
        with dl_col:
            st.download_button(
                label="Trích xuất CSV", 
                data=csv, 
                file_name='ees_race_2026_raw.csv', 
                mime='text/csv'
            )

except Exception as e:
    ibcs_message("Lỗi kết nối nghiêm trọng", f"Hệ thống từ chối truy cập hoặc không tìm thấy luồng dữ liệu.<br><br><b>Mã lỗi hệ thống:</b> <code>{str(e)}</code>", "error")
    
    ibcs_message("Sổ tay khắc phục (Troubleshooting)", """
    1. Kiểm tra tập tin <code>.streamlit/secrets.toml</code> có chứa đúng cấu trúc <code>[connections.gsheets]</code>.<br>
    2. Đảm bảo file Google Sheets đã được cấp quyền <em>"Bất kỳ ai có liên kết" (Anyone with the link)</em>.<br>
    3. Xác minh môi trường đã cài đặt package: <code>st-gsheets-connection</code>.
    """, "info")

# Footer chuẩn báo cáo
st.markdown("""
<div style="margin-top: 50px; border-top: 1px solid #EAEAEA; padding-top: 15px; display: flex; justify-content: space-between; font-size: 0.75rem; color: #888888;">
    <div><strong>BẢO MẬT:</strong> Tài liệu lưu hành nội bộ - Nghiêm cấm sao chép hoặc chia sẻ dưới mọi hình thức.</div>
    <div style="text-align: right;">GHN EES 2026 Analytics Dashboard • Phiên bản 1.2</div>
</div>
""", unsafe_allow_html=True)