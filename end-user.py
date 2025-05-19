# my_dashboard_app_enhanced.py
import streamlit as st
import pandas as pd
# import sqlite3 # Không cần thiết khi đọc từ CSV đã xử lý
import os
import json
import matplotlib.pyplot as plt 
import seaborn as sns
import plotly.express as px 
from collections import Counter

# --- Cấu hình Trang Streamlit ---
st.set_page_config(
    page_title="Dashboard Phân Tích Việc Làm DA/BA",
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.example.com/help', 
        'Report a bug': "https://www.example.com/bug",
        'About': "# Dashboard Phân Tích Thị Trường Việc Làm DA/BA\nĐây là sản phẩm của Nhóm 6."
    }
)

# --- Tên file CSV chứa dữ liệu tổng hợp đã làm sạch ---
DATA_CSV_FILENAME = "data_cleaned.csv" # Đảm bảo tên file này đúng

# --- Hàm Tải Dữ Liệu từ CSV (có cache) ---
@st.cache_data 
def load_data_from_csv(csv_file_name):
    """Tải dữ liệu từ file CSV và thực hiện các chuyển đổi kiểu cơ bản."""
    try:
        df = pd.read_csv(csv_file_name)
        if not df.empty:
            if 'posted_datetime_str' in df.columns:
                df['posted_datetime'] = pd.to_datetime(df['posted_datetime_str'], errors='coerce')
                if df['posted_datetime'].notna().any():
                    df['posted_year_month'] = df['posted_datetime'].dt.to_period('M')
            
            numeric_cols = ['salary_min_vnd', 'salary_max_vnd', 'days_to_deadline', 
                            'experience_years_min_numeric', 'views_count']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            
            def parse_json_list_safe(json_string):
                if pd.isna(json_string) or not isinstance(json_string, str): return []
                try:
                    if json_string.strip() == '[]': return []
                    data = json.loads(json_string)
                    return data if isinstance(data, list) else []
                except json.JSONDecodeError: return []

            df['parsed_skills_or_tags'] = pd.Series([[] for _ in range(len(df))], dtype=object)
            if 'skills_list_json_vnw' in df.columns:
                mask_vnw_skills = df['source_website'] == 'VietnamWorks'
                df.loc[mask_vnw_skills, 'parsed_skills_or_tags'] = df.loc[mask_vnw_skills, 'skills_list_json_vnw'].apply(parse_json_list_safe)
            if 'job_tags_list_json_cv' in df.columns:
                mask_cv_tags = df['source_website'] == 'CareerViet'
                df.loc[mask_cv_tags & (df['parsed_skills_or_tags'].apply(len) == 0), 'parsed_skills_or_tags'] = \
                    df.loc[mask_cv_tags, 'job_tags_list_json_cv'].apply(parse_json_list_safe)
        return df, None 
    except FileNotFoundError:
        st.error(f"LỖI: File CSV '{csv_file_name}' không tìm thấy. Hãy đảm bảo file này tồn tại trong repository GitHub của bạn (thường là cùng cấp với file app này).")
        return pd.DataFrame(), f"LỖI: File CSV '{csv_file_name}' không tìm thấy."
    except Exception as e:
        st.error(f"Lỗi khi tải hoặc xử lý dữ liệu từ CSV '{csv_file_name}': {e}")
        return pd.DataFrame(), f"Lỗi khi tải hoặc xử lý dữ liệu từ CSV: {e}"

# --- Hàm tạo cột Job Role Group ---
def categorize_job_role_st(title):
    title_lower = str(title).lower()
    if any(kw in title_lower for kw in ['hr data analyst']): return 'HR Data Analyst'
    if any(kw in title_lower for kw in ['data analyst', 'phân tích dữ liệu', 'bi analyst', 'business intelligence analyst', 'insight analyst', 'data analytics', 'quantitative researcher']): return 'Data Analyst'
    if any(kw in title_lower for kw in ['business analyst', 'phân tích kinh doanh', 'phân tích nghiệp vụ', 'it ba', 'technical business analyst', 'system analyst', 'phân tích hệ thống', 'process analyst']): return 'Business Analyst'
    if any(kw in title_lower for kw in ['product owner']): return 'Product Owner'
    if any(kw in title_lower for kw in ['product manager']): return 'Product Manager'
    return 'Khác'

# --- CSS Tùy chỉnh ---
def load_custom_css():
    st.markdown("""
    <style>
        @keyframes rainbowText {
            0% { color: #ff0000; } 14% { color: #ff7f00; } 28% { color: #ffff00; }
            42% { color: #00ff00; } 57% { color: #0000ff; } 71% { color: #4b0082; }
            85% { color: #8b00ff; } 100% { color: #ff0000; }
        }
        /* Tiêu đề chính của ứng dụng (st.title) */
        /* Để font Arial Black có hiệu lực tốt nhất, nó cần được cài đặt trên hệ thống người dùng 
           hoặc bạn có thể nhúng font web nếu muốn đảm bảo tính nhất quán tuyệt đối.
           Một số font đậm khác bạn có thể thử (cần import nếu là webfont): 
           'Impact', 'Bungee', 'Anton', 'Passion One' 
        */
        div[data-testid="stAppViewContainer"] > .main > div > div > div > h1 {
            text-align: center; 
            font-family: 'Arial Black', Gadget, sans-serif; /* Giữ Arial Black hoặc thử font khác */
            font-size: 2.8em; 
            animation: rainbowText 8s infinite linear; 
            background: linear-gradient(to right, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8b00ff, #ff0000);
            -webkit-background-clip: text; background-clip: text; color: transparent;
            padding-bottom: 10px; 
            margin-bottom: 20px; 
        }
        /* Tiêu đề các phần (st.header - h2) */
        h2 { 
            color: #2980b9 !important; 
            border-bottom: 2px solid #2980b9;
            padding-bottom: 5px; margin-top: 40px; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        }
        /* Tiêu đề nhỏ hơn (st.subheader - h3) */
        h3 { 
            color: #34495e !important; 
            margin-top: 30px; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        div[data-testid="stSidebar"] > div:first-child { 
            background-color: #f8f9fa; 
        }
        .stButton>button { 
            border-radius: 25px; border: 2px solid #3498db; color: #3498db;
            font-weight: bold; padding: 8px 18px; transition: all 0.3s ease-in-out; 
        }
        .stButton>button:hover { 
            background-color: #3498db; color: white; border-color: #2980b9;
            transform: scale(1.05); 
        }
        .stMetric { 
            background-color: #ffffff; border-left: 7px solid #1abc9c; 
            padding: 20px; border-radius: 10px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.12); 
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; 
        }
        .stMetric:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }
        div[data-testid="stMetric"] label { 
            color: #555555 !important; font-weight: 500;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { 
            color: #2c3e50 !important; font-size: 2em !important; font-weight: bold;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricDelta"] { 
            color: #7f8c8d !important; 
        }
        .stDataFrame { border-radius: 8px; overflow: hidden; }
        div[data-testid="stTabs"] button[role="tab"] {
            font-weight: 500; border-radius: 8px 8px 0 0; margin-right: 4px;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background-color: #e0e0e0; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- Tải dữ liệu ---
df_master, error_message = load_data_from_csv(DATA_CSV_FILENAME) 

# --- Xây dựng Giao diện Streamlit ---
load_custom_css() 

st.title("🚀 Dashboard Phân Tích Thị Trường Việc Làm DA/BA")
st.markdown("Khám phá các xu hướng tuyển dụng mới nhất cho ngành Phân tích Dữ liệu và Phân tích Kinh doanh tại Việt Nam.")
st.markdown("---")

if error_message: 
    st.error(error_message)
elif df_master.empty:
    st.warning("Hiện không có dữ liệu để hiển thị. Vui lòng kiểm tra lại file CSV hoặc chạy script thu thập/xử lý dữ liệu.")
else:
    if 'job_title' in df_master.columns and 'job_role_group' not in df_master.columns:
        df_master['job_role_group'] = df_master['job_title'].apply(categorize_job_role_st)

    # --- Sidebar cho Bộ lọc ---
    st.sidebar.image("https://i.ibb.co/3ySXFK2M/496510428-2054206478392683-5625031274161836120-n.jpg", caption="Data Analytics", use_container_width=True) 
    st.sidebar.header("Bộ lọc Dữ liệu 🛠️")
    source_options = ["Tất cả"] + sorted(df_master['source_website'].unique().tolist()) if 'source_website' in df_master.columns else ["Tất cả"]
    selected_source = st.sidebar.selectbox("Nguồn Website:", source_options, help="Chọn nguồn dữ liệu bạn muốn xem.")
    location_options = ["Tất cả"] + sorted(df_master['location_primary'].dropna().unique().tolist()) if 'location_primary' in df_master.columns else ["Tất cả"]
    selected_location = st.sidebar.selectbox("Địa điểm:", location_options, help="Lọc theo thành phố/khu vực chính.")
    selected_role = "Tất cả"
    if 'job_role_group' in df_master.columns:
        role_options = ["Tất cả"] + sorted(df_master['job_role_group'].dropna().unique().tolist())
        selected_role = st.sidebar.selectbox("Vai trò chính:", role_options, help="Lọc theo nhóm vai trò công việc.")
    min_exp_data, max_exp_data = 0, 20 
    if 'experience_years_min_numeric' in df_master.columns and df_master['experience_years_min_numeric'].notna().any():
        min_exp_data_val = df_master['experience_years_min_numeric'].min(skipna=True); max_exp_data_val = df_master['experience_years_min_numeric'].max(skipna=True)
        if pd.notna(min_exp_data_val): min_exp_data = int(min_exp_data_val)
        if pd.notna(max_exp_data_val): max_exp_data = int(max_exp_data_val)
        if max_exp_data < min_exp_data : max_exp_data = min_exp_data 
    selected_exp_range = st.sidebar.slider("Số năm kinh nghiệm tối thiểu:", min_exp_data, max_exp_data, (min_exp_data, max_exp_data))
    
    # Checkbox để hiển thị toàn bộ dữ liệu
    show_all_data_checkbox = st.sidebar.checkbox("Hiển thị toàn bộ dữ liệu (sau lọc)", value=False, key="show_all_data")

    # Áp dụng bộ lọc
    df_filtered = df_master.copy()
    if selected_source != "Tất cả" and 'source_website' in df_filtered.columns: df_filtered = df_filtered[df_filtered['source_website'] == selected_source]
    if selected_location != "Tất cả" and 'location_primary' in df_filtered.columns: df_filtered = df_filtered[df_filtered['location_primary'] == selected_location]
    if 'job_role_group' in df_filtered.columns and selected_role != "Tất cả": df_filtered = df_filtered[df_filtered['job_role_group'] == selected_role]
    if 'experience_years_min_numeric' in df_filtered.columns and not df_filtered.empty: 
        df_filtered = df_filtered[(df_filtered['experience_years_min_numeric'] >= selected_exp_range[0]) & (df_filtered['experience_years_min_numeric'] <= selected_exp_range[1])]
    
    # --- Hiển thị Thông tin Tổng quan ---
    st.header("📈 Tổng Quan Dữ Liệu (Sau lọc)") 
    if not df_filtered.empty:
        total_jobs_filtered = len(df_filtered)
        latest_update_time = "Không rõ"
        if 'process_timestamp' in df_filtered.columns and df_filtered['process_timestamp'].notna().any():
            try: latest_update_time = pd.to_datetime(df_filtered['process_timestamp'].max()).strftime('%H:%M:%S %d/%m/%Y')
            except: pass
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric(label="Tổng số Tin Tuyển Dụng", value=f"{total_jobs_filtered:,}")
        avg_exp_val = df_filtered['experience_years_min_numeric'].median() if 'experience_years_min_numeric' in df_filtered.columns and df_filtered['experience_years_min_numeric'].notna().any() else "N/A"
        kpi_col2.metric(label="Kinh nghiệm TB (Median)", value=f"{avg_exp_val} năm" if avg_exp_val != "N/A" else "N/A")
        kpi_col3.metric(label="Dữ liệu cập nhật lúc", value=latest_update_time)
        
        if show_all_data_checkbox: # SỬA Ở ĐÂY
            st.subheader("🔍 Toàn bộ dữ liệu (sau lọc)")
            st.dataframe(df_filtered.reset_index(drop=True)) # Hiển thị toàn bộ df_filtered
        elif st.sidebar.checkbox("Hiển thị dữ liệu mẫu (10 dòng đầu)", value=False, key="show_sample_data_default"): # Giữ lại lựa chọn cũ nếu muốn
             st.subheader("🔍 Dữ liệu mẫu (10 dòng đầu)")
             st.dataframe(df_filtered.head(10).reset_index(drop=True))
    else: st.warning("⚠️ Không có dữ liệu nào khớp với bộ lọc của bạn.")
    st.markdown("---")

    # --- Các Tab Phân Tích ---
    if not df_filtered.empty:
        st.header("💡 Insights Chi Tiết") 
        tab1, tab2, tab3, tab4 = st.tabs(["🌍 Địa Điểm & Vai Trò", "🛠️ Kinh Nghiệm & Kỹ Năng", "💰 Lương & Phúc Lợi", "📅 Xu Hướng Thời Gian"])
        
        with tab1:
            # ... (Nội dung tab 1 giữ nguyên)
            col_loc, col_role = st.columns(2)
            with col_loc:
                if 'location_primary' in df_filtered.columns:
                    location_counts_f = df_filtered['location_primary'].value_counts().head(7)
                    if not location_counts_f.empty:
                        fig_loc = px.bar(location_counts_f, x=location_counts_f.index, y=location_counts_f.values, labels={'x':'Địa điểm', 'y':'Số lượng tin'}, title="<b>Top 7 Địa điểm Tuyển dụng</b>", color=location_counts_f.index, color_discrete_sequence=px.colors.qualitative.Pastel1)
                        fig_loc.update_layout(xaxis_tickangle=-45, title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_loc, use_container_width=True)
            with col_role:
                if 'job_role_group' in df_filtered.columns:
                    role_counts_f = df_filtered['job_role_group'].value_counts()
                    if not role_counts_f.empty:
                        fig_role = px.pie(role_counts_f, values=role_counts_f.values, names=role_counts_f.index, title="<b>Tỷ lệ theo Vai trò chính</b>", hole=.4, color_discrete_sequence=px.colors.sequential.Agsunset)
                        fig_role.update_traces(textposition='inside', textinfo='percent+label'); fig_role.update_layout(title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_role, use_container_width=True)
        with tab2:
            # ... (Nội dung tab 2 giữ nguyên)
            col_exp_skill1, col_exp_skill2 = st.columns(2)
            with col_exp_skill1:
                if 'experience_years_min_numeric' in df_filtered.columns:
                    if 'experience_group' not in df_filtered.columns or df_filtered['experience_group'].isnull().all() :
                        def group_experience_st(years):
                            if pd.isna(years): return "Không rõ"; 
                            if years == 0: return "0 (Fresher)"; 
                            if 1 <= years <= 2: return "1-2 năm"; 
                            if 3 <= years <= 5: return "3-5 năm"; 
                            if years > 5: return ">5 năm"; return "Khác"
                        df_filtered.loc[:, 'experience_group'] = df_filtered['experience_years_min_numeric'].apply(group_experience_st)
                    if 'experience_group' in df_filtered.columns:
                        exp_group_counts_f = df_filtered['experience_group'].value_counts()
                        if not exp_group_counts_f.empty:
                            fig_exp = px.bar(exp_group_counts_f, x=exp_group_counts_f.index, y=exp_group_counts_f.values, labels={'x':'Nhóm kinh nghiệm', 'y':'Số lượng tin'}, title="<b>Số tin theo Nhóm Kinh nghiệm</b>", color=exp_group_counts_f.index, color_discrete_sequence=px.colors.qualitative.Safe)
                            fig_exp.update_layout(title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_exp, use_container_width=True)
            with col_exp_skill2:
                if 'parsed_skills_or_tags' in df_filtered.columns:
                    st.markdown("**Top 10 Kỹ năng/Tags phổ biến**", unsafe_allow_html=True)
                    all_skills_tags_list_f = []; df_filtered['parsed_skills_or_tags'].dropna().apply(lambda skills_list: all_skills_tags_list_f.extend([skill.lower().strip() for skill in skills_list if skill.strip()]))
                    if all_skills_tags_list_f:
                        skill_tag_counts_f = pd.Series(all_skills_tags_list_f).value_counts().head(10)
                        fig_skill = px.bar(skill_tag_counts_f, y=skill_tag_counts_f.index, x=skill_tag_counts_f.values, orientation='h', labels={'y':'Kỹ năng/Tag', 'x':'Số lần xuất hiện'}, title="<b>Top 10 Kỹ năng/Tags</b>", color=skill_tag_counts_f.values, color_continuous_scale=px.colors.sequential.Tealgrn)
                        fig_skill.update_layout(yaxis={'categoryorder':'total ascending'}, title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_skill, use_container_width=True)
                    else: st.write("Không có dữ liệu kỹ năng/tags.")
        with tab3:
            # ... (Nội dung tab 3 giữ nguyên)
            if 'salary_min_vnd' in df_filtered.columns and 'salary_negotiable' in df_filtered.columns:
                df_salary_plot_f = df_filtered[(df_filtered['salary_negotiable'] == False) & (df_filtered['salary_min_vnd'].notna())].copy()
                if not df_salary_plot_f.empty:
                    st.write(f"Phân tích trên {len(df_salary_plot_f)} tin có mức lương cụ thể:")
                    if 'salary_avg_vnd' not in df_salary_plot_f.columns: 
                        df_salary_plot_f['salary_avg_vnd'] = df_salary_plot_f[['salary_min_vnd', 'salary_max_vnd']].mean(axis=1)
                        min_only_mask = df_salary_plot_f['salary_avg_vnd'].isna() & df_salary_plot_f['salary_min_vnd'].notna(); df_salary_plot_f.loc[min_only_mask, 'salary_avg_vnd'] = df_salary_plot_f.loc[min_only_mask, 'salary_min_vnd']
                        max_only_mask = df_salary_plot_f['salary_avg_vnd'].isna() & df_salary_plot_f['salary_max_vnd'].notna(); df_salary_plot_f.loc[max_only_mask, 'salary_avg_vnd'] = df_salary_plot_f.loc[max_only_mask, 'salary_max_vnd']
                        df_salary_plot_f.dropna(subset=['salary_avg_vnd'], inplace=True)
                    if not df_salary_plot_f.empty:
                        fig_salary = px.histogram(df_salary_plot_f, x="salary_min_vnd", nbins=15, title="<b>Phân bổ Lương Tối thiểu (VND/tháng)</b>", labels={'salary_min_vnd':'Lương tối thiểu (VND)'}, opacity=0.8, color_discrete_sequence=['#2ecc71'])
                        fig_salary.update_layout(bargap=0.1, title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_salary, use_container_width=True)
                        if 'job_role_group' in df_salary_plot_f.columns:
                            st.write("**Lương tối thiểu trung vị theo Vai trò:**"); st.dataframe(df_salary_plot_f.groupby('job_role_group')['salary_min_vnd'].median().apply(lambda x: f"{x/1000000:,.1f} Tr" if pd.notna(x) else "N/A").sort_values(ascending=False).reset_index().rename(columns={'job_role_group':'Vai trò', 'salary_min_vnd':'Lương trung vị (Min)'}))
                    else: st.write("Không có đủ dữ liệu lương cụ thể (sau khi tính avg) để vẽ biểu đồ.")
                else: st.write("Không có đủ dữ liệu lương cụ thể để vẽ biểu đồ.")
            if 'benefits_text' in df_filtered.columns:
                st.write("**Phúc lợi thường gặp (Top 10)**")
                try:
                    all_benefits = []; df_filtered['benefits_text'].dropna().astype(str).apply(lambda x: all_benefits.extend([b.strip().lower() for b in x.split(';') if b.strip() and b.lower() != 'không có thông tin']))
                    if all_benefits:
                        benefit_counts_f = pd.Series(all_benefits).value_counts().head(10)
                        fig_benefits = px.bar(benefit_counts_f, x=benefit_counts_f.index, y=benefit_counts_f.values, labels={'x':'Phúc lợi', 'y':'Số lần đề cập'}, title="<b>Top 10 Phúc lợi</b>", color=benefit_counts_f.values, color_continuous_scale=px.colors.sequential.Magenta)
                        fig_benefits.update_layout(xaxis_tickangle=-45, title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_benefits, use_container_width=True)
                    else: st.write("Không có dữ liệu phúc lợi.")
                except Exception as e_ben: st.write(f"Lỗi khi phân tích phúc lợi: {e_ben}")
        with tab4:
            # ... (Nội dung tab 4 giữ nguyên)
            if 'posted_year_month' in df_filtered.columns:
                df_filtered_for_trend = df_filtered.copy() 
                df_filtered_for_trend.loc[:, 'posted_year_month_dt'] = df_filtered_for_trend['posted_year_month'].apply(lambda x: x.to_timestamp() if pd.notna(x) else pd.NaT)
                monthly_counts_f = df_filtered_for_trend.dropna(subset=['posted_year_month_dt']).set_index('posted_year_month_dt').resample('M')['url'].count().sort_index()
                if not monthly_counts_f.empty:
                    fig_trend = px.line(monthly_counts_f, x=monthly_counts_f.index, y=monthly_counts_f.values, markers=True, labels={'x':'Tháng/Năm đăng tin', 'y':'Số lượng tin'}, title='<b>Xu hướng số lượng tin đăng theo Tháng</b>')
                    fig_trend.update_layout(xaxis_tickangle=-45, title_x=0.5, font=dict(family="Arial, sans-serif")); st.plotly_chart(fig_trend, use_container_width=True)
                else: st.write("Không đủ dữ liệu ngày tháng để vẽ biểu đồ xu hướng.")
            else: st.write("Thiếu cột 'posted_year_month' để phân tích xu hướng.")

    # --- Thông báo cuối trang ---
    st.markdown("---"); st.markdown("Dự án được thực hiện bởi Nhóm 6") 
    st.markdown(f"Dữ liệu được tổng hợp từ VietnamWorks và CareerViet, xử lý lần cuối vào: {latest_update_time if 'latest_update_time' in locals() and latest_update_time != 'Không rõ' else 'Chưa có thông tin'}")

