#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forensic Analyzer V2 - 風險貼水機制（軟性懲罰版）
=================================================
從「剔除壞學生」轉變為「計算風險貼水」，讓評分更連續、更精準。

核心改進：
1. 🛡️ Soft Penalty：Sloan/F-Score 異常扣分而非剔除
2. 🔍 Hollow Profit Detection：偵測虛胖獲利（業外佔比過高）
3. 📊 Forensic Score (0-100)：供主程式最終排序使用

資料源：本地資料庫 (Stock_Pool/Database/)
- Operating Cash Flow: 營業活動現金流 (OCF)
- Net Income: 稅後淨利
- Investing Cash Flow: 投資活動現金流 (ICF)
- Total Assets: 資產總額
- Operating Income / EBIT: 營業利益

輸出檔案：
institutional_forensic_report_v2.csv: 含 Forensic Score 的進階報告

執行方式：
  python forensic_analyzer_v2.py

必要前置步驟：
  1. 先執行 data_downloader.py 下載資料
  2. 確保 Stock_Pool/Database/ 有 JSON 資料
  3. 確保 Stock_Pool/final_valuation_report_v2.csv 存在
"""

import pandas as pd
import numpy as np
import io
import time
import random
import json
from pathlib import Path
from datetime import datetime

# 添加 Data 資料夾到 Python 路徑
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))

# 使用 tej_tool 讀取本地資料庫
import tej_tool
from tej_tool import OFFLINE_MODE

# 取得 loader 實例
loader = tej_tool.loader


def fetch_financials_from_database(ticker: str, quarters: int = 8) -> pd.DataFrame | None:
    """
    從本地資料庫載入財務報表數據
    
    Args:
        ticker: 股票代碼 (可含 .TW 或純數字)
        quarters: 抓取季數 (預設 8 季)
    
    Returns:
        包含各指標的 DataFrame（以日期為列，指標為欄）
        欄位: mdate, net_income, ocf, icf, total_assets, op_income, revenue, gpm
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 從 tej_tool 載入財務資料
        fin_raw, bs_raw, cf_raw = loader.get_financials(ticker_tw, quarters=quarters)
        
        # 檢查數據有效性
        if fin_raw is None or fin_raw.empty:
            return None
        
        # 處理重複的日期欄位名稱
        unique_dates = []
        seen_dates = set()
        for col in fin_raw.columns:
            base_date = col.split('.')[0]
            if base_date not in seen_dates:
                unique_dates.append(col)
                seen_dates.add(base_date)
        
        # 建立合併的 DataFrame
        records = []
        for col in unique_dates[:quarters]:
            base_date = col.split('.')[0]
            try:
                record = {
                    'mdate': pd.to_datetime(base_date)
                }
                
                # 從 financials 取得 Net Income, Revenue, Operating Income
                if 'Net Income' in fin_raw.index:
                    record['net_income'] = fin_raw.loc['Net Income', col]
                elif 'Net Income Common Stockholders' in fin_raw.index:
                    record['net_income'] = fin_raw.loc['Net Income Common Stockholders', col]
                
                if 'Total Revenue' in fin_raw.index:
                    record['revenue'] = fin_raw.loc['Total Revenue', col]
                elif 'Revenue' in fin_raw.index:
                    record['revenue'] = fin_raw.loc['Revenue', col]
                
                if 'Operating Income' in fin_raw.index:
                    record['op_income'] = fin_raw.loc['Operating Income', col]
                elif 'EBIT' in fin_raw.index:
                    record['op_income'] = fin_raw.loc['EBIT', col]
                
                if 'Gross Profit' in fin_raw.index and 'revenue' in record:
                    gp = fin_raw.loc['Gross Profit', col]
                    rev = record['revenue']
                    if pd.notna(gp) and pd.notna(rev) and rev != 0:
                        record['gpm'] = (gp / rev) * 100
                
                # 從 balance_sheet 取得 Total Assets
                if bs_raw is not None and not bs_raw.empty and col in bs_raw.columns:
                    if 'Total Assets' in bs_raw.index:
                        record['total_assets'] = bs_raw.loc['Total Assets', col]
                
                # 從 cashflow 取得 OCF 和 ICF
                if cf_raw is not None and not cf_raw.empty and col in cf_raw.columns:
                    if 'Operating Cash Flow' in cf_raw.index:
                        record['ocf'] = cf_raw.loc['Operating Cash Flow', col]
                    if 'Investing Cash Flow' in cf_raw.index:
                        record['icf'] = cf_raw.loc['Investing Cash Flow', col]
                
                records.append(record)
            except Exception:
                continue
        
        if not records:
            return None
        
        result_df = pd.DataFrame(records)
        
        # 按日期排序（最新在前）
        result_df = result_df.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        return result_df
    
    except Exception as e:
        print(f"    ❌ 資料庫載入錯誤: {e}")
        return None


def calculate_sloan_ratio(fin_data: pd.DataFrame) -> float | None:
    """
    計算 Sloan Ratio（應計項目比率）- 使用標準學術定義
    
    標準公式：(Net Income - OCF) / Total Assets
    
    註：原版本包含 ICF，但這不是標準 Sloan Ratio 定義。
    標準 Sloan Ratio 僅衡量「會計盈餘」vs「現金盈餘」的差異。
    ICF（投資現金流）反映的是資本支出決策，不應納入盈餘品質計算。
    
    解讀（標準定義）：
    - < -0.05: 🏆 優秀（OCF > Net Income，現金流強勁）
    - -0.05 ~ 0.05: ✅ 正常
    - 0.05 ~ 0.10: ⚠️ 留意
    - > 0.10: 🛑 盈餘品質差（多來自應計項目而非現金）
    - > 0.20: 🚫 財務虛胖警示
    
    學術來源：Sloan, R. (1996). "Do Stock Prices Fully Reflect 
    Information in Accruals and Cash Flows about Future Earnings?"
    The Accounting Review, 71(3), 289-315.
    """
    try:
        if fin_data is None or len(fin_data) < 1:
            return None
        
        # 確保按日期排序
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 取得最新一季數據
        net_income = fin_data.loc[0, 'net_income'] if 'net_income' in fin_data.columns else None
        ocf = fin_data.loc[0, 'ocf'] if 'ocf' in fin_data.columns else None
        total_assets = fin_data.loc[0, 'total_assets'] if 'total_assets' in fin_data.columns else None
        
        if net_income is None or ocf is None or total_assets is None:
            return None
        
        if pd.isna(net_income) or pd.isna(ocf) or pd.isna(total_assets) or total_assets == 0:
            return None
        
        # 標準 Sloan Ratio 公式：(Net Income - OCF) / Total Assets
        # 注意：不包含 ICF（投資現金流）
        sloan_ratio = (net_income - ocf) / abs(total_assets)
        
        return sloan_ratio
    
    except Exception:
        return None


def calculate_piotroski_f_score(fin_data: pd.DataFrame) -> tuple[int | None, int]:
    """
    計算 Piotroski F-Score（9 點財務實力評分）- 修正版
    
    修正說明：
    - 原版本對無法計算的項目直接假設通過（+3分），這是錯誤的
    - 新版本只計算可計算的項目，並返回 (得分, 可計算項目數)
    - 若可計算項目數過少，調用者應視為數據不足
    
    獲利能力 (4 分):
    1. ROA > 0: +1
    2. OCF > 0: +1
    3. ROA 增加（YoY）: +1
    4. OCF > Net Income（盈餘品質）: +1
    
    槓桿/流動性 (3 分):
    5. 長期負債比下降: +1 (需要 long_term_debt 欄位)
    6. 流動比率增加: +1 (需要 current_ratio 欄位)
    7. 無增發新股: +1 (需要 shares_outstanding 欄位)
    
    營運效率 (2 分):
    8. 毛利率增加: +1
    9. 資產週轉率增加: +1
    
    Returns:
        tuple: (f_score, items_evaluated)
        - f_score: 實際得分（只計算可計算的項目）
        - items_evaluated: 成功計算的項目數（用於判斷數據品質）
        
        若 items_evaluated < 5，建議視為數據不足
    """
    try:
        if fin_data is None or len(fin_data) < 5:
            return None, 0
        
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        f_score = 0
        items_evaluated = 0
        
        # 取得數據
        ni = fin_data.loc[0, 'net_income'] if 'net_income' in fin_data.columns else None
        ta = fin_data.loc[0, 'total_assets'] if 'total_assets' in fin_data.columns else None
        ocf = fin_data.loc[0, 'ocf'] if 'ocf' in fin_data.columns else None
        rev = fin_data.loc[0, 'revenue'] if 'revenue' in fin_data.columns else None
        
        # 去年同期數據 (index 4)
        ni_yoy = fin_data.loc[4, 'net_income'] if len(fin_data) > 4 and 'net_income' in fin_data.columns else None
        ta_yoy = fin_data.loc[4, 'total_assets'] if len(fin_data) > 4 and 'total_assets' in fin_data.columns else None
        rev_yoy = fin_data.loc[4, 'revenue'] if len(fin_data) > 4 and 'revenue' in fin_data.columns else None
        
        # ═══════════════════════════════════════════════════════════════
        # 獲利能力 (4 分)
        # ═══════════════════════════════════════════════════════════════
        
        # 1. ROA > 0
        if ni is not None and ta is not None and pd.notna(ni) and pd.notna(ta) and ta > 0:
            items_evaluated += 1
            roa = ni / ta
            if roa > 0:
                f_score += 1
        
        # 2. OCF > 0
        if ocf is not None and pd.notna(ocf):
            items_evaluated += 1
            if ocf > 0:
                f_score += 1
        
        # 3. ROA 增加 (YoY)
        if all(v is not None and pd.notna(v) for v in [ni, ta, ni_yoy, ta_yoy]) and ta > 0 and ta_yoy > 0:
            items_evaluated += 1
            roa_curr = ni / ta
            roa_yoy = ni_yoy / ta_yoy
            if roa_curr > roa_yoy:
                f_score += 1
        
        # 4. OCF > Net Income（盈餘品質）
        if ocf is not None and ni is not None and pd.notna(ocf) and pd.notna(ni):
            items_evaluated += 1
            if ocf > ni:
                f_score += 1
        
        # ═══════════════════════════════════════════════════════════════
        # 槓桿/流動性 (3 分) - 只有在有數據時才計算
        # ═══════════════════════════════════════════════════════════════
        
        # 5. 長期負債比下降 (需要 long_term_debt 和 total_assets)
        if 'long_term_debt' in fin_data.columns and len(fin_data) > 4:
            ltd_curr = fin_data.loc[0, 'long_term_debt']
            ltd_yoy = fin_data.loc[4, 'long_term_debt']
            if all(v is not None and pd.notna(v) for v in [ltd_curr, ltd_yoy, ta, ta_yoy]) and ta > 0 and ta_yoy > 0:
                items_evaluated += 1
                ltd_ratio_curr = ltd_curr / ta
                ltd_ratio_yoy = ltd_yoy / ta_yoy
                if ltd_ratio_curr < ltd_ratio_yoy:
                    f_score += 1
        
        # 6. 流動比率增加 (需要 current_ratio 欄位)
        if 'current_ratio' in fin_data.columns and len(fin_data) > 4:
            cr_curr = fin_data.loc[0, 'current_ratio']
            cr_yoy = fin_data.loc[4, 'current_ratio']
            if cr_curr is not None and cr_yoy is not None and pd.notna(cr_curr) and pd.notna(cr_yoy):
                items_evaluated += 1
                if cr_curr > cr_yoy:
                    f_score += 1
        
        # 7. 無增發新股 (需要 shares_outstanding 欄位)
        if 'shares_outstanding' in fin_data.columns and len(fin_data) > 4:
            shares_curr = fin_data.loc[0, 'shares_outstanding']
            shares_yoy = fin_data.loc[4, 'shares_outstanding']
            if shares_curr is not None and shares_yoy is not None and pd.notna(shares_curr) and pd.notna(shares_yoy):
                items_evaluated += 1
                if shares_curr <= shares_yoy:
                    f_score += 1
        
        # ═══════════════════════════════════════════════════════════════
        # 營運效率 (2 分)
        # ═══════════════════════════════════════════════════════════════
        
        # 8. 資產週轉率增加
        if all(v is not None and pd.notna(v) for v in [rev, ta, rev_yoy, ta_yoy]) and ta > 0 and ta_yoy > 0:
            items_evaluated += 1
            at_curr = rev / ta
            at_yoy = rev_yoy / ta_yoy
            if at_curr > at_yoy:
                f_score += 1
        
        # 9. 毛利率增加
        if 'gpm' in fin_data.columns and len(fin_data) > 4:
            gpm_curr = fin_data.loc[0, 'gpm']
            gpm_yoy = fin_data.loc[4, 'gpm']
            if gpm_curr is not None and gpm_yoy is not None and pd.notna(gpm_curr) and pd.notna(gpm_yoy):
                items_evaluated += 1
                if gpm_curr > gpm_yoy:
                    f_score += 1
        
        # 數據品質檢查：如果可評估項目少於 5 項，分數可能不可靠
        # 返回 tuple 讓調用者決定如何處理
        return f_score, items_evaluated
    
    except Exception:
        return None, 0


def calculate_hollow_profit_ratio(fin_data: pd.DataFrame) -> tuple[float | None, bool]:
    """
    計算虛胖獲利比（本業獲利佔比）
    
    公式：營業利益 (Operating Income) / 稅後淨利 (Net Income)
    
    解讀：
    - > 100%：可能有稅務效益或業外損失
    - 50-100%：正常
    - < 50%：獲利多來自業外，標記 Quality Warning
    
    Returns:
        (本業獲利比, 是否有品質警示)
    """
    try:
        if fin_data is None or len(fin_data) < 1:
            return None, False
        
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 使用 Operating Income 作為本業獲利指標
        op_income = fin_data.loc[0, 'op_income'] if 'op_income' in fin_data.columns else None
        net_income = fin_data.loc[0, 'net_income'] if 'net_income' in fin_data.columns else None
        
        if op_income is None or net_income is None:
            return None, False
        
        if pd.isna(op_income) or pd.isna(net_income) or net_income == 0:
            return None, False
        
        # 本業獲利比
        hollow_ratio = op_income / net_income
        
        # 品質警示：< 50% 表示業外佔比過高
        quality_warning = hollow_ratio < 0.5
        
        return hollow_ratio, quality_warning
    
    except Exception:
        return None, False


def calculate_roic(fin_data: pd.DataFrame) -> float | None:
    """
    計算 ROIC (Return on Invested Capital)
    
    簡化公式：EBIT (TTM) / Total Assets
    """
    try:
        if fin_data is None or len(fin_data) < 4:
            return None
        
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 使用營業利益作為 EBIT，加總近 4 季
        if 'op_income' not in fin_data.columns:
            return None
        
        ebit_ttm = fin_data.loc[0:3, 'op_income'].sum()
        
        if pd.isna(ebit_ttm):
            return None
        
        # 簡化計算：使用總資產替代
        ta = fin_data.loc[0, 'total_assets'] if 'total_assets' in fin_data.columns else None
        
        if ta is None or pd.isna(ta) or ta <= 0:
            return None
        
        roic = ebit_ttm / ta
        
        return roic
    
    except Exception:
        return None


def calculate_forensic_score(sloan: float | None, f_score: int | None, 
                              hollow_ratio: float | None, quality_warning: bool,
                              roic: float | None,
                              f_score_reliable: bool = True) -> tuple[int, dict]:
    """
    計算 Forensic Score (0-100)
    
    評分標準：
    - 基礎分：80 分
    - Sloan Ratio > 0.1：-15 分
    - Sloan Ratio > 0.2：額外 -10 分
    - F-Score < 4：-20 分（僅當數據可靠時）
    - F-Score >= 7：+10 分（僅當數據可靠時）
    - Quality Warning（虛胖）：-25 分
    - ROIC > 15%：+10 分
    
    修正版 v2.1:
    - 新增 f_score_reliable 參數
    - 當 F-Score 數據不可靠（評估項目<5項）時，不納入評分
    """
    score = 80  # 基礎分
    details = {'base': 80}
    warnings = []
    
    # 1. Sloan Ratio 懲罰
    if sloan is not None:
        if sloan > 0.2:
            score -= 25
            details['sloan_penalty'] = -25
            warnings.append("盈餘品質極差")
        elif sloan > 0.1:
            score -= 15
            details['sloan_penalty'] = -15
            warnings.append("盈餘品質差")
        elif sloan < 0.05:
            score += 5
            details['sloan_bonus'] = 5
        else:
            details['sloan_penalty'] = 0
    else:
        details['sloan_penalty'] = 0
    
    # 2. F-Score 評估 - 只有當數據可靠時才納入評分
    if f_score is not None and f_score_reliable:
        if f_score < 4:
            score -= 20
            details['fscore_penalty'] = -20
            warnings.append("財務實力弱")
        elif f_score >= 7:
            score += 10
            details['fscore_bonus'] = 10
        else:
            details['fscore_penalty'] = 0
            details['fscore_bonus'] = 0
    elif f_score is not None and not f_score_reliable:
        # F-Score 數據不可靠，給予警告但不扣分
        details['fscore_penalty'] = 0
        details['fscore_bonus'] = 0
        details['fscore_note'] = "數據不足，未納入評分"
        warnings.append("F-Score 數據不完整")
    else:
        details['fscore_penalty'] = 0
        details['fscore_bonus'] = 0
    
    # 3. 虛胖檢測
    if quality_warning:
        score -= 25
        details['hollow_penalty'] = -25
        warnings.append("虛胖獲利（業外佔比高）")
    else:
        details['hollow_penalty'] = 0
    
    # 4. ROIC 加分
    if roic is not None and roic > 0.15:
        score += 10
        details['roic_bonus'] = 10
    else:
        details['roic_bonus'] = 0
    
    # 確保分數在 0-100 範圍內
    score = max(0, min(100, score))
    
    details['warnings'] = warnings
    
    return score, details


def determine_forensic_verdict(forensic_score: int, sloan: float | None, 
                                 f_score: int | None, quality_warning: bool) -> str:
    """
    決定 Forensic 評級
    """
    if forensic_score >= 90:
        return "🏆 AAA：財務透明優質"
    elif forensic_score >= 80:
        return "⭐ AA：財務健康"
    elif forensic_score >= 70:
        return "✅ A：財務正常"
    elif forensic_score >= 60:
        return "⚠️ B：需留意"
    elif forensic_score >= 40:
        if quality_warning:
            return "🛑 C：虛胖警示"
        else:
            return "⚠️ C：財務風險"
    else:
        return "🚫 D：高風險"


def process_single_file(input_path: Path, output_path: Path):
    """
    處理單一檔案的分析
    """
    print(f"\n📂 讀取估值報告: {input_path}")
    try:
        input_df = pd.read_csv(input_path, encoding='utf-8-sig')
        print(f"✅ 共載入 {len(input_df)} 支股票")
    except Exception as e:
        print(f"❌ 讀取報告失敗: {e}")
        return
    
    print()
    print("-" * 70)
    print("🔍 開始執行財務取證分析（風險貼水版）...")
    print("-" * 70)
    
    results = []
    error_count = 0
    batch_size = 5
    
    for i, row in input_df.iterrows():
        ticker_tw = row['Ticker']
        ticker = ticker_tw.replace('.TW', '')
        company_name = row.get('Company_Name', '')
        
        # 繼承上游分數
        health_score = row.get('Health_Score', None)
        decision = row.get('Decision', '')
        
        idx = i + 1
        print(f"\n[{idx}/{len(input_df)}] 分析 {ticker} ({company_name})...")
        
        try:
            # 從本地資料庫載入財務報表
            fin_data = fetch_financials_from_database(ticker_tw, quarters=8)
            
            if fin_data is None or len(fin_data) < 4:
                print(f"    ⚠️  財務數據不足")
                results.append({
                    'Ticker': ticker_tw,
                    'Company_Name': company_name,
                    'Forensic_Score': None,
                    'Forensic_Verdict': "❓ 數據不足",
                    'Health_Score': health_score,
                    'Decision': decision
                })
                error_count += 1
                continue
            
            # 1. 計算 Sloan Ratio
            sloan = calculate_sloan_ratio(fin_data)
            
            # 2. 計算 F-Score（新版返回 tuple: score, items_evaluated）
            f_score_result = calculate_piotroski_f_score(fin_data)
            f_score, f_score_items = f_score_result if f_score_result[0] is not None else (None, 0)
            
            # F-Score 數據品質檢查：若可評估項目少於 5 項，標記為數據不足
            f_score_reliable = f_score_items >= 5
            
            # 3. 計算虛胖獲利比
            hollow_ratio, quality_warning = calculate_hollow_profit_ratio(fin_data)
            
            # 4. 計算 ROIC
            roic = calculate_roic(fin_data)
            
            # 5. 計算 Forensic Score
            forensic_score, score_details = calculate_forensic_score(
                sloan, f_score, hollow_ratio, quality_warning, roic,
                f_score_reliable=f_score_reliable
            )
            
            # 6. 決定評級
            forensic_verdict = determine_forensic_verdict(
                forensic_score, sloan, f_score, quality_warning
            )
            
            # 7. 儲存結果
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Forensic_Score': forensic_score,
                'Forensic_Verdict': forensic_verdict,
                'Sloan_Ratio': round(sloan, 4) if sloan is not None else None,
                'F_Score': f_score,
                'F_Score_Items': f_score_items,  # 新增：可評估項目數
                'F_Score_Reliable': f_score_reliable,  # 新增：數據是否可靠
                'Hollow_Ratio': round(hollow_ratio * 100, 1) if hollow_ratio is not None else None,
                'Quality_Warning': quality_warning,
                'ROIC': round(roic * 100, 2) if roic is not None else None,
                'Warnings': ', '.join(score_details.get('warnings', [])),
                'Score_Details': json.dumps(score_details, ensure_ascii=False),
                'Health_Score': health_score,
                'Decision': decision
            })
            
            # 顯示結果
            verdict_icon = "🏆" if forensic_score >= 90 else ("⭐" if forensic_score >= 80 else ("✅" if forensic_score >= 70 else "⚠️"))
            print(f"    {verdict_icon} Forensic Score: {forensic_score} | {forensic_verdict}")
            print(f"       Sloan: {sloan:.4f}" if sloan else "       Sloan: N/A")
            # 改進 F-Score 顯示，包含數據品質指標
            if f_score is not None:
                reliability_mark = "✓" if f_score_reliable else "⚠️"
                print(f"       F-Score: {f_score}/{f_score_items}項評估 {reliability_mark}")
            else:
                print(f"       F-Score: N/A")
            if quality_warning:
                print(f"       🛑 虛胖警示！本業獲利比: {hollow_ratio*100:.1f}%")
            if score_details.get('warnings'):
                print(f"       ⚠️  警示: {', '.join(score_details['warnings'])}")
        
        except Exception as e:
            print(f"    ❌ 分析錯誤: {str(e)}")
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Forensic_Score': None,
                'Forensic_Verdict': "❓ 數據不足",
                'Health_Score': health_score,
                'Decision': decision
            })
            error_count += 1
        
        # 分批暫停
        if idx % batch_size == 0 and idx < len(input_df):
            delay = random.uniform(1.5, 2.5)
            print(f"\n    ⏳ 已處理 {idx} 支股票，暫停 {delay:.1f} 秒...")
            time.sleep(delay)
    
    # 生成報告
    print()
    print("=" * 70)
    print("📈 財務取證分析完成！")
    print("=" * 70)
    
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"📁 報告已儲存: {output_path}")
    
    # 統計摘要
    print()
    print("-" * 70)
    print("📋 Forensic 評級統計:")
    print("-" * 70)
    
    if not results_df.empty and 'Forensic_Verdict' in results_df.columns:
        verdict_counts = results_df['Forensic_Verdict'].value_counts()
        for verdict, count in verdict_counts.items():
            print(f"   {verdict}: {count} 支")
    
    # 高風險警示
    print()
    print("-" * 70)
    print("🛑 財務風險警示清單 (Forensic Score < 60):")
    print("-" * 70)
    
    risk_df = results_df[
        (results_df['Forensic_Score'].notna()) & 
        (results_df['Forensic_Score'] < 60)
    ]
    
    if not risk_df.empty:
        for _, row in risk_df.iterrows():
            print(f"   {row['Ticker']} ({row['Company_Name']})")
            print(f"      Forensic Score: {row['Forensic_Score']} | {row['Forensic_Verdict']}")
            if row['Warnings']:
                print(f"      警示: {row['Warnings']}")
            print()
    else:
        print("   ✅ 無高風險標的")
    
    # Top 5 最透明
    print()
    print("-" * 70)
    print("🏆 財務最透明 Top 5:")
    print("-" * 70)
    
    top_df = results_df[results_df['Forensic_Score'].notna()].nlargest(5, 'Forensic_Score')
    for _, row in top_df.iterrows():
        print(f"   {row['Forensic_Score']} 分 | {row['Ticker']} ({row['Company_Name']})")
        print(f"      {row['Forensic_Verdict']}")
        print(f"      Sloan: {row['Sloan_Ratio']} | F-Score: {row['F_Score']}")
        print()
    
    print(f"❌ 數據異常/錯誤: {error_count} 支")


def main():
    """
    主程式
    """
    print("=" * 70)
    print("🔍 Forensic Analyzer V2 - 風險貼水機制")
    print("=" * 70)
    print("✨ 核心改進:")
    print("   1. Soft Penalty：異常扣分而非剔除")
    print("   2. Hollow Profit Detection：虛胖獲利偵測")
    print("   3. Forensic Score (0-100)：風險量化")
    print()
    print(f"📦 離線模式: {'✅ 啟用 (僅讀取本地資料庫)' if OFFLINE_MODE else '❌ 停用 (可能呼叫 API)'}")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    script_dir = Path(__file__).parent
    stock_pool_dir = script_dir.parent.parent.parent / "Stock_Pool"
    
    input_files = [
        "final_valuation_report_v2.csv",
        "hidden_gems_valuation_report_v2.csv",  # 隱藏寶石估值報告
        "final_valuation_report.csv"
    ]
    
    output_mapping = {
        "final_valuation_report_v2.csv": "institutional_forensic_report_v2.csv",
        "hidden_gems_valuation_report_v2.csv": "hidden_gems_forensic_report_v2.csv",
        "final_valuation_report.csv": "institutional_forensic_report_v2_from_v1.csv"
    }
    
    for input_file in input_files:
        input_path = stock_pool_dir / input_file
        
        if not input_path.exists():
            print(f"\n⚠️  檔案不存在，跳過: {input_file}")
            continue
        
        output_file = output_mapping.get(input_file, f"forensic_v2_{input_file}")
        output_path = stock_pool_dir / output_file
        
        print(f"\n{'='*70}")
        print(f"📄 處理檔案: {input_file}")
        print(f"{'='*70}")
        
        process_single_file(input_path, output_path)
    
    print()
    print(f"⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

