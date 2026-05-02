# GHN Employee Engagement Survey (EES) 2026 - Progress Dashboard

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-red.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)
![Plotly](https://img.shields.io/badge/Plotly-5.18+-blueviolet.svg)

A real-time, interactive **Streamlit dashboard** designed to track the participation progress of the **GiaoHangNhanh (GHN) Employee Engagement Survey 2026**.

## 📊 Overview

The EES 2026 Dashboard provides HR and Leadership teams with a comprehensive view of survey completion rates across all operational groups and geographical regions. It seamlessly integrates with Google Sheets to fetch raw workforce data and live survey responses, processing them instantly to deliver actionable insights.

### Key Features

*   **Real-time Synchronization:** Directly connects to Google Sheets via `st-gsheets-connection` for live response tracking.
*   **Comprehensive Filtering:** Multi-level dynamic filtering by Survey Group, Division, Department, Section, and Date Range.
*   **Dynamic Visualizations:** Interactive Plotly charts including daily trendlines, cumulative completion curves, and department-level distribution metrics.
*   **Bilingual Support:** Fully localized in Vietnamese (VI) and English (EN) with instant toggle.
*   **Active Workforce Filtering:** Automatically isolates active employees (`status = 1`) to ensure Headcount (HC) accuracy.
*   **Robust State Management:** Custom session state callbacks ensure perfect widget persistence during aggressive UI reruns.

## 🎯 Target Audience (Survey Groups)

The dashboard tracks the following employee cohorts:
*   **1A**: Nhóm NV Giao nhận (NVPTTT & NVGN) / Delivery Staff
*   **1B**: Nhóm Tài xế Vận tải (GXT & TXXT) / Truck Drivers
*   **2A**: Nhóm Nhân viên Vận hành Kho / Warehouse Operations Staff
*   **2B**: Nhóm Quản lý Tuyến đầu / Frontline Managers
*   **3A**: Nhóm Nhân viên Văn phòng HO / HO Office Staff
*   **3B**: Manager & Director HO / HO Manager & Director

## ⚙️ Architecture & Technical Stack

*   **Framework**: Streamlit (Frontend & Backend integration)
*   **Data Processing**: Pandas
*   **Data Visualization**: Plotly (Graph Objects, Subplots)
*   **Database Connector**: `streamlit-gsheets`
*   **Caching Strategy**: TTL-based `@st.cache_data` with aggressive clear triggers for manual reloads.

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LQP-CTER/EES-Tracking.git
   cd EES-Tracking
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Google Sheets Secrets:**
   Create a `.streamlit/secrets.toml` file and securely add your Google Service Account credentials:
   ```toml
   [connections.gsheets]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "..."
   client_email = "..."
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## 🔒 Security Notice

*   **Data Privacy**: All raw Excel and sensitive survey mapping files located in the `data/` and `doc/` directories are strictly ignored via `.gitignore` to prevent accidental exposure of confidential HR information.
*   **Internal Use Only**: This dashboard and its connected datasets are property of GiaoHangNhanh and are restricted to internal authorized personnel only.

---
*Developed by the GHN EX Team • Employee Experience Department*
