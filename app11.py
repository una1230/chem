# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 02:56:53 2026

@author: User
"""

import sqlite3
import re
import streamlit as st

# --- 核心邏輯類別 ---
class ChemistrySystem:
    def __init__(self, db_path='chemistry.db'):
        self.db_path = db_path
        self.init_db()
        self.db_dict = self.get_all_elements_dict()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS elements 
                          (symbol TEXT PRIMARY KEY, atomic_weight REAL)''')
        elements_data = [
            ('H', 1.008), ('He', 4.0026), ('Li', 6.94), ('Be', 9.0122),
            ('B', 10.81), ('C', 12.011), ('N', 14.007), ('O', 15.999),
            ('F', 18.998), ('Na', 22.990), ('Mg', 24.305), ('Al', 26.982),
            ('Si', 28.085), ('P', 30.974), ('S', 32.06), ('Cl', 35.45),
            ('K', 39.098), ('Ca', 40.078), ('Fe', 55.845), ('Cu', 63.546),
            ('Zn', 65.38), ('I', 126.90), ('Ag', 107.87), ('Ba', 137.33)
        ]
        cursor.executemany("INSERT OR IGNORE INTO elements VALUES (?, ?)", elements_data)
        conn.commit()
        conn.close()

    def get_all_elements_dict(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, atomic_weight FROM elements ORDER BY symbol ASC")
        data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return data

    def save_new_element(self, symbol, weight):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO elements VALUES (?, ?)", (symbol, weight))
        conn.commit()
        conn.close()
        self.db_dict = self.get_all_elements_dict()

    def delete_element(self, symbol):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM elements WHERE symbol = ?", (symbol,))
        conn.commit()
        conn.close()
        self.db_dict = self.get_all_elements_dict()

    def parse_basic_string(self, text, is_bracket_content=False):
        if not is_bracket_content or " " not in text:
            text = text.replace(" ", "")
        total_mw = 0.0
        i = 0
        while i < len(text):
            tag_match = re.match(r'\[MW:([\d.]+)\]', text[i:])
            if tag_match:
                total_mw += float(tag_match.group(1))
                i += len(tag_match.group(0))
                continue
            
            found_symbol = None
            if i + 1 < len(text) and text[i].isupper() and text[i+1].islower():
                potential_sym = text[i:i+2]
                if potential_sym in self.db_dict:
                    found_symbol = potential_sym
                    i += 2
            
            if not found_symbol and i < len(text) and text[i].isalpha():
                potential_sym = text[i].upper() if text[i].islower() else text[i]
                if potential_sym in self.db_dict:
                    found_symbol = potential_sym
                    i += 1

            if found_symbol:
                weight = self.db_dict[found_symbol]
                num_match = re.match(r'\d+', text[i:])
                count = int(num_match.group()) if num_match else 1
                if num_match: i += len(num_match.group())
                total_mw += weight * count
                continue
            
            unknown_match = re.match(r'[a-zA-Z]+', text[i:])
            if unknown_match:
                full_unknown = unknown_match.group()
                sym_to_ask = full_unknown[0].upper()
                if len(full_unknown) >= 2 and full_unknown[1].islower():
                    sym_to_ask += full_unknown[1]
                raise ValueError(f"資料庫找不到元素 [{sym_to_ask}]，請先在左側欄位新增。")
            else:
                i += 1
        return total_mw

    def calculate_recursive_mw(self, formula):
        bracket_pattern = r'\(([^()]+)\)(\d*)'
        temp_formula = formula
        while '(' in temp_formula:
            match = re.search(bracket_pattern, temp_formula)
            if match:
                inner_str = match.group(1)
                multiplier = int(match.group(2)) if match.group(2) else 1
                if " " in inner_str:
                    parts = inner_str.split()
                    inner_mw = sum(self.parse_basic_string(p, is_bracket_content=True) for p in parts)
                else:
                    inner_mw = self.parse_basic_string(inner_str, is_bracket_content=True)
                temp_formula = temp_formula.replace(match.group(0), f"[MW:{inner_mw * multiplier}]", 1)
            else:
                break
        return self.parse_basic_string(temp_formula, is_bracket_content=False)

    def analyze_properties(self, formula):
        # --- 修正後的電解質與酸鹼判定邏輯 ---
        f_clean = formula.replace(" ", "")
        f_upper = f_clean.upper()
        
        metals = ['NA', 'K', 'MG', 'CA', 'FE', 'CU', 'ZN', 'AG', 'AL', 'BA', 'LI', 'BE', 'CO']
        strong_acid_roots = ['CL', 'SO4', 'NO3', 'BR', 'I', 'CLO4']
        
        has_metal = any(m in f_upper for m in metals)
        is_ammonium = 'NH4' in f_upper
        is_organic = 'C' in f_upper and not is_ammonium
        
        # 1. 酸鹼性判定
        if (f_upper.startswith('H') and f_upper != 'H2O') or 'COOH' in f_upper:
            ph = "酸性 (pH < 7)"
        elif (('OH' in f_upper) and (has_metal or is_ammonium)) or 'NH3' in f_upper:
            ph = "鹼性 (pH > 7)"
        elif is_organic and ('OH' in f_upper or 'CHO' in f_upper) and 'COOH' not in f_upper:
            ph = "中性 (醇類/醣類等有機物)"
        else:
            ph = "中性 (pH ≈ 7)"

        # 2. 電解質判定
        is_strong_acid = f_upper.startswith('H') and any(root in f_upper for root in strong_acid_roots)
        is_strong_base = ('OH' in f_upper) and any(m in f_upper for m in ['NA', 'K', 'CA', 'BA', 'LI'])
        
        if is_strong_acid or is_strong_base or (has_metal and not is_organic) or (is_ammonium and any(root in f_upper for root in strong_acid_roots or ['CL'])):
            elec = "強電解質 (強酸/強鹼/可溶性鹽類)"
        elif 'COOH' in f_upper or 'NH3' in f_upper or (f_upper.startswith('H') and not is_strong_acid and f_upper != 'H2O'):
            elec = "弱電解質 (弱酸/弱鹼)"
        elif is_organic or f_upper == 'H2O':
            elec = "非電解質 (多為共價有機物或純水)"
        else:
            elec = "視具體解離度而定"

        # 3. MSDS 安全警示
        msds = []
        if "酸性" in ph or "鹼性" in ph: 
            msds.append("☢️ 腐蝕性警告：接觸可能導致化學灼傷。")
        if "強電解質" in elec: 
            msds.append("⚡ 導電風險：高濃度離子溶液，請防範短路。")
        if not msds: 
            msds.append("⚠️ 提醒：請依標準實驗室規範配戴防護具。")
            
        return ph, elec, msds

# --- Streamlit UI 介面 ---
st.set_page_config(page_title="智能化學系統", page_icon="🔬", layout="wide")

if 'chem' not in st.session_state:
    st.session_state.chem = ChemistrySystem()

chem = st.session_state.chem

with st.sidebar:
    st.title("🧪 實驗室控制台")
    st.markdown("---")
    
    st.subheader("🆕 新增元素")
    with st.form("add_element_form"):
        new_sym = st.text_input("元素符號", max_chars=2)
        new_weight = st.number_input("原子量", min_value=0.001, format="%.4f")
        if st.form_submit_button("存入資料庫"):
            if new_sym:
                chem.save_new_element(new_sym, new_weight)
                st.success(f"已記錄: {new_sym}")
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ 移除資料")
    all_elements = list(chem.db_dict.keys())
    del_sym = st.selectbox("選擇要刪除的元素", ["請選擇"] + all_elements)
    if st.button("確認刪除", type="primary"):
        if del_sym != "請選擇":
            chem.delete_element(del_sym)
            st.warning(f"已刪除: {del_sym}")
            st.rerun()

    st.markdown("---")
    with st.expander("📊 目前資料庫快照"):
        st.write(chem.db_dict)

st.title("🔬 智能化學解析系統")
st.caption("2026 專業版 | 核心引擎：精準解析模式")

formula_input = st.text_input("請輸入化學式", placeholder="例如: Mg(OH)2, CH3COOH, CoCl2", help="支援括號運算，如 (NH4)2SO4")

if formula_input:
    try:
        mw = chem.calculate_recursive_mw(formula_input)
        ph, elec, msds = chem.analyze_properties(formula_input)

        st.markdown("### 🧬 解析結果")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="理論分子量", value=f"{mw:.4f}", delta="g/mol", delta_color="off")
        with col2:
            st.info(f"**酸鹼性質**\n\n{ph}")
        with col3:
            st.success(f"**電解質性**\n\n{elec}")

        with st.expander("🚨 MSDS 安全警示 (Safety First)", expanded=True):
            for msg in msds:
                st.write(msg)

        st.markdown("---")
        st.subheader("🧪 溶液配製助手")
        mode = st.radio("功能選擇", ["跳過", "計算配製稱重", "濃度調整回饋"], horizontal=True)
        
        if mode == "計算配製稱重":
            c1, c2 = st.columns(2)
            m_target = c1.number_input("目標濃度 (M)", min_value=0.0, step=0.1, key="m1")
            v_target = c2.number_input("目標體積 (L)", min_value=0.0, step=0.1, key="v1")
            if m_target > 0 and v_target > 0:
                result_w = m_target * v_target * mw
                st.balloons()
                st.metric("👉 需稱取重量", f"{result_w:.4f} g")

        elif mode == "濃度調整回饋":
            c1, c2, c3 = st.columns(3)
            w_actual = c1.number_input("實際溶質重 (g)", min_value=0.0, step=0.1)
            v_actual = c2.number_input("目前溶液體積 (L)", min_value=0.0, step=0.1)
            m_final = c3.number_input("最終目標濃度 (M)", min_value=0.0, step=0.1)
            
            if w_actual > 0 and v_actual > 0 and m_final > 0:
                cur_m = w_actual / (mw * v_actual)
                st.write(f"📊 目前實測濃度： **{cur_m:.4f}** M")
                if cur_m > m_final:
                    needed_v = (cur_m * v_actual / m_final) * 1000
                    st.warning(f"💡 需加水稀釋至總體積： **{needed_v:.1f}** mL")
                else:
                    needed_w = (m_final * v_actual * mw) - w_actual
                    st.info(f"💡 需補加溶質： **{needed_w:.4f}** g")

    except ValueError as ve:
        st.error(f"❌ {ve}")
    except Exception as e:
        st.error(f"❌ 系統錯誤: {e}")
st.markdown("---")
st.caption("Chemistry Engine v2.1 - Clean & Professional Mode")