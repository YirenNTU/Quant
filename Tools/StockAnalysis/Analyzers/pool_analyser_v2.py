#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pool Analyser V2 - 轉型股獵人（Turnaround Hunter）
====================================================================
核心設計理念：
找出獲利結構正在改變、但市場尚未充分反映的股票

核心改進：
1. 🔥 拐點偵測：偵測 GPM/OPM 從負轉正（方向改變）
2. 📈 連續改善：追蹤連續 2-3 季的趨勢，降低單季雜訊
3. 🎯 品質分層：區分「早期轉型」vs「成熟擴張」
4. 💎 隱藏訊號：交叉比對估值位置，找出市場忽略的標的
5. 🔬 營益率彈性：OPM 改善幅度 vs GPM 改善幅度（營運槓桿）

評分邏輯（基礎分 30，滿分約 125）：
- 基礎分：30
- 拐點訊號（方向反轉）：+25（最重要！）
- 連續改善（2季+）：+20
- 營業槓桿正向：+15
- 毛利率改善：+10
- 營益率改善：+10
- 營收動能正向：+10
- 業外風險：+5（低業外）/ -10（極高業外）

數據來源：
- 本地資料庫 (Stock_Pool/Database/*.json)

輸出檔案：
structural_change_report_v2.csv: 轉型候選股報告
structural_change_report_v2_full.csv: 完整報告
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime
from io import StringIO
from glob import glob


# ==========================================
# 本地資料庫設定
# ==========================================
# 從 Analyzers/pool_analyser_v2.py 往上4層到達專案根目錄
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Stock_Pool", "Database")


def load_database():
    """載入本地資料庫索引"""
    database = {}
    if not os.path.exists(DATABASE_DIR):
        print(f"⚠️ 警告: 資料庫目錄不存在: {DATABASE_DIR}")
        return database
    
    json_files = glob(os.path.join(DATABASE_DIR, "*.json"))
    
    for json_path in json_files:
        try:
            filename = os.path.basename(json_path)
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 2:
                code = parts[0]
                if code not in database:
                    database[code] = json_path
                else:
                    existing_date = os.path.basename(database[code]).replace('.json', '').split('_')[1]
                    new_date = parts[1]
                    if new_date > existing_date:
                        database[code] = json_path
        except Exception:
            continue
    
    return database


def load_financials_from_database(ticker: str, database: dict) -> pd.DataFrame | None:
    """
    從本地資料庫載入財務報表並計算 GPM/OPM
    
    需要至少 8 季資料以計算連續趨勢
    """
    code = ticker.replace('.TW', '')
    
    if code not in database:
        return None
    
    try:
        with open(database[code], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data.get('financials'):
            return None
        
        fin_df = pd.read_json(StringIO(data['financials']), orient='split')
        
        if fin_df.empty:
            return None
        
        # 轉置：原本是 row=指標, col=日期，轉為 row=日期
        fin_t = fin_df.T
        fin_t.index.name = 'mdate'
        fin_t = fin_t.reset_index()
        
        # 計算 GPM, OPM
        revenue = fin_t['Revenue'] if 'Revenue' in fin_t.columns else fin_t.get('Total Revenue')
        gross_profit = fin_t.get('Gross Profit')
        operating_income = fin_t['Operating Income'] if 'Operating Income' in fin_t.columns else fin_t.get('EBIT')
        net_income = fin_t['Net Income'] if 'Net Income' in fin_t.columns else fin_t.get('Net Income Common Stockholders')
        
        if revenue is None or gross_profit is None or operating_income is None:
            return None
        
        # 轉換為數值
        revenue = pd.to_numeric(revenue, errors='coerce')
        gross_profit = pd.to_numeric(gross_profit, errors='coerce')
        operating_income = pd.to_numeric(operating_income, errors='coerce')
        net_income = pd.to_numeric(net_income, errors='coerce') if net_income is not None else None
        
        # 計算比率
        with np.errstate(divide='ignore', invalid='ignore'):
            fin_t['revenue'] = revenue
            
            # 1. GPM/OPM 計算
            # 優先使用 TEJ 官方比率 (若資料庫已更新)
            if 'TEJ_GPM' in fin_t.columns and 'TEJ_OPM' in fin_t.columns:
                fin_t['gpm'] = pd.to_numeric(fin_t['TEJ_GPM'], errors='coerce')
                fin_t['opm'] = pd.to_numeric(fin_t['TEJ_OPM'], errors='coerce')
            else:
                fin_t['gpm'] = np.where(revenue != 0, gross_profit / revenue * 100, np.nan)
                fin_t['opm'] = np.where(revenue != 0, operating_income / revenue * 100, np.nan)
            
            # 2. 計算業外比重
            # 業外收支 = 稅前淨利 - 營業利益
            if 'Pretax Income' in fin_t.columns and operating_income is not None:
                # 精確計算：業外 = 稅前淨利 - 營業利益
                pretax = pd.to_numeric(fin_t['Pretax Income'], errors='coerce')
                non_op_val = pretax - operating_income
                fin_t['non_op_ratio'] = np.where(np.abs(net_income) != 0, np.abs(non_op_val) / np.abs(net_income) * 100, 0)
            elif net_income is not None and operating_income is not None:
                # 舊邏輯與異常偵測
                non_op = np.abs(net_income - operating_income)
                ratio = np.where(np.abs(net_income) != 0, non_op / np.abs(net_income) * 100, 0)
                
                # 異常偵測：修正 TEJ 舊資料中 Operating Income 數值錯誤問題
                # 如果 OPM < 0.5% 但 Net Margin > 3%，視為資料異常，不計算業外風險，避免錯誤扣分
                opm_est = np.where(revenue != 0, operating_income / revenue * 100, 0)
                nm_est = np.where(revenue != 0, net_income / revenue * 100, 0)
                is_data_error = (np.abs(opm_est) < 0.5) & (np.abs(nm_est) > 3) & (net_income > 0)
                
                fin_t['non_op_ratio'] = np.where(is_data_error, 0, ratio)
            else:
                fin_t['non_op_ratio'] = 0
        
        return fin_t
    
    except Exception as e:
        print(f"    ⚠️  載入資料庫錯誤: {e}")
        return None


def calculate_margin_metrics(fin_data: pd.DataFrame) -> dict | None:
    """
    計算毛利率/營益率的多維度指標
    
    Returns:
        {
            'gpm_latest': 最新毛利率,
            'opm_latest': 最新營益率,
            'gpm_yoy_slope': GPM YoY 斜率 (t - t-4),
            'opm_yoy_slope': OPM YoY 斜率 (t - t-4),
            'gpm_yoy_slope_prev': 前一期 GPM YoY 斜率,
            'opm_yoy_slope_prev': 前一期 OPM YoY 斜率,
            'gpm_inflection': GPM 是否出現拐點 (負轉正),
            'opm_inflection': OPM 是否出現拐點,
            'consecutive_gpm_improve': GPM 連續改善季數,
            'consecutive_opm_improve': OPM 連續改善季數,
            'operating_leverage': 營業槓桿 (OPM改善/GPM改善),
            'non_operating_ratio': 業外比重
        }
    """
    try:
        if len(fin_data) < 8:  # 需要 8 季資料
            return None
        
        # 確保按日期排序 (最新在前)
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # === 基本數值 ===
        gpm_latest = fin_data.loc[0, 'gpm']
        opm_latest = fin_data.loc[0, 'opm']
        non_op_ratio = fin_data.loc[0, 'non_op_ratio'] / 100 if pd.notna(fin_data.loc[0, 'non_op_ratio']) else 0
        
        # === YoY 斜率計算 (去季節化) ===
        # 最新 YoY: Q0 vs Q4
        gpm_0, gpm_4 = fin_data.loc[0, 'gpm'], fin_data.loc[4, 'gpm'] if len(fin_data) > 4 else None
        opm_0, opm_4 = fin_data.loc[0, 'opm'], fin_data.loc[4, 'opm'] if len(fin_data) > 4 else None
        
        # 前一期 YoY: Q1 vs Q5
        gpm_1, gpm_5 = fin_data.loc[1, 'gpm'] if len(fin_data) > 1 else None, fin_data.loc[5, 'gpm'] if len(fin_data) > 5 else None
        opm_1, opm_5 = fin_data.loc[1, 'opm'] if len(fin_data) > 1 else None, fin_data.loc[5, 'opm'] if len(fin_data) > 5 else None
        
        # 更前一期 YoY: Q2 vs Q6
        gpm_2, gpm_6 = fin_data.loc[2, 'gpm'] if len(fin_data) > 2 else None, fin_data.loc[6, 'gpm'] if len(fin_data) > 6 else None
        opm_2, opm_6 = fin_data.loc[2, 'opm'] if len(fin_data) > 2 else None, fin_data.loc[6, 'opm'] if len(fin_data) > 6 else None
        
        # 計算 YoY 斜率
        gpm_yoy_slope = gpm_0 - gpm_4 if pd.notna(gpm_0) and pd.notna(gpm_4) else None
        opm_yoy_slope = opm_0 - opm_4 if pd.notna(opm_0) and pd.notna(opm_4) else None
        gpm_yoy_slope_prev = gpm_1 - gpm_5 if pd.notna(gpm_1) and pd.notna(gpm_5) else None
        opm_yoy_slope_prev = opm_1 - opm_5 if pd.notna(opm_1) and pd.notna(opm_5) else None
        gpm_yoy_slope_prev2 = gpm_2 - gpm_6 if pd.notna(gpm_2) and pd.notna(gpm_6) else None
        opm_yoy_slope_prev2 = opm_2 - opm_6 if pd.notna(opm_2) and pd.notna(opm_6) else None
        
        if gpm_yoy_slope is None or opm_yoy_slope is None:
            return None
        
        # === 拐點偵測 (Inflection Point) ===
        # 拐點 = 前一期為負，當期為正（方向反轉）
        gpm_inflection = False
        opm_inflection = False
        
        if gpm_yoy_slope_prev is not None:
            gpm_inflection = (gpm_yoy_slope_prev < 0 and gpm_yoy_slope > 0) or \
                            (gpm_yoy_slope_prev < -2 and gpm_yoy_slope > gpm_yoy_slope_prev + 3)  # 大幅改善也算
        
        if opm_yoy_slope_prev is not None:
            opm_inflection = (opm_yoy_slope_prev < 0 and opm_yoy_slope > 0) or \
                            (opm_yoy_slope_prev < -2 and opm_yoy_slope > opm_yoy_slope_prev + 3)
        
        # === 連續改善計算 ===
        # 計算 GPM 連續 YoY 改善季數
        consecutive_gpm = 0
        if gpm_yoy_slope > 0:
            consecutive_gpm = 1
            if gpm_yoy_slope_prev is not None and gpm_yoy_slope_prev > 0:
                consecutive_gpm = 2
                if gpm_yoy_slope_prev2 is not None and gpm_yoy_slope_prev2 > 0:
                    consecutive_gpm = 3
        
        # 計算 OPM 連續 YoY 改善季數
        consecutive_opm = 0
        if opm_yoy_slope > 0:
            consecutive_opm = 1
            if opm_yoy_slope_prev is not None and opm_yoy_slope_prev > 0:
                consecutive_opm = 2
                if opm_yoy_slope_prev2 is not None and opm_yoy_slope_prev2 > 0:
                    consecutive_opm = 3
        
        # === 營業槓桿係數 ===
        if abs(gpm_yoy_slope) < 0.01:
            operating_leverage = 0.0
        else:
            operating_leverage = opm_yoy_slope / gpm_yoy_slope
        
        return {
            'gpm_latest': gpm_latest,
            'opm_latest': opm_latest,
            'gpm_yoy_slope': gpm_yoy_slope,
            'opm_yoy_slope': opm_yoy_slope,
            'gpm_yoy_slope_prev': gpm_yoy_slope_prev,
            'opm_yoy_slope_prev': opm_yoy_slope_prev,
            'gpm_inflection': gpm_inflection,
            'opm_inflection': opm_inflection,
            'consecutive_gpm_improve': consecutive_gpm,
            'consecutive_opm_improve': consecutive_opm,
            'operating_leverage': operating_leverage,
            'non_operating_ratio': non_op_ratio
        }
    
    except Exception as e:
        print(f"    ⚠️  計算指標錯誤: {e}")
        return None


def calculate_revenue_acceleration(fin_data: pd.DataFrame) -> dict | None:
    """
    計算營收加速度（動能）
    
    公式：
    - rev_yoy_0: 最新一季 YoY%
    - rev_yoy_1: 前一季 YoY%
    - acceleration: rev_yoy_0 - rev_yoy_1 (加速度)
    - is_accelerating: 加速度 > 0
    
    Returns:
        {
            'rev_yoy': 最新營收 YoY%,
            'rev_acceleration': 營收加速度,
            'is_accelerating': 是否加速中,
            'rev_new_high': 是否創近4季新高
        }
    """
    try:
        if len(fin_data) < 6:
            return None
        
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        revenue_col = 'revenue'
        if revenue_col not in fin_data.columns:
            return None
        
        # 取得營收數據
        rev_0 = fin_data.loc[0, revenue_col]  # 最新
        rev_1 = fin_data.loc[1, revenue_col] if len(fin_data) > 1 else None
        rev_4 = fin_data.loc[4, revenue_col] if len(fin_data) > 4 else None
        rev_5 = fin_data.loc[5, revenue_col] if len(fin_data) > 5 else None
        
        if pd.isna(rev_0) or pd.isna(rev_4) or rev_4 == 0:
            return None
        
        # 最新 YoY
        rev_yoy_0 = (rev_0 - rev_4) / abs(rev_4) * 100
        
        # 前一季 YoY
        rev_yoy_1 = None
        if pd.notna(rev_1) and pd.notna(rev_5) and rev_5 != 0:
            rev_yoy_1 = (rev_1 - rev_5) / abs(rev_5) * 100
        
        # 加速度
        if rev_yoy_1 is not None:
            acceleration = rev_yoy_0 - rev_yoy_1
        else:
            acceleration = 0  # 無法計算時給 0
        
        # 是否創近 4 季新高
        recent_revs = [fin_data.loc[i, revenue_col] for i in range(1, min(5, len(fin_data)))]
        recent_revs = [r for r in recent_revs if pd.notna(r)]
        rev_new_high = rev_0 >= max(recent_revs) if recent_revs else False
        
        return {
            'rev_yoy': rev_yoy_0,
            'rev_acceleration': acceleration,
            'is_accelerating': acceleration > 0,
            'rev_new_high': rev_new_high
        }
    
    except Exception as e:
        print(f"    ⚠️  計算營收動能錯誤: {e}")
        return None


def calculate_turnaround_score(margin_metrics: dict, rev_metrics: dict) -> tuple[int, dict, str]:
    """
    計算轉型股評分（專注於結構性改變）
    
    評分邏輯（基礎分 30，累加制）：
    
    【拐點訊號】最高 +25 ★ 最重要
    - GPM 拐點 (負轉正): +15
    - OPM 拐點 (負轉正): +10
    
    【連續改善】最高 +20
    - GPM 連續改善 2季+: +10
    - OPM 連續改善 2季+: +10
    
    【營業槓桿】最高 +15
    - OL > 1.0: +15
    - OL > 0.5: +10
    - OL > 0: +5
    
    【毛利率改善】+10
    【營益率改善】+10
    【營收動能】最高 +10
    
    【業外風險】輕微調整
    - 業外比重 <= 30%: +5 (bonus)
    - 業外比重 > 80%: -10
    
    總分 = 30 + 累加，滿分約 125
    """
    score = 30  # 基礎分
    details = {'base': 30}
    
    # === 1. 拐點訊號（最有價值，給予高權重）===
    if margin_metrics['gpm_inflection']:
        score += 15
        details['gpm_inflection'] = "+15 (GPM拐點)"
    if margin_metrics['opm_inflection']:
        score += 10
        details['opm_inflection'] = "+10 (OPM拐點)"
    
    # === 2. 連續改善 ===
    if margin_metrics['consecutive_gpm_improve'] >= 2:
        score += 10
        details['gpm_consecutive'] = f"+10 (GPM連續{margin_metrics['consecutive_gpm_improve']}季)"
    if margin_metrics['consecutive_opm_improve'] >= 2:
        score += 10
        details['opm_consecutive'] = f"+10 (OPM連續{margin_metrics['consecutive_opm_improve']}季)"
    
    # === 3. 營業槓桿 ===
    ol = margin_metrics['operating_leverage']
    if ol > 1.0:
        score += 15
        details['ol'] = f"+15 (OL={ol:.2f})"
    elif ol > 0.5:
        score += 10
        details['ol'] = f"+10 (OL={ol:.2f})"
    elif ol > 0:
        score += 5
        details['ol'] = f"+5 (OL={ol:.2f})"
    else:
        details['ol'] = f"0 (OL={ol:.2f})"
    
    # === 4. 毛利率改善 ===
    if margin_metrics['gpm_yoy_slope'] > 0:
        score += 10
        details['gpm_improve'] = "+10 (GPM↑)"
    else:
        details['gpm_improve'] = "0"
    
    # === 5. 營益率改善 ===
    if margin_metrics['opm_yoy_slope'] > 0:
        score += 10
        details['opm_improve'] = "+10 (OPM↑)"
    else:
        details['opm_improve'] = "0"
    
    # === 6. 營收動能 ===
    if rev_metrics:
        if rev_metrics['is_accelerating'] and rev_metrics['rev_new_high']:
            score += 10
            details['rev_momentum'] = "+10 (營收加速+新高)"
        elif rev_metrics['is_accelerating']:
            score += 5
            details['rev_momentum'] = "+5 (營收加速)"
        elif rev_metrics['rev_yoy'] > 0:
            score += 3
            details['rev_momentum'] = "+3 (營收正成長)"
        else:
            details['rev_momentum'] = "0"
    else:
        details['rev_momentum'] = "N/A"
    
    # === 7. 業外風險（放寬標準）===
    non_op = margin_metrics['non_operating_ratio']
    if non_op <= 0.3:
        score += 5
        details['non_op'] = "+5 (低業外)"
    elif non_op > 0.8:
        score -= 10
        details['non_op'] = "-10 (極高業外風險)"
    else:
        details['non_op'] = "0"
    
    # === 決定標籤 ===
    has_inflection = margin_metrics['gpm_inflection'] or margin_metrics['opm_inflection']
    has_dual_inflection = margin_metrics['gpm_inflection'] and margin_metrics['opm_inflection']
    has_consecutive = margin_metrics['consecutive_gpm_improve'] >= 2 or margin_metrics['consecutive_opm_improve'] >= 2
    
    if score >= 80 and has_dual_inflection:
        tag = "🏆 SSS級：雙拐點確認"
    elif score >= 70 and has_inflection:
        tag = "🔥 S級：結構性拐點"
    elif score >= 60 and has_inflection:
        tag = "⭐ A級：轉型初期"
    elif score >= 60 and has_consecutive:
        tag = "⭐ A級：持續性擴張"
    elif score >= 50:
        tag = "✅ B級：趨勢改善"
    elif score >= 40:
        tag = "🔍 C級：觀察中"
    else:
        tag = "ℹ️  D級：尚無明顯訊號"
    
    return score, details, tag


def main():
    """主程式"""
    print("=" * 70)
    print("🎯 Pool Analyser V2 - 轉型股獵人 (Turnaround Hunter)")
    print("=" * 70)
    print("✨ 核心設計:")
    print("   1. 🔥 拐點偵測：找出 GPM/OPM 從負轉正的轉折")
    print("   2. 📈 連續改善：追蹤 2-3 季的持續性趨勢")
    print("   3. 🎯 品質分層：區分早期轉型 vs 成熟擴張")
    print("   4. 💎 營收動能：加速度 + 創新高訊號")
    print("   💾 資料來源: 本地資料庫 (無 API 呼叫)")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 設定路徑
    script_dir = Path(__file__).parent
    # 從 Analyzers 往上3層到達專案根目錄
    project_root = script_dir.parent.parent.parent
    list_json_path = project_root / "Stock_Pool" / "list.json"
    output_path = project_root / "Stock_Pool" / "structural_change_report_v2.csv"
    output_full_path = project_root / "Stock_Pool" / "structural_change_report_v2_full.csv"
    
    # 載入本地資料庫
    print(f"📂 載入本地資料庫: {DATABASE_DIR}")
    database = load_database()
    print(f"✅ 共載入 {len(database)} 支股票資料")
    
    # 讀取股票清單
    print(f"📂 讀取股票清單: {list_json_path}")
    try:
        with open(list_json_path, 'r', encoding='utf-8') as f:
            company_dict = json.load(f)
        
        tickers = [ticker.replace('.TW', '') for ticker in company_dict.keys()]
        print(f"✅ 共載入 {len(tickers)} 支股票代碼")
    except Exception as e:
        print(f"❌ 讀取股票清單失敗: {e}")
        return
    
    print()
    print("-" * 70)
    print("🔍 開始分析轉型訊號...")
    print("-" * 70)
    
    results = []
    error_count = 0
    skip_count = 0
    
    for i, ticker in enumerate(tickers, 1):
        ticker_tw = f"{ticker}.TW"
        company_name = company_dict.get(ticker_tw, '')
        
        print(f"\n[{i}/{len(tickers)}] 分析 {ticker} ({company_name})...")
        
        if ticker not in database:
            print(f"    ⚠️  不在資料庫中，跳過")
            skip_count += 1
            continue
        
        try:
            # 1. 載入財務報表
            fin_data = load_financials_from_database(ticker, database)
            
            if fin_data is None or len(fin_data) < 8:
                print(f"    ⚠️  財務數據不足 (需要至少 8 季)")
                error_count += 1
                continue
            
            # 2. 計算毛利率/營益率指標
            margin_metrics = calculate_margin_metrics(fin_data)
            
            if margin_metrics is None:
                print(f"    ⚠️  無法計算利潤率指標")
                error_count += 1
                continue
            
            # 3. 計算營收動能
            rev_metrics = calculate_revenue_acceleration(fin_data)
            
            # 4. 計算評分
            score, score_details, result_tag = calculate_turnaround_score(margin_metrics, rev_metrics)
            
            # 5. 儲存結果
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Score': score,
                'Result_Tag': result_tag,
                # 毛利率
                'Latest_GPM': round(margin_metrics['gpm_latest'], 2),
                'GPM_YoY_Slope': round(margin_metrics['gpm_yoy_slope'], 2),
                'GPM_Inflection': margin_metrics['gpm_inflection'],
                'GPM_Consecutive': margin_metrics['consecutive_gpm_improve'],
                # 營益率
                'Latest_OPM': round(margin_metrics['opm_latest'], 2),
                'OPM_YoY_Slope': round(margin_metrics['opm_yoy_slope'], 2),
                'OPM_Inflection': margin_metrics['opm_inflection'],
                'OPM_Consecutive': margin_metrics['consecutive_opm_improve'],
                # 營業槓桿
                'Operating_Leverage': round(margin_metrics['operating_leverage'], 2),
                # 營收動能
                'Rev_YoY': round(rev_metrics['rev_yoy'], 2) if rev_metrics else None,
                'Rev_Acceleration': round(rev_metrics['rev_acceleration'], 2) if rev_metrics else None,
                'Rev_New_High': rev_metrics['rev_new_high'] if rev_metrics else None,
                # 業外
                'Non_Op_Ratio': round(margin_metrics['non_operating_ratio'] * 100, 2),
                # 評分細節
                'Score_Details': json.dumps(score_details, ensure_ascii=False)
            })
            
            # 顯示重點結果
            icon = "🏆" if score >= 70 else ("🔥" if score >= 60 else ("⭐" if score >= 50 else "✅"))
            print(f"    {icon} 評分: {score} 分 | {result_tag}")
            
            if margin_metrics['gpm_inflection'] or margin_metrics['opm_inflection']:
                inflection_parts = []
                if margin_metrics['gpm_inflection']:
                    inflection_parts.append("GPM")
                if margin_metrics['opm_inflection']:
                    inflection_parts.append("OPM")
                print(f"       🔥 拐點訊號: {'/'.join(inflection_parts)} 出現反轉！")
            
            print(f"       GPM: {margin_metrics['gpm_latest']:.1f}% (YoY: {margin_metrics['gpm_yoy_slope']:+.1f}%)")
            print(f"       OPM: {margin_metrics['opm_latest']:.1f}% (YoY: {margin_metrics['opm_yoy_slope']:+.1f}%)")
            if rev_metrics:
                print(f"       營收 YoY: {rev_metrics['rev_yoy']:+.1f}% (加速度: {rev_metrics['rev_acceleration']:+.1f}%)")
        
        except Exception as e:
            print(f"    ❌ 處理錯誤: {str(e)}")
            error_count += 1
    
    # 生成報告
    print()
    print("=" * 70)
    print("📈 分析完成！")
    print("=" * 70)
    
    if not results:
        print("⚠️  沒有股票符合數據要求")
        return
    
    results_df = pd.DataFrame(results)
    
    # 計算排名百分位
    results_df['Score_Percentile'] = results_df['Score'].rank(pct=True) * 100
    
    # 篩選轉型股候選 (Score >= 50 或 有拐點訊號)
    filtered_df = results_df[
        (results_df['Score'] >= 50) |
        (results_df['GPM_Inflection'] == True) |
        (results_df['OPM_Inflection'] == True)
    ].copy()
    
    # 按分數降序排列
    filtered_df = filtered_df.sort_values('Score', ascending=False)
    
    # 儲存完整報告
    results_df.sort_values('Score', ascending=False).to_csv(output_full_path, index=False, encoding='utf-8-sig')
    
    # 儲存篩選後報告
    filtered_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"📁 完整報告: {output_full_path.name} ({len(results_df)} 支)")
    print(f"📁 轉型候選: {output_path.name} ({len(filtered_df)} 支)")
    print(f"⏩ 不在資料庫: {skip_count} 支")
    print(f"❌ 數據異常/錯誤: {error_count} 支")
    print()
    
    # 統計摘要
    print("-" * 70)
    print("📋 評級統計:")
    print("-" * 70)
    
    tag_counts = filtered_df['Result_Tag'].value_counts()
    for tag, count in tag_counts.items():
        print(f"   {tag}: {count} 支")
    
    # 拐點股特別標示
    inflection_df = filtered_df[
        (filtered_df['GPM_Inflection'] == True) | 
        (filtered_df['OPM_Inflection'] == True)
    ]
    print()
    print(f"🔥 出現拐點訊號: {len(inflection_df)} 支")
    
    # Top 15 展示
    print()
    print("-" * 70)
    print("🏆 Top 15 轉型候選股:")
    print("-" * 70)
    
    top15 = filtered_df.head(15)
    for idx, row in top15.iterrows():
        inflection_mark = ""
        if row['GPM_Inflection'] or row['OPM_Inflection']:
            inflection_parts = []
            if row['GPM_Inflection']:
                inflection_parts.append("GPM")
            if row['OPM_Inflection']:
                inflection_parts.append("OPM")
            inflection_mark = f" 🔥拐點({'/'.join(inflection_parts)})"
        
        print(f"\n   {row['Score']:.0f} 分 | {row['Ticker']} ({row['Company_Name']}){inflection_mark}")
        print(f"      {row['Result_Tag']}")
        print(f"      GPM: {row['Latest_GPM']}% (YoY: {row['GPM_YoY_Slope']:+}%, 連續{row['GPM_Consecutive']}季)")
        print(f"      OPM: {row['Latest_OPM']}% (YoY: {row['OPM_YoY_Slope']:+}%, 連續{row['OPM_Consecutive']}季)")
        print(f"      營收 YoY: {row['Rev_YoY']}% | 加速度: {row['Rev_Acceleration']}% | OL: {row['Operating_Leverage']}")
    
    print()
    print(f"⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
