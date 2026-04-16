#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 02:38:54 2026

@author: kllin
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import sqlite3
import re
import pandas as pd

# --- 設定頁面外觀 ---
st.set_page_config(page_title="🔬 智能實驗室系統", layout="wide", page_icon="🧪")

# --- 1. 資料庫基礎與核心邏輯 ---

def init_db():
    conn = sqlite3.connect('chemistry.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS elements 
                      (symbol TEXT PRIMARY KEY, atomic_weight REAL)''')
    # 預設元素表
    elements_data = [
        ('H', 1.008), ('He', 4.0026), ('Li', 6.94), ('Be', 9.0122),
        ('B', 10.81), ('C', 12.011), ('N', 14.007), ('O', 15.999),
        ('F', 18.998), ('Na', 22.990), ('Mg', 24.305), ('Al', 26.982),
        ('Si', 28.085), ('P', 30.974), ('S', 32.06), ('Cl', 35.45),
        ('K', 39.098), ('Ca', 40.078), ('Fe', 55.845), ('Co', 58.933),
        ('Cu', 63.546), ('Zn', 65.38), ('I', 126.90), ('Ag', 107.87)
    ]
    cursor.executemany("INSERT OR IGNORE INTO elements VALUES (?, ?)", elements_data)
    conn.commit()
    conn.close()

def get_element_weight(symbol):
    conn = sqlite3.connect('chemistry.db')
    cursor = conn.cursor()
    cursor.execute("SELECT atomic_weight FROM elements WHERE symbol = ?", (symbol,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_new_element(symbol, weight):
    conn = sqlite3.connect('chemistry.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO elements VALUES (?, ?)", (symbol, weight))
    conn.commit()
    conn.close()

def delete_element(symbol):
    conn = sqlite3.connect('chemistry.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM elements WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()

def sum_basic_formula(formula):
    total_mw = 0.0
    virtual_mws = re.findall(r'\[MW:([\d.]+)\]', formula)
    total_mw += sum(float(m) for m in virtual_mws)
    
    clean_f = re.sub(r'\[MW:[\d.]+\]', '', formula)
    # 關鍵 Regex：區分大小寫
    tokens = re.findall(r'([A-Z][a-z]*)(\d*)', clean_f)
    
    for symbol, count in tokens:
        count = int(count) if count else 1
        weight = get_element_weight(symbol)
        if weight is None:
            st.error(f"❌ 找不到元素 [{symbol}]，請在左側資料庫新增。")
            return -1.0
        total_mw += weight * count
    return total_mw

def calculate_recursive_mw(formula):
    bracket_pattern = r'\(([^()]+)\)(\d*)'
    temp_formula = formula.replace(" ", "") 
    
    while '(' in temp_formula:
        match = re.search(bracket_pattern, temp_formula)
        if match:
            inner_str = match.group(1)
            multiplier = int(match.group(2)) if match.group(2) else 1
            inner_mw = sum_basic_formula(inner_str)
            if inner_mw < 0: return 0.0
            temp_formula = temp_formula.replace(match.group(0), f"[MW:{inner_mw * multiplier}]", 1)
        else: break
    
    res = sum_basic_formula(temp_formula)
    return res if res > 0 else 0.0

def analyze_properties(formula):
    # (此部分邏輯與先前一致，保留大小寫識別)
    clean_f = formula.replace(" ", "")
    ph = "中性 (pH ≈ 7)"
    if clean_f.startswith('H') or 'COOH' in clean_f: ph = "酸性 (pH < 7)"
    elif clean_f.endswith('OH') or 'NH3' in clean_f: ph = "鹼性 (pH > 7)"
    
    metals = ['Na', 'K', 'Mg', 'Ca', 'Fe', 'Cu', 'Zn', 'Ag', 'Al', 'Ba', 'Co']
    has_metal = any(m in clean_f for m in metals)
    elec = "強電解質" if (has_metal or clean_f.startswith('H') or 'NH4' in clean_f) else "非電解質"
    if 'COOH' in clean_f: elec = "弱電解質"
    
    temp_f = clean_f
    while '(' in temp_f:
        match = re.search(r'\(([^()]+)\)(\d*)', temp_f)
        if match:
            inner = match.group(1); mult = int(match.group(2)) if match.group(2) else 1
            temp_f = temp_f.replace(match.group(0), inner * mult)
        else: break
    atom_matches = re.findall(r'([A-Z][a-z]?)(\d*)', temp_f)
    total_atoms = sum(int(c) if c else 1 for _, c in atom_matches)
    
    msds_warnings = []
    if "酸性" in ph: msds_warnings.append("☢️ 腐蝕性警告：酸性化學品，可能導致灼傷。")
    if "鹼性" in ph: msds_warnings.append("☢️ 腐蝕性警告：鹼性化學品，具強腐蝕性。")
    if elec == "強電解質": msds_warnings.append("⚡ 導電風險：溶液導電性強。")
    if not msds_warnings: msds_warnings.append("⚠️ 通用安全建議：請配戴基本防護具。")
    
    return ph, elec, total_atoms, msds_warnings

# --- 2. Streamlit 介面設計 ---
init_db()

# --- 側邊欄：完整的資料庫管理功能 ---
with st.sidebar:
    st.header("🗄️ 元素資料庫管理")
    
    # 顯示目前資料
    conn = sqlite3.connect('chemistry.db')
    df = pd.read_sql_query("SELECT * FROM elements ORDER BY symbol ASC", conn)
    conn.close()
    
    st.subheader("📊 目前收錄元素")
    st.dataframe(df, use_container_width=True, hide_index=True, height=300)
    
    # 新增/更新功能
    st.divider()
    st.subheader("➕ 新增/更新元素")
    new_sym = st.text_input("元素符號 (如: Au 或 Co)", key="new_sym")
    new_weight = st.number_input("原子量 (g/mol)", min_value=0.0, step=0.0001, format="%.4f")
    if st.button("確認儲存", use_container_width=True):
        if new_sym:
            save_new_element(new_sym, new_weight)
            st.success(f"✅ 已儲存 {new_sym}")
            st.rerun()
        else:
            st.error("請輸入符號")

    # --- 關鍵：刪除功能加回這裡 ---
    st.divider()
    st.subheader("🗑️ 刪除元素資料")
    # 使用下拉選單，讓使用者從現有的 symbol 中選擇
    element_list = df['symbol'].tolist()
    del_sym = st.selectbox("選擇要刪除的元素", ["請選擇..."] + element_list)
    
    if st.button("🔥 執行刪除", type="primary", use_container_width=True):
        if del_sym != "請選擇...":
            delete_element(del_sym)
            st.warning(f"已刪除元素：{del_sym}")
            st.rerun()
        else:
            st.error("請先選擇一個元素")

# --- 主頁面 ---
st.title("🔬 智能化學系統")
st.caption("大小寫敏感解析 | 資料庫完全管理版")

tab1, tab2 = st.tabs(["🧪 分子量與特性分析", "📊 濃度配製計算"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        raw_f = st.text_input("請輸入化學式", placeholder="例如: CoCl2, CO2, (NH4)2SO4")
        analyze_btn = st.button("開始解析系統", type="primary")

    if analyze_btn and raw_f:
        with st.status("正在計算中...", expanded=False) as status:
            # 這裡直接使用原始輸入，保留大小寫
            mw = calculate_recursive_mw(raw_f)
            if mw > 0:
                ph, elec, atoms, msds = analyze_properties(raw_f)
                status.update(label="解析完成！", state="complete")
                
                st.balloons()
                c1, c2, c3 = st.columns(3)
                c1.metric("識別結果", raw_f)
                c2.metric("理論分子量", f"{mw:.4f} g/mol")
                c3.metric("原子總數", f"{atoms} 個")
                
                st.subheader("📋 特性分析報告")
                st.info(f"**酸鹼值預測：** {ph}")
                st.info(f"**電解質判定：** {elec}")
                
                st.subheader("🚨 MSDS 安全警示")
                for msg in msds:
                    st.error(msg)
                
                st.session_state['current_mw'] = mw
                st.session_state['current_f'] = raw_f
            else:
                status.update(label="解析失敗，請確認元素是否存在於資料庫", state="error")

with tab2:
    if 'current_mw' not in st.session_state:
        st.info("請先在第一個分頁輸入化學式進行解析。")
    else:
        mw = st.session_state['current_mw']
        st.success(f"當前目標物：**{st.session_state['current_f']}** ({mw:.4f} g/mol)")
        
        mode = st.radio("選擇計算模式", ["配製新溶液", "調整現有濃度"])
        if mode == "配製新溶液":
            m_target = st.number_input("目標濃度 (M)", min_value=0.0, format="%.4f")
            v_target = st.number_input("目標體積 (L)", min_value=0.0, format="%.4f")
            if st.button("計算稱重"):
                res = m_target * v_target * mw
                st.success(f"✨ 實驗指令：需稱取重量 **{res:.4f}** g")
        else:
            w_now = st.number_input("現有溶質重量 (g)", min_value=0.0, format="%.4f")
            v_now = st.number_input("現有體積 (L)", min_value=0.0, format="%.4f")
            tm_target = st.number_input("目標濃度 (M)", min_value=0.0, format="%.4f", key="tm")
            if st.button("分析調整方案"):
                cur_m = w_now / (mw * v_now)
                st.write(f"📊 目前實測濃度為：`{cur_m:.4f} M`")
                if cur_m < tm_target:
                    needed = (tm_target * v_now * mw) - w_now
                    st.warning(f"👉 濃度不足，需補加溶質：**{needed:.4f}** g")
                else:
                    dilute = (cur_m * v_now / tm_target) * 1000
                    st.success(f"👉 濃度過高，需加水稀釋至總體積：**{dilute:.1f}** mL")

st.divider()
st.markdown("<center style='opacity: 0.5;'>系統已就緒 | 支援大小寫與資料庫即時刪改</center>", unsafe_allow_html=True)