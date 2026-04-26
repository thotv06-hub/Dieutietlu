import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d, PchipInterpolator
import streamlit.components.v1 as components
import io

# ==========================================
# CẤU HÌNH TRANG & NHÚNG CSS GIAO DIỆN CHUNG
# ==========================================
st.set_page_config(page_title="Điều Tiết Lũ Hồ Chứa", page_icon="🌊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .main-header {
        font-size: 2.2rem;
        color: #0F4C81;
        font-weight: 800;
        text-align: center;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .input-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 0rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.4);
    }
    
    .btn-anim > button {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
        margin-top: 15px;
    }
    .btn-anim > button:hover {
        box-shadow: 0 6px 12px rgba(16, 185, 129, 0.4);
    }
    
    .esc-btn > button {
        background: #EF4444 !important;
        color: white !important;
        font-weight: bold;
        box-shadow: none !important;
        float: right;
        margin-bottom: 10px;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 5px 5px 0px 0px;
        padding: 10px 20px;
        background-color: #F1F5F9;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #E0F2FE;
        color: #0369A1;
        border-bottom: 3px solid #0284C7;
    }
    </style>
""", unsafe_allow_html=True)

# Khởi tạo Session State
if 'animating' not in st.session_state:
    st.session_state['animating'] = False
if 'calculated' not in st.session_state:
    st.session_state['calculated'] = False

# ==========================================
# XÁC THỰC MẬT KHẨU (THÊM MỚI, GIỮ NGUYÊN MỌI CODE KHÁC)
# ==========================================
def check_password():
    """Kiểm tra mật khẩu truy cập"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("<div class='main-header'>🔐 XÁC THỰC TRUY CẬP</div>", unsafe_allow_html=True)
        with st.form("login_form"):
            password = st.text_input("Nhập mật khẩu:", type="password")
            submitted = st.form_submit_button("Đăng nhập")
            if submitted:
                if password == "429751":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Mật khẩu không chính xác!")
        st.stop()

check_password()   # <--- Gọi kiểm tra, nếu chưa đăng nhập sẽ dừng tại đây

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🎛️ BẢNG ĐIỀU KHIỂN</h2>", unsafe_allow_html=True)
    st.markdown("---")
    loai_tran = st.radio("Loại đập tràn:", ["Có cửa van", "Tràn tự do (Không cửa van)"])
    st.markdown("---")
    
    st.markdown("### ⚙️ 1. THÔNG SỐ CÔNG TRÌNH")
    Z_nguong = st.number_input("Cao trình ngưỡng tràn (m)", value=552.70, step=0.1, format="%.2f")
    B_tran = st.number_input("Tổng bề rộng tràn B (m)", value=8.00, step=1.0, format="%.2f")
    m_heso = st.number_input("Hệ số lưu lượng m", value=0.399, step=0.001, format="%.3f")
    epsilon = st.number_input("Hệ số co hẹp epsilon (ε)", value=1.00, step=0.01, format="%.2f")
    sigma_n = st.number_input("Hệ số chảy ngập (σn)", value=1.00, step=0.01, format="%.2f")
    
    # Ẩn hiện thông minh
    if loai_tran == "Có cửa van":
        a_max = st.number_input("Chiều cao cửa van a_max (m)", value=4.00, step=0.1, format="%.2f")
    else:
        a_max = 0.0 
        
    st.markdown("### ⏱️ 2. THÔNG SỐ VẬN HÀNH")
    Z_mndbt = st.number_input("Mực nước dâng bình thường (MNDBT)", value=556.70, step=0.1, format="%.2f")
    Z_bd = st.number_input("Mực nước hồ bắt đầu đón lũ (m)", value=556.70, step=0.1, format="%.2f")
    dt_phut = st.number_input("Thời đoạn tính toán dt (phút)", value=30, step=10)
    dt_sec = dt_phut * 60

# DỮ LIỆU MẪU
sample_zv = pd.DataFrame({
    "Z (m)": [540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560],
    "F (ha)": [0, 0, 7.412, 13.998, 19.626, 25.554, 29.034, 33.182, 37.184, 40.839, 47.087, 51.064, 54.045, 58.004, 62.837, 66.6, 70.017, 77.201, 84.353, 90.268, 97.286],
    "V (10^6 m3)": [0, 0, 0.03706, 0.14411, 0.31223, 0.53813, 0.81107, 1.12215, 1.47398, 1.8641, 2.30373, 2.79448, 3.32002, 3.88027, 4.48447, 5.13165, 5.81474, 6.55083, 7.3586, 8.2317, 9.16948]
})
sample_qin = pd.DataFrame({
    "Time (h)": [0.00, 0.50, 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 5.00, 5.50, 6.00, 6.50, 7.00, 7.50, 8.00, 8.50, 9.00, 9.50, 10.00, 10.50, 11.00, 11.50, 12.00, 12.50, 13.00],
    "Qin (m3/s)": [0, 47.0523, 94.1045, 130.077, 188.209, 235.261, 282.314, 258.787, 235.261, 211.735, 188.209, 164.683, 141.157, 117.631, 94.1045, 70.5784, 47.0523, 23.5261, 23.4301, 23.046, 22.6619, 22.2778, 21.1255, 19.205, 15.364, 9.6025, 0]
})

def clean_data(df):
    df_clean = df.copy()
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].astype(str).str.replace(',', '.').str.strip()
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    return df_clean.dropna()

def thieu_luu_luong_tran(Z, Z_nguong, B, m, eps, sigma_n):
    g = 9.81
    if Z <= Z_nguong: return 0.0
    return sigma_n * eps * m * B * np.sqrt(2 * g) * ((Z - Z_nguong) ** 1.5)

def tinh_toan_puls(df_qin, df_zv, Z_bd, Z_mndbt, dt_sec, loai_tran, a_max):
    df_qin = clean_data(df_qin)
    df_zv = clean_data(df_zv)
    Z_arr = df_zv['Z (m)'].to_numpy(dtype=float)
    V_arr = df_zv['V (10^6 m3)'].to_numpy(dtype=float)
    T = df_qin['Time (h)'].to_numpy(dtype=float)
    Qin = df_qin['Qin (m3/s)'].to_numpy(dtype=float)
    
    V_func = interp1d(Z_arr, V_arr, fill_value="extrapolate")
    V_bd = float(V_func(Z_bd))
    V_mndbt = float(V_func(Z_mndbt)) 
    
    Z_max_bang1 = max(Z_bd, Z_mndbt) + 6.0
    Z_start = min(Z_bd, Z_mndbt)
    Z_gt_arr = np.round(np.arange(Z_start, Z_max_bang1 + 0.1, 0.2), 2)
    
    bang1_data = []
    for i, z in enumerate(Z_gt_arr):
        H_tr = z - Z_nguong
        q_xa = thieu_luu_luong_tran(z, Z_nguong, B_tran, m_heso, epsilon, sigma_n)
        V_ho = float(V_func(z))
        V_pl = max(0.0, V_ho - V_mndbt) 
        f1 = (V_pl * 1e6) / dt_sec - q_xa / 2.0
        f2 = (V_pl * 1e6) / dt_sec + q_xa / 2.0
        bang1_data.append([i+1, z, H_tr, q_xa, V_ho, V_pl, f1, f2])
        
    df_bang1 = pd.DataFrame(bang1_data, columns=["TT", "Zgt (m)", "Htr (m)", "q_xa (m³/s)", "V_ho (10⁶m³)", "V_pl (10⁶m³)", "f1 (m³/s)", "f2 (m³/s)"])
    
    f2_arr = df_bang1["f2 (m³/s)"].to_numpy(dtype=float)
    qxa_arr = df_bang1["q_xa (m³/s)"].to_numpy(dtype=float)
    z_arr = df_bang1["Zgt (m)"].to_numpy(dtype=float)
    vho_arr = df_bang1["V_ho (10⁶m³)"].to_numpy(dtype=float)
    vpl_arr = df_bang1["V_pl (10⁶m³)"].to_numpy(dtype=float)
    f2_min = f2_arr[0]
    
    n = len(T)
    bang2_data = []
    if loai_tran == "Có cửa van":
        q_dau_0 = Qin[0] 
    else:
        q_dau_0 = thieu_luu_luong_tran(Z_bd, Z_nguong, B_tran, m_heso, epsilon, sigma_n)
        
    bang2_data.append([T[0], Qin[0], np.nan, 0.0, np.nan, np.nan, q_dau_0, Z_bd - Z_nguong, Z_bd, V_bd, max(0.0, V_bd - V_mndbt)])
    
    for i in range(n - 1):
        Qtb = (Qin[i] + Qin[i+1]) / 2.0
        q_dau = bang2_data[-1][6]
        Vsc_prev = bang2_data[-1][10]
        f1 = (Vsc_prev * 1e6) / dt_sec - q_dau / 2.0
        f2 = f1 + Qtb
        
        if loai_tran == "Có cửa van" and f2 <= f2_min:
            q_cuoi = Qin[i+1] 
            Zsc = Z_bd
            Vho = V_bd
            Vsc = 0.0
            Htr = Z_bd - Z_nguong
            f1_disp, f2_disp = np.nan, np.nan
        else:
            f2_calc = max(f2, f2_min)
            q_cuoi = float(np.interp(f2_calc, f2_arr, qxa_arr))
            Zsc = float(np.interp(f2_calc, f2_arr, z_arr))
            Vho = float(np.interp(f2_calc, f2_arr, vho_arr))
            Vsc = float(np.interp(f2_calc, f2_arr, vpl_arr))
            Htr = Zsc - Z_nguong
            f1_disp, f2_disp = f1, f2
            
        bang2_data.append([T[i+1], Qin[i+1], Qtb, q_dau, f1_disp, f2_disp, q_cuoi, Htr, Zsc, Vho, Vsc])
        
    df_bang2 = pd.DataFrame(bang2_data, columns=["T (giờ)", "Q~T (m³/s)", "Qtb (m³/s)", "q_dau (m³/s)", "f1 (m³/s)", "f2 (m³/s)", "q_cuoi (m³/s)", "Htr (m)", "Zsc (m)", "V_ho (10⁶m³)", "Vsc (10⁶m³)"])
    
    df_qza = None
    if loai_tran == "Có cửa van":
        a_H_arr = np.array([0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75])
        alpha_arr = np.array([0.611, 0.613, 0.615, 0.618, 0.620, 0.622, 0.625, 0.628, 0.632, 0.638, 0.645, 0.650, 0.660, 0.672, 0.690, 0.705])
        g = 9.81
        a_van_list = []
        for index, row in df_bang2.iterrows():
            Z_hientai = row["Zsc (m)"]
            q_cuoi = row["q_cuoi (m³/s)"] 
            H = Z_hientai - Z_nguong
            if H <= 0 or q_cuoi <= 0:
                a_calc = 0.0
            else:
                Q_tudo = thieu_luu_luong_tran(Z_hientai, Z_nguong, B_tran, m_heso, epsilon, sigma_n)
                if q_cuoi >= Q_tudo * 0.990: 
                    a_calc = a_max
                else:
                    alpha_gt = 0.615
                    sai_so = 1.0
                    lan_lap = 0
                    while sai_so > 1e-4 and lan_lap < 30:
                        lan_lap += 1
                        a_calc = q_cuoi / (alpha_gt * epsilon * B_tran * np.sqrt(2 * g * H))
                        a_H = a_calc / H
                        if a_H > 0.75: alpha_tt = 0.705 
                        elif a_H < 0: alpha_tt = 0.611
                        else: alpha_tt = float(np.interp(a_H, a_H_arr, alpha_arr))
                        sai_so = abs(alpha_tt - alpha_gt)
                        alpha_gt = alpha_tt
                    if a_calc > a_max: a_calc = a_max
            a_van_list.append(a_calc)
        df_bang2["Độ mở e (m)"] = a_van_list
        
        Z_range = np.round(np.arange(Z_start, Z_max_bang1 + 0.2, 0.2), 2)
        a_steps = np.arange(0.5, a_max + 0.5, 0.5)
        qza_data = {"Z (m)": Z_range}
        q_tudo_list = []
        for z in Z_range:
            q_tudo_list.append(thieu_luu_luong_tran(z, Z_nguong, B_tran, m_heso, epsilon, sigma_n))
        qza_data["Tràn tự do (m³/s)"] = q_tudo_list
        
        for a_val in a_steps:
            q_col = []
            for z in Z_range:
                H = z - Z_nguong
                Q_tudo = thieu_luu_luong_tran(z, Z_nguong, B_tran, m_heso, epsilon, sigma_n)
                if H <= 0: q_col.append(0.0)
                elif H <= a_val: q_col.append(Q_tudo)
                else:
                    a_H = a_val / H
                    if a_H > 0.75: alpha_tt = 0.705 
                    elif a_H < 0: alpha_tt = 0.611
                    else: alpha_tt = float(np.interp(a_H, a_H_arr, alpha_arr))
                    Q_lo = alpha_tt * epsilon * B_tran * a_val * np.sqrt(2 * g * H)
                    Q_thuc_te = min(Q_lo, Q_tudo) 
                    q_col.append(Q_thuc_te)
            qza_data[f"e = {a_val}m"] = q_col
        df_qza = pd.DataFrame(qza_data)

    return df_bang1, df_bang2, df_qza

def tao_file_excel(df_b1, df_b2, df_qza, loai_tran):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    T_arr = df_b2["T (giờ)"].to_numpy(dtype=float)
    T_dense = np.linspace(T_arr.min(), T_arr.max(), 300)
    qin_dense = PchipInterpolator(T_arr, df_b2["Q~T (m³/s)"].to_numpy(dtype=float))(T_dense)
    qout_dense = PchipInterpolator(T_arr, df_b2["q_cuoi (m³/s)"].to_numpy(dtype=float))(T_dense)
    z_dense = PchipInterpolator(T_arr, df_b2["Zsc (m)"].to_numpy(dtype=float))(T_dense)
    chart_dict = {"T": T_dense, "Qin": qin_dense, "Qout": qout_dense, "Z": z_dense}
    if loai_tran == "Có cửa van":
        chart_dict["e"] = PchipInterpolator(T_arr, df_b2["Độ mở e (m)"].to_numpy(dtype=float))(T_dense) 
    df_chart_data = pd.DataFrame(chart_dict)
    
    df_b1.to_excel(writer, sheet_name='Bang_1_Phu_Tro', index=False, header=False, startrow=1)
    df_b2.to_excel(writer, sheet_name='Bang_2_Dieu_Tiet', index=False, header=False, startrow=1)
    if loai_tran == "Có cửa van": df_qza.to_excel(writer, sheet_name='Bang_3_Tra_Cuu_Van', index=False, header=False, startrow=1)
    df_chart_data.to_excel(writer, sheet_name='Data_Bieu_Do', index=False)
    
    workbook = writer.book
    ws1 = writer.sheets['Bang_1_Phu_Tro']
    ws2 = writer.sheets['Bang_2_Dieu_Tiet']
    ws_chart = writer.sheets['Data_Bieu_Do']
    ws_chart.hide() 
    
    header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9E1F2', 'text_wrap': True})
    data_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})
    
    for col_num, value in enumerate(df_b1.columns.values): ws1.write(0, col_num, value, header_format)
    for row in range(len(df_b1)):
        for col in range(len(df_b1.columns)): ws1.write(row + 1, col, df_b1.iloc[row, col], data_format)

    for col_num, value in enumerate(df_b2.columns.values): ws2.write(0, col_num, value, header_format)
    for row in range(len(df_b2)):
        for col in range(len(df_b2.columns)):
            val = df_b2.iloc[row, col]
            if pd.isna(val): ws2.write(row + 1, col, "", data_format)
            else: ws2.write(row + 1, col, val, data_format)
            
    ws1.set_column('A:H', 15)
    ws2.set_column('A:L', 14)
    
    chart1 = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
    max_row1 = len(df_b1)
    chart1.add_series({'name': 'Đường f1', 'categories': ['Bang_1_Phu_Tro', 1, 0, max_row1, 0], 'values': ['Bang_1_Phu_Tro', 1, 6, max_row1, 6], 'line': {'color': '#0070C0', 'width': 2.5}})
    chart1.add_series({'name': 'Đường f2', 'categories': ['Bang_1_Phu_Tro', 1, 0, max_row1, 0], 'values': ['Bang_1_Phu_Tro', 1, 7, max_row1, 7], 'line': {'color': '#FF0000', 'width': 2.5}})
    chart1.set_title({'name': 'BIỂU ĐỒ PHỤ TRỢ Z ~ f1, f2', 'name_font': {'size': 14, 'bold': True}})
    chart1.set_x_axis({'name': 'Số thứ tự (TT)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
    chart1.set_y_axis({'name': 'Lưu lượng f1, f2 (m³/s)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
    chart1.set_legend({'position': 'bottom'})
    chart1.set_size({'width': 800, 'height': 500})
    ws1.insert_chart('J2', chart1)
    
    chart2 = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'}) 
    chart2.add_series({'name': 'Lũ đến (Qin)', 'categories': ['Data_Bieu_Do', 1, 0, 300, 0], 'values': ['Data_Bieu_Do', 1, 1, 300, 1], 'line': {'color': '#FF0000', 'width': 2.5}})
    chart2.add_series({'name': 'Lũ xả (Qout)', 'categories': ['Data_Bieu_Do', 1, 0, 300, 0], 'values': ['Data_Bieu_Do', 1, 2, 300, 2], 'line': {'color': '#0070C0', 'width': 2.5}})
    chart2.set_title({'name': 'BIỂU ĐỒ QUÁ TRÌNH ĐIỀU TIẾT LŨ', 'name_font': {'size': 14, 'bold': True}})
    chart2.set_x_axis({'name': 'Thời gian (Giờ)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
    chart2.set_y_axis({'name': 'Lưu lượng (m³/s)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
    
    z_min = df_b2["Zsc (m)"].min()
    z_max = df_b2["Zsc (m)"].max()
    dz = z_max - z_min if z_max > z_min else 1.0
    chart2.add_series({'name': 'Mực nước (Z)', 'categories': ['Data_Bieu_Do', 1, 0, 300, 0], 'values': ['Data_Bieu_Do', 1, 3, 300, 3], 'y2_axis': True, 'line': {'color': '#00B050', 'dash_type': 'dash', 'width': 2.5}})
    chart2.set_y2_axis({'name': 'Mực nước hồ (m)', 'min': z_min - 0.2 * dz, 'max': z_max + 8.0 * dz, 'major_gridlines': {'visible': False}})
    chart2.set_legend({'position': 'bottom'})
    chart2.set_size({'width': 800, 'height': 450})
    ws2.insert_chart('N2', chart2)
    
    if loai_tran == "Có cửa van":
        ws3 = writer.sheets['Bang_3_Tra_Cuu_Van']
        for col_num, value in enumerate(df_qza.columns.values): ws3.write(0, col_num, value, header_format)
        for row in range(len(df_qza)):
            for col in range(len(df_qza.columns)): ws3.write(row + 1, col, df_qza.iloc[row, col], data_format)
        ws3.set_column('A:K', 14)
        
        chart3 = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        chart3.add_series({'name': 'Độ mở cửa van (e)', 'categories': ['Data_Bieu_Do', 1, 0, 300, 0], 'values': ['Data_Bieu_Do', 1, 4, 300, 4], 'line': {'color': '#8B4513', 'width': 2.5}})
        chart3.set_title({'name': 'BIỂU ĐỒ QUÁ TRÌNH ĐỘ MỞ CỬA VAN', 'name_font': {'size': 14, 'bold': True}})
        chart3.set_x_axis({'name': 'Thời gian (Giờ)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
        chart3.set_y_axis({'name': 'Độ mở e (m)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
        chart3.set_legend({'position': 'bottom'})
        chart3.set_size({'width': 800, 'height': 350})
        ws2.insert_chart('N26', chart3)

        chart4 = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        max_row_qza = len(df_qza)
        chart4.add_series({'name': 'Tràn tự do', 'categories': ['Bang_3_Tra_Cuu_Van', 1, 0, max_row_qza, 0], 'values': ['Bang_3_Tra_Cuu_Van', 1, 1, max_row_qza, 1], 'line': {'color': 'black', 'dash_type': 'dash', 'width': 2}})
        for col_idx in range(2, len(df_qza.columns)):
            col_name = df_qza.columns[col_idx]
            chart4.add_series({'name': col_name, 'categories': ['Bang_3_Tra_Cuu_Van', 1, 0, max_row_qza, 0], 'values': ['Bang_3_Tra_Cuu_Van', 1, col_idx, max_row_qza, col_idx], 'line': {'width': 1.5}})
        chart4.set_title({'name': 'QUAN HỆ GIỮA LƯU LƯỢNG VÀ MỰC NƯỚC HỒ THEO ĐỘ MỞ CỬA VAN', 'name_font': {'size': 14, 'bold': True}})
        chart4.set_x_axis({'name': 'Cao trình mực nước hồ Z (m)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
        chart4.set_y_axis({'name': 'Lưu lượng xả qua tràn Q (m³/s)', 'major_gridlines': {'visible': True, 'line': {'color': '#D9D9D9', 'dash_type': 'dash'}}})
        chart4.set_legend({'position': 'bottom'}) 
        chart4.set_size({'width': 800, 'height': 600})
        ws3.insert_chart('M2', chart4)
    
    writer.close()
    return output.getvalue()

# =========================================================
# VÙNG ANIMATION TOÀN MÀN HÌNH (GÓI GỌN 1 HÀNG + TẮT BẰNG ESC)
# =========================================================
if st.session_state['animating']:
    # CHỈ ép CSS ẩn bóng ma khi đang ở chế độ Animation
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none !important;}
        header[data-testid="stHeader"] {display: none !important;}
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 0rem !important; 
            margin: 0rem !important;
            max-width: 100% !important;
        }
        [data-stale="true"] {
            display: none !important;
            opacity: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    components.html("""
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function handleEsc(e) {
            if (e.key === 'Escape') {
                const btns = Array.from(doc.querySelectorAll('button'));
                const escBtn = btns.find(b => b.innerText.includes('THOÁT CHẠY (ESC)'));
                if (escBtn) escBtn.click();
                doc.removeEventListener('keydown', handleEsc);
            }
        });
        </script>
    """, height=0)
    
    st.markdown("<div class='esc-btn'>", unsafe_allow_html=True)
    if st.button("❌ THOÁT CHẠY (ESC)"):
        st.session_state['animating'] = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center; color: #1E3A8A; margin-top: -30px;'>🎬 ĐANG PHÁT DIỄN BIẾN ĐIỀU TIẾT LŨ...</h2>", unsafe_allow_html=True)
    anim_placeholder = st.empty()
    
    try:
        res = st.session_state['calc_results']
        df_b1 = res['df_b1']
        df_b2 = res['df_b2']
        loai_tran_cache = res['loai_tran_cache']
        a_max_cache = res['a_max_cache']
        
        STT_arr1 = df_b1["TT"].to_numpy()
        STT_smooth1 = np.linspace(STT_arr1.min(), STT_arr1.max(), 300)
        f1_smooth = PchipInterpolator(STT_arr1, df_b1["f1 (m³/s)"].to_numpy())(STT_smooth1)
        f2_smooth = PchipInterpolator(STT_arr1, df_b1["f2 (m³/s)"].to_numpy())(STT_smooth1)
        
        T_arr = df_b2["T (giờ)"].to_numpy()
        T_smooth2 = np.linspace(T_arr.min(), T_arr.max(), 300)
        qin_smooth = PchipInterpolator(T_arr, df_b2["Q~T (m³/s)"].to_numpy())(T_smooth2)
        qout_smooth = PchipInterpolator(T_arr, df_b2["q_cuoi (m³/s)"].to_numpy())(T_smooth2)
        zsc_smooth = PchipInterpolator(T_arr, df_b2["Zsc (m)"].to_numpy())(T_smooth2)
        
        if loai_tran_cache == "Có cửa van":
            e_smooth = PchipInterpolator(T_arr, df_b2["Độ mở e (m)"].to_numpy())(T_smooth2)
            
        x1_min, x1_max = STT_smooth1.min(), STT_smooth1.max()
        y1_max = max(f1_smooth.max(), f2_smooth.max()) * 1.1
        x2_min, x2_max = T_smooth2.min(), T_smooth2.max()
        y2_max = max(qin_smooth.max(), qout_smooth.max()) * 1.1
        z_min, z_max = df_b2["Zsc (m)"].min(), df_b2["Zsc (m)"].max()
        dz = z_max - z_min if z_max > z_min else 1.0
        
        frames = 40 
        for step in range(1, frames + 1):
            if not st.session_state['animating']: break 
            
            idx = int((step / frames) * 300)
            if idx == 0: idx = 1
            
            if loai_tran_cache == "Có cửa van":
                fig, (ax1, ax2, ax_a) = plt.subplots(1, 3, figsize=(18, 4.2))
            else:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.2))

            ax1.plot(STT_smooth1[:idx], f1_smooth[:idx], color='#0070C0', label='Đường f1', linewidth=2.5)
            ax1.plot(STT_smooth1[:idx], f2_smooth[:idx], color='#FF0000', label='Đường f2', linewidth=2.5)
            ax1.set_title('BIỂU ĐỒ PHỤ TRỢ Z ~ f1, f2', fontsize=12, fontweight='bold', color='#0F4C81')
            ax1.set_xlabel('Số thứ tự (TT)', fontweight='bold')
            ax1.set_ylabel('Lưu lượng f1, f2 (m³/s)', fontweight='bold')
            ax1.set_xlim(x1_min, x1_max)
            ax1.set_ylim(0, y1_max) 
            ax1.legend(loc='lower right', frameon=True, shadow=True)
            ax1.grid(True, linestyle='--', alpha=0.7)
            
            ax2.plot(T_smooth2[:idx], qin_smooth[:idx], color='#FF0000', label='Lũ đến (Qin)', linewidth=2.5)
            ax2.plot(T_smooth2[:idx], qout_smooth[:idx], color='#0070C0', label='Lũ xả (Qout)', linewidth=2.5)
            ax2.set_title('BIỂU ĐỒ QUÁ TRÌNH ĐIỀU TIẾT LŨ', fontsize=12, fontweight='bold', color='#0F4C81')
            ax2.set_xlabel('Thời gian (Giờ)', fontweight='bold')
            ax2.set_ylabel('Lưu lượng (m³/s)', fontweight='bold')
            ax2.set_xlim(x2_min, x2_max) 
            ax2.set_ylim(0, y2_max)     
            ax2.grid(True, linestyle='--', alpha=0.7)
            
            ax3 = ax2.twinx()
            ax3.set_ylim(z_min - 0.2 * dz, z_max + 8.0 * dz) 
            ax3.plot(T_smooth2[:idx], zsc_smooth[:idx], color='#00B050', linestyle='--', label='Mực nước (Z)', linewidth=2.5)
            ax3.set_ylabel('Mực nước hồ (m)', color='#00B050', fontweight='bold')
            lines, labels = ax2.get_legend_handles_labels()
            lines2, labels2 = ax3.get_legend_handles_labels()
            ax2.legend(lines + lines2, labels + labels2, loc='upper right', frameon=True, shadow=True, handlelength=3)
            
            if loai_tran_cache == "Có cửa van":
                ax_a.plot(T_smooth2[:idx], e_smooth[:idx], color='#8B4513', linewidth=2.5, label='Độ mở van (e)')
                ax_a.set_title('BIỂU ĐỒ QUÁ TRÌNH ĐỘ MỞ CỬA VAN', fontsize=12, fontweight='bold', color='#0F4C81')
                ax_a.set_xlabel('Thời gian (Giờ)', fontweight='bold')
                ax_a.set_ylabel('Độ mở e (m)', fontweight='bold')
                ax_a.set_xlim(x2_min, x2_max) 
                ax_a.set_ylim(0, a_max_cache + 0.5) 
                ax_a.grid(True, linestyle='--', alpha=0.7)
                ax_a.legend(loc='upper right', frameon=True, shadow=True)
                
            fig.tight_layout()
            anim_placeholder.pyplot(fig)
            plt.close(fig) 
            
    except Exception as e:
        st.error(f"Lỗi vẽ: {e}")

    st.session_state['animating'] = False
    st.rerun()

else:
    # ==========================================
    # GIAO DIỆN CHÍNH
    # ==========================================
    st.markdown('<div class="main-header">🌊 PHẦN MỀM TÍNH TOÁN ĐIỀU TIẾT LŨ HỒ CHỨA</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="input-box">', unsafe_allow_html=True)
        st.markdown("<h5 style='color:#0F4C81; text-align: center; margin-bottom: 15px;'>📋 BẢNG QUAN HỆ Z - F - V LÒNG HỒ</h5>", unsafe_allow_html=True)
        df_zv_input = st.data_editor(sample_zv, num_rows="dynamic", use_container_width=True, height=250)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c2:
        st.markdown('<div class="input-box">', unsafe_allow_html=True)
        st.markdown("<h5 style='color:#0F4C81; text-align: center; margin-bottom: 15px;'>🌧️ QUÁ TRÌNH LŨ ĐẾN (Q ~ T)</h5>", unsafe_allow_html=True)
        df_qin_input = st.data_editor(sample_qin, num_rows="dynamic", use_container_width=True, height=250)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 CHẠY TÍNH TOÁN ĐIỀU TIẾT LŨ ", use_container_width=True):
        with st.spinner('⏳ Đang tính toán thuật toán Puls...'):
            try:
                df_b1, df_b2, df_qza = tinh_toan_puls(df_qin_input, df_zv_input, Z_bd, Z_mndbt, dt_sec, loai_tran, a_max)
                excel_data = tao_file_excel(df_b1, df_b2, df_qza, loai_tran)
                st.session_state['calc_results'] = {
                    'df_b1': df_b1, 'df_b2': df_b2, 'df_qza': df_qza,
                    'excel_data': excel_data, 'loai_tran_cache': loai_tran, 'a_max_cache': a_max
                }
                st.session_state['calculated'] = True
                st.toast('Tính toán thành công!', icon='✅')
            except Exception as e:
                st.error(f"⚠️ Kiểm tra lại dữ liệu đầu vào. Lỗi: {e}")

    if st.session_state['calculated']:
        res = st.session_state['calc_results']
        df_b1, df_b2, df_qza = res['df_b1'], res['df_b2'], res['df_qza']
        loai_tran_cache = res['loai_tran_cache']
        
        st.download_button(
            label="📥 BẤM VÀO ĐÂY ĐỂ TẢI FILE EXCEL ",
            data=res['excel_data'],
            file_name="TinhToan_DieuTietLu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        if loai_tran_cache == "Có cửa van":
            tab_list = st.tabs(["📑 BẢNG 1: PHỤ TRỢ F1,F2 ", "📑 BẢNG 2: ĐIỀU TIẾT LŨ ", "📖 BẢNG 3: TRA QUAN HỆ (Z-Q-e)", "📈 BIỂU ĐỒ "])
            t_b1, t_b2, t_b3, t_b4 = tab_list[0], tab_list[1], tab_list[2], tab_list[3]
        else:
            tab_list = st.tabs(["📑 BẢNG 1: PHỤ TRỢ F1,F2 ", "📑 BẢNG 2: ĐIỀU TIẾT LŨ ", "📈 BIỂU ĐỒ "])
            t_b1, t_b2, t_b4 = tab_list[0], tab_list[1], tab_list[2]
        
        with t_b1:
            st.dataframe(df_b1.style.format({"Zgt (m)": "{:.2f}", "Htr (m)": "{:.2f}", "q_xa (m³/s)": "{:.2f}", "V_ho (10⁶m³)": "{:.3f}", "V_pl (10⁶m³)": "{:.3f}", "f1 (m³/s)": "{:.2f}", "f2 (m³/s)": "{:.2f}"}), use_container_width=True, height=500)
            
        with t_b2:
            if loai_tran_cache == "Có cửa van":
                styled_b2 = df_b2.style.format({"T (giờ)": "{:.2f}", "Q~T (m³/s)": "{:.2f}", "Qtb (m³/s)": "{:.2f}", "q_dau (m³/s)": "{:.2f}", "f1 (m³/s)": "{:.2f}", "f2 (m³/s)": "{:.2f}", "q_cuoi (m³/s)": "{:.2f}", "Htr (m)": "{:.3f}", "Zsc (m)": "{:.2f}", "V_ho (10⁶m³)": "{:.3f}", "Vsc (10⁶m³)": "{:.3f}", "Độ mở e (m)": "{:.2f}"}, na_rep="").highlight_max(subset=["Q~T (m³/s)", "q_cuoi (m³/s)", "Zsc (m)"], color='#DBEAFE')
            else:
                styled_b2 = df_b2.style.format({"T (giờ)": "{:.2f}", "Q~T (m³/s)": "{:.2f}", "Qtb (m³/s)": "{:.2f}", "q_dau (m³/s)": "{:.2f}", "f1 (m³/s)": "{:.2f}", "f2 (m³/s)": "{:.2f}", "q_cuoi (m³/s)": "{:.2f}", "Htr (m)": "{:.3f}", "Zsc (m)": "{:.2f}", "V_ho (10⁶m³)": "{:.3f}", "Vsc (10⁶m³)": "{:.3f}"}, na_rep="").highlight_max(subset=["Q~T (m³/s)", "q_cuoi (m³/s)", "Zsc (m)"], color='#DBEAFE')
            st.dataframe(styled_b2, use_container_width=True, height=600)
            
        if loai_tran_cache == "Có cửa van":
            with t_b3:
                st.markdown("<h5 style='color: #334155;'>BẢNG TRA CỨU LƯU LƯỢNG (Q) THEO ĐỘ MỞ VAN (e) VÀ MỰC NƯỚC (Z)</h5>", unsafe_allow_html=True)
                st.dataframe(df_qza.style.format("{:.2f}"), use_container_width=True, height=500)
                
                st.markdown("<h4 style='text-align: center; margin-top: 30px; color:#0F4C81;'>QUAN HỆ GIỮA LƯU LƯỢNG VÀ MỰC NƯỚC HỒ THEO ĐỘ MỞ CỬA VAN</h4>", unsafe_allow_html=True)
                fig4, ax4 = plt.subplots(figsize=(10, 6))
                ax4.plot(df_qza["Z (m)"], df_qza["Tràn tự do (m³/s)"], color='black', linestyle='--', linewidth=2, label='Tràn tự do (Max)')
                for col in df_qza.columns[2:]:
                    ax4.plot(df_qza["Z (m)"], df_qza[col], linewidth=1.5, label=col)
                ax4.set_xlabel('Cao trình mực nước hồ Z (m)', fontweight='bold')
                ax4.set_ylabel('Lưu lượng xả qua tràn Q (m³/s)', fontweight='bold')
                ax4.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=6, frameon=True, shadow=True) 
                ax4.grid(True, linestyle='--', alpha=0.7)
                fig4.tight_layout()
                st.pyplot(fig4)

        with t_b4:
            st.markdown("<div class='btn-anim'>", unsafe_allow_html=True)
            if st.button("▶️ PHÁT LẠI DIỄN BIẾN ĐIỀU TIẾT LŨ (TOÀN MÀN HÌNH)", use_container_width=True):
                st.session_state['animating'] = True
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("<h4 style='text-align: center; color:#0F4C81;'>BIỂU ĐỒ PHỤ TRỢ F1, F2</h4>", unsafe_allow_html=True)
                fig1, ax1 = plt.subplots(figsize=(7, 6))
                STT_arr1 = df_b1["TT"].to_numpy()
                STT_smooth1 = np.linspace(STT_arr1.min(), STT_arr1.max(), 300)
                ax1.plot(STT_smooth1, PchipInterpolator(STT_arr1, df_b1["f1 (m³/s)"].to_numpy())(STT_smooth1), color='#0070C0', label='Đường F1', linewidth=2.5)
                ax1.plot(STT_smooth1, PchipInterpolator(STT_arr1, df_b1["f2 (m³/s)"].to_numpy())(STT_smooth1), color='#FF0000', label='Đường F2', linewidth=2.5)
                ax1.set_xlabel('Số thứ tự (TT)', fontweight='bold')
                ax1.set_ylabel('Lưu lượng F1, F2 (m³/s)', fontweight='bold')
                ax1.legend(loc='lower right', frameon=True, shadow=True)
                ax1.grid(True, linestyle='--', alpha=0.7)
                fig1.tight_layout()
                st.pyplot(fig1)
                
            with col_chart2:
                st.markdown("<h4 style='text-align: center; color:#0F4C81;'>BIỂU ĐỒ QUÁ TRÌNH ĐIỀU TIẾT LŨ</h4>", unsafe_allow_html=True)
                fig2, ax2 = plt.subplots(figsize=(7, 6))
                T_arr = df_b2["T (giờ)"].to_numpy()
                T_smooth2 = np.linspace(T_arr.min(), T_arr.max(), 300)
                ax2.plot(T_smooth2, PchipInterpolator(T_arr, df_b2["Q~T (m³/s)"].to_numpy())(T_smooth2), color='#FF0000', label='Lũ đến (Qin)', linewidth=2.5)
                ax2.plot(T_smooth2, PchipInterpolator(T_arr, df_b2["q_cuoi (m³/s)"].to_numpy())(T_smooth2), color='#0070C0', label='Lũ xả (Qout)', linewidth=2.5)
                ax2.set_xlabel('Thời gian (Giờ)', fontweight='bold')
                ax2.set_ylabel('Lưu lượng (m³/s)', fontweight='bold')
                ax2.set_ylim(bottom=0)
                ax2.grid(True, linestyle='--', alpha=0.7)
                
                ax3 = ax2.twinx()
                z_min = df_b2["Zsc (m)"].min()
                z_max = df_b2["Zsc (m)"].max()
                dz = z_max - z_min if z_max > z_min else 1.0
                ax3.set_ylim(z_min - 0.2 * dz, z_max + 8.0 * dz)
                ax3.plot(T_smooth2, PchipInterpolator(T_arr, df_b2["Zsc (m)"].to_numpy())(T_smooth2), color='#00B050', linestyle='--', label='Mực nước (Z)', linewidth=2.5)
                ax3.set_ylabel('Mực nước hồ (m)', color='#00B050', fontweight='bold')
                lines, labels = ax2.get_legend_handles_labels()
                lines2, labels2 = ax3.get_legend_handles_labels()
                ax2.legend(lines + lines2, labels + labels2, loc='upper right', frameon=True, shadow=True, handlelength=3)
                fig2.tight_layout()
                st.pyplot(fig2)

            if loai_tran_cache == "Có cửa van":
                st.markdown("<h4 style='text-align: center; margin-top: 40px; color:#0F4C81;'>BIỂU ĐỒ QUÁ TRÌNH ĐỘ MỞ CỬA VAN</h4>", unsafe_allow_html=True)
                fig3, ax_a = plt.subplots(figsize=(14, 4))
                ax_a.plot(T_smooth2, PchipInterpolator(T_arr, df_b2["Độ mở e (m)"].to_numpy())(T_smooth2), color='#8B4513', linewidth=2.5, label='Độ mở van (e)')
                ax_a.set_xlabel('Thời gian (Giờ)', fontweight='bold')
                ax_a.set_ylabel('Độ mở e (m)', fontweight='bold')
                ax_a.set_ylim(bottom=0, top=res['a_max_cache'] + 0.5)
                ax_a.grid(True, linestyle='--', alpha=0.7)
                ax_a.legend(loc='upper right', frameon=True, shadow=True)
                fig3.tight_layout()
                st.pyplot(fig3)

            # --- BẢNG TỔNG HỢP CHỈ TIÊU ---
            st.markdown("<hr style='margin-top: 40px; margin-bottom: 20px;'>", unsafe_allow_html=True)
            st.markdown("<div style='background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color:#1E3A8A; margin-bottom: 20px;'>🏆 BẢNG TỔNG HỢP</h3>", unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("🌊 Mực nước lớn nhất (Zsc_max)", f"{df_b2['Zsc (m)'].max():.2f} m")
            m1.metric("📏 Cột nước tràn lớn nhất (Htr_max)", f"{df_b2['Htr (m)'].max():.2f} m")
            m2.metric("🌪️ Lưu lượng xả lớn nhất (Qxả_max)", f"{df_b2['q_cuoi (m³/s)'].max():.2f} m³/s")
            m2.metric("📦 Dung tích phòng lũ sử dụng lớn nhất (Vsc)", f"{df_b2['Vsc (10⁶m³)'].max():.3f} x10⁶ m³")
            st.markdown("</div>", unsafe_allow_html=True)
