#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Checker V2.3 - 防禦型財務體檢（整合 6 因子升級版）
==========================================================
針對 structural_change_report_v2.csv 中的股票執行穩健的基本面體檢。

核心改進 (V2.3 多因子整合版)：
1. 🛡️ CCR 改用 TTM (近四季加總)：避免單季入帳時間差
2. 🚫 Sloan Ratio 核心防禦：財務虛胖 (>0.1) = 拒絕往來
3. 📦 存貨週轉天數 YoY 變化：去化能力惡化 = 營運風險

NEW V2.3 新增因子：
4. 📈 FCF Yield：自由現金流收益率（取代只看正負）
5. 📊 Margin Stability：盈利穩定度（OPM/GPM 波動）
6. 💰 Asset Growth：投資強度（避免「越擴越爛」）

Sloan Ratio 公式：
(Net Income - OCF) / Total Assets

Sloan Ratio 解讀：
- < 0: 🏆 優秀 (現金流強勁，OCF > Net Income)
- 0 ~ 0.05: ✅ 健康
- 0.05 ~ 0.10: ⚡ 留意
- > 0.10: ⚠️ 高風險 (財務虛胖，拒絕往來)
- > 0.20: 🚫 極高風險 (財報警示)

存貨週轉天數 (r611) 解讀：
- YoY 惡化 > 30天: 🚫 嚴重積壓 (-20分)
- YoY 惡化 > 15天: ⚠️ 積壓 (-15分)
- YoY 惡化 > 5天: ⚡ 微升 (-5分)
- YoY 改善 < -15天: 🏆 大幅改善 (+10分)
- YoY 改善 < -5天: ✅ 改善 (+5分)

數據來源：本地資料庫 (Stock_Pool/Database/)
- Operating Cash Flow: 營業活動現金流 (OCF)
- Net Income: 稅後淨利
- Total Assets: 總資產
- Inventory Days: 存貨週轉天數 (TEJ r611)

輸出檔案：
final_health_check_report_v2.csv: 含評分、風險等級的進階報告

執行方式：
  python health_checker_v2.py

必要前置步驟：
  1. 先執行 data_downloader.py 下載資料
  2. 確保 Stock_Pool/Database/ 有 JSON 資料
  3. 確保 Stock_Pool/structural_change_report_v2.csv 存在
"""

import pandas as pd
import numpy as np
import io
import time
import random
import json
from pathlib import Path
from datetime import datetime
from io import StringIO

# 添加 Data 資料夾到 Python 路徑
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))

# 使用 tej_tool 讀取本地資料庫
import tej_tool
from tej_tool import OFFLINE_MODE

# 引入新因子分析器
try:
    from factor_analyzer_v3 import (
        calculate_fcf_yield,
        calculate_margin_stability,
        calculate_asset_growth
    )
    FACTOR_V3_AVAILABLE = True
except ImportError:
    FACTOR_V3_AVAILABLE = False
    print("⚠️ factor_analyzer_v3 未找到，將使用舊版因子計算")

# 取得 loader 實例
loader = tej_tool.loader


def fetch_financials_from_database(ticker: str, quarters: int = 8) -> pd.DataFrame | None:
    """
    從本地資料庫載入財務報表數據
    
    Args:
        ticker: 股票代碼 (可含 .TW 或純數字)
        quarters: 抓取季數 (預設 8 季)
    
    Returns:
        包含 OCF, NetIncome, ICF, Inventory, Revenue 的 DataFrame
        欄位: mdate, ocf, net_income, icf, inventory, revenue
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 從 tej_tool 載入財務資料
        fin_raw, bs_raw, cf_raw = loader.get_financials(ticker_tw, quarters=quarters)
        
        # 檢查數據有效性
        if fin_raw is None or fin_raw.empty:
            return None
        if cf_raw is None or cf_raw.empty:
            return None
        
        # 轉換資料格式：從 (rows=metrics, cols=dates) 轉為 (rows=dates, cols=metrics)
        # 處理重複的日期欄位名稱 (如 2025-09-01, 2025-09-01.1)
        # 只取每個日期的第一個值
        unique_dates = []
        seen_dates = set()
        for col in fin_raw.columns:
            base_date = col.split('.')[0]  # 移除 .1, .2 等後綴
            if base_date not in seen_dates:
                unique_dates.append(col)
                seen_dates.add(base_date)
        
        # 建立合併的 DataFrame
        records = []
        for col in unique_dates[:quarters]:  # 只取需要的季數
            base_date = col.split('.')[0]
            try:
                record = {
                    'mdate': pd.to_datetime(base_date)
                }
                
                # 從 financials 取得 Net Income 和 Revenue
                if 'Net Income' in fin_raw.index:
                    record['net_income'] = fin_raw.loc['Net Income', col]
                elif 'Net Income Common Stockholders' in fin_raw.index:
                    record['net_income'] = fin_raw.loc['Net Income Common Stockholders', col]
                
                if 'Total Revenue' in fin_raw.index:
                    record['revenue'] = fin_raw.loc['Total Revenue', col]
                elif 'Revenue' in fin_raw.index:
                    record['revenue'] = fin_raw.loc['Revenue', col]
                
                # 從 balance_sheet 取得 Total Assets (Sloan Ratio 計算需要)
                if bs_raw is not None and not bs_raw.empty and col in bs_raw.columns:
                    if 'Total Assets' in bs_raw.index:
                        record['total_assets'] = bs_raw.loc['Total Assets', col]
                
                # 從 financials 取得 TEJ 已計算的指標
                if 'Inventory Days' in fin_raw.index:
                    record['inventory_days'] = fin_raw.loc['Inventory Days', col]  # r611 平均售貨天數
                if 'Days Sales Outstanding' in fin_raw.index:
                    record['dso'] = fin_raw.loc['Days Sales Outstanding', col]  # r609 平均收帳天數
                
                # 從 cashflow 取得 OCF 和 ICF
                if cf_raw is not None and not cf_raw.empty and col in cf_raw.columns:
                    if 'Operating Cash Flow' in cf_raw.index:
                        record['ocf'] = cf_raw.loc['Operating Cash Flow', col]
                    if 'Investing Cash Flow' in cf_raw.index:
                        record['icf'] = cf_raw.loc['Investing Cash Flow', col]
                
                records.append(record)
            except Exception as e:
                continue
        
        if not records:
            return None
        
        result_df = pd.DataFrame(records)
        
        # 檢查核心欄位 (OCF 和 NetIncome 是必要的)
        core_cols = ['ocf', 'net_income', 'mdate']
        missing_core = [col for col in core_cols if col not in result_df.columns]
        
        if missing_core:
            print(f"    ⚠️  缺少核心欄位: {missing_core}")
            return None
        
        # 按日期排序（最新在前）
        result_df = result_df.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        return result_df
    
    except Exception as e:
        print(f"    ❌ 資料庫載入錯誤: {e}")
        return None


def calculate_ccr_ttm(fin_data: pd.DataFrame) -> float | None:
    """
    計算 TTM 獲利含金量 (Cash Conversion Ratio - TTM)
    
    公式：CCR_TTM = sum(近4季 OCF) / sum(近4季 NetIncome)
    
    Args:
        fin_data: 財務報表 DataFrame (含 ocf, net_income 欄位)
    
    Returns:
        CCR_TTM 比率
    """
    try:
        if len(fin_data) < 4:
            return None
        
        # 確保按日期排序 (最新在前)
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 近 4 季 OCF 加總
        ocf_ttm = fin_data.loc[0:3, 'ocf'].sum()
        
        # 近 4 季淨利加總
        ni_ttm = fin_data.loc[0:3, 'net_income'].sum()
        
        # 檢查數據有效性
        if pd.isna(ocf_ttm) or pd.isna(ni_ttm) or ni_ttm == 0:
            return None
        
        # 淨利為負時，CCR 參考性低
        if ni_ttm < 0:
            return None
        
        ccr_ttm = ocf_ttm / ni_ttm
        
        return ccr_ttm
    
    except Exception as e:
        print(f"    ⚠️  計算 CCR_TTM 錯誤: {e}")
        return None


def calculate_inventory_days_risk(fin_data: pd.DataFrame) -> tuple[str, float | None, float | None]:
    """
    計算存貨週轉天數風險 (使用 TEJ 已計算好的 r611)
    
    比較本季與去年同季的存貨週轉天數 (YoY)
    
    Note: 部分產業（如半導體代工、金融、服務業）可能無存貨科目，返回 "不適用"
    
    Args:
        fin_data: 財務報表 DataFrame (含 inventory_days 欄位 = TEJ r611)
    
    Returns:
        (風險狀態, 天數變化, 當季天數)
    """
    try:
        if fin_data is None or len(fin_data) < 5:
            return "數據不足", None, None
        
        # 確保按日期排序
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 檢查存貨天數欄位 (TEJ r611)
        if 'inventory_days' not in fin_data.columns:
            return "不適用 (無存貨)", None, None
        
        # 取得本季存貨天數 (TEJ 已計算好)
        current_days = fin_data.loc[0, 'inventory_days']
        
        # 存貨天數為空或0表示該產業不適用
        if pd.isna(current_days) or current_days == 0:
            return "不適用 (無存貨)", None, None
        
        # 取得去年同季存貨天數 (YoY, index=4)
        yoy_days = fin_data.loc[4, 'inventory_days']
        
        if pd.isna(yoy_days) or yoy_days == 0:
            # 僅有當季資料，無法比較 YoY
            return f"當季 {current_days:.0f} 天 (無YoY)", None, current_days
        
        # 計算變化
        days_change = current_days - yoy_days
        
        # 判斷風險
        if days_change > 30:
            risk_status = "🚫 極高風險 (嚴重積壓)"
        elif days_change > 15:
            risk_status = "⚠️ 高風險 (積壓)"
        elif days_change > 5:
            risk_status = "⚡ 留意 (微升)"
        elif days_change < -15:
            risk_status = "🏆 優秀 (大幅改善)"
        elif days_change < -5:
            risk_status = "✅ 健康 (改善)"
        else:
            risk_status = "✅ 健康 (穩定)"
        
        return risk_status, days_change, current_days
    
    except Exception as e:
        print(f"    ⚠️  計算存貨風險錯誤: {e}")
        return "計算錯誤", None, None


def calculate_fcf_status(fin_data: pd.DataFrame) -> tuple[str, float | None]:
    """
    計算自由現金流狀態 (FCF = OCF - CapEx)
    
    Args:
        fin_data: 財務報表 DataFrame (含 ocf, icf 欄位)
    
    Returns:
        (FCF 狀態, FCF 值)
    """
    try:
        if len(fin_data) < 1:
            return "數據不足", None
        
        # 最新一季
        ocf = fin_data.loc[0, 'ocf']
        icf = fin_data.loc[0, 'icf'] if 'icf' in fin_data.columns else None  # 投資現金流（通常為負）
        
        if pd.isna(ocf):
            return "數據不足", None
        
        # ICF 為負表示支出 (CapEx)
        capex = abs(icf) if pd.notna(icf) and icf < 0 else 0
        
        # FCF = OCF - CapEx
        fcf = ocf - capex
        
        # 判斷狀態
        if fcf > 0:
            status = "✅ 正流入"
        elif capex > ocf * 1.5:
            status = "⚠️ 負流出 (擴產)"
        else:
            status = "🛑 負流出 (體質弱)"
        
        return status, fcf
    
    except Exception as e:
        print(f"    ⚠️  計算 FCF 錯誤: {e}")
        return "計算錯誤", None


def calculate_sloan_ratio(fin_data: pd.DataFrame) -> tuple[float | None, str]:
    """
    計算 Sloan Ratio (應計項比率)
    
    公式：Sloan Ratio = (Net Income - OCF) / Total Assets
    
    解讀：
    - < 0.05: 優秀（獲利主要來自現金）
    - 0.05 ~ 0.10: 正常
    - > 0.10: 警示（應計項過高，財務虛胖）
    - > 0.20: 危險（財務造假嫌疑）
    
    核心邏輯：
    Sloan Ratio 高 = 淨利遠大於 OCF = 帳面獲利虛胖 = 拒絕往來
    
    Args:
        fin_data: 財務報表 DataFrame (含 net_income, ocf, total_assets)
    
    Returns:
        (Sloan Ratio, 風險狀態)
    """
    try:
        if fin_data is None or len(fin_data) < 1:
            return None, "數據不足"
        
        # 取最新一季
        latest = fin_data.iloc[0]
        
        net_income = latest.get('net_income')
        ocf = latest.get('ocf')
        total_assets = latest.get('total_assets')
        
        # 必須有這三個欄位
        if pd.isna(net_income) or pd.isna(ocf) or pd.isna(total_assets):
            return None, "數據不足"
        
        if total_assets == 0:
            return None, "數據異常"
        
        # Sloan Ratio = (Net Income - OCF) / Total Assets
        sloan = (net_income - ocf) / total_assets
        
        # 判斷風險等級
        if sloan > 0.20:
            status = "🚫 極高風險 (財報警示)"
        elif sloan > 0.10:
            status = "⚠️ 高風險 (財務虛胖)"
        elif sloan > 0.05:
            status = "⚡ 留意"
        elif sloan >= 0:
            status = "✅ 健康"
        else:
            # 負值表示 OCF > Net Income，現金流品質優良
            status = "🏆 優秀 (現金流強勁)"
        
        return round(sloan, 4), status
    
    except Exception as e:
        print(f"    ⚠️  計算 Sloan Ratio 錯誤: {e}")
        return None, "計算錯誤"


def calculate_health_score(ccr_ttm: float | None, fcf: float | None, 
                           sloan_ratio: float | None, 
                           inv_days_change: float | None = None,
                           fcf_yield: float | None = None,
                           margin_stability: float | None = None,
                           asset_growth: float | None = None) -> tuple[int, dict]:
    """
    計算健康評分 (防禦型評分制) - V2.3 多因子整合版
    
    評分標準（滿分 130）：
    - 基礎分：50 分
    
    === 原有因子 ===
    - CCR_TTM > 0.8: +15 分
    - CCR_TTM > 1.0: +5 分 (額外)
    - Sloan Ratio > 0.20: -50 分 (極高風險)
    - Sloan Ratio > 0.10: -30 分 (高風險)
    - Sloan Ratio > 0.05: -10 分 (留意)
    - Sloan Ratio < 0: +10 分 (現金流優良)
    - 存貨天數惡化 > 30天: -15 分
    - 存貨天數惡化 > 15天: -10 分
    - 存貨天數惡化 > 5天: -5 分
    - 存貨天數改善 < -15天: +10 分
    - 存貨天數改善 < -5天: +5 分
    
    === NEW V2.3 新增因子 ===
    - FCF Yield > 8%: +15 分
    - FCF Yield > 5%: +10 分
    - FCF Yield > 2%: +5 分
    - FCF Yield < -5%: -10 分
    - Margin Stability >= 85: +10 分
    - Margin Stability >= 70: +5 分
    - Margin Stability < 40: -10 分
    - Asset Growth < 0%: +10 分 (謹慎經營)
    - Asset Growth < 10%: +5 分
    - Asset Growth > 40%: -15 分 (過度擴張)
    - Asset Growth > 20%: -8 分
    
    Args:
        ccr_ttm: TTM 獲利含金量
        fcf: 自由現金流
        sloan_ratio: Sloan Ratio (應計項比率)
        inv_days_change: 存貨週轉天數 YoY 變化
        fcf_yield: FCF Yield (新增)
        margin_stability: 盈利穩定度分數 (新增)
        asset_growth: 資產成長率 (新增)
    
    Returns:
        (總分, 詳細評分字典)
    """
    score = 50  # 基礎分
    details = {'base': 50}
    
    # 1. CCR_TTM 評分
    if ccr_ttm is not None:
        if ccr_ttm > 0.8:
            score += 15
            details['ccr_bonus'] = 15
            
            # 額外加分：CCR > 1.0 表示現金流優於獲利
            if ccr_ttm > 1.0:
                score += 5
                details['ccr_extra'] = 5
            else:
                details['ccr_extra'] = 0
        else:
            details['ccr_bonus'] = 0
            details['ccr_extra'] = 0
    else:
        details['ccr_bonus'] = 0
        details['ccr_extra'] = 0
    
    # 2. FCF Yield 評分 (取代舊版 FCF 正負判斷)
    if fcf_yield is not None:
        if fcf_yield > 8:
            score += 15
            details['fcf_yield_bonus'] = 15
        elif fcf_yield > 5:
            score += 10
            details['fcf_yield_bonus'] = 10
        elif fcf_yield > 2:
            score += 5
            details['fcf_yield_bonus'] = 5
        elif fcf_yield < -5:
            score -= 10
            details['fcf_yield_bonus'] = -10
        else:
            details['fcf_yield_bonus'] = 0
    elif fcf is not None and fcf > 0:
        # Fallback: 若無 FCF Yield 則用舊版邏輯
        score += 8
        details['fcf_yield_bonus'] = 8
    else:
        details['fcf_yield_bonus'] = 0
    
    # 3. Sloan Ratio 評分 (核心防禦指標)
    if sloan_ratio is not None:
        if sloan_ratio > 0.20:
            score -= 50
            details['sloan_penalty'] = -50
        elif sloan_ratio > 0.10:
            score -= 30
            details['sloan_penalty'] = -30
        elif sloan_ratio > 0.05:
            score -= 10
            details['sloan_penalty'] = -10
        elif sloan_ratio < 0:
            score += 10
            details['sloan_penalty'] = 10
        else:
            details['sloan_penalty'] = 0
    else:
        details['sloan_penalty'] = 0
    
    # 4. 存貨週轉天數評分 (YoY 變化)
    if inv_days_change is not None:
        if inv_days_change > 30:
            score -= 15
            details['inv_penalty'] = -15
        elif inv_days_change > 15:
            score -= 10
            details['inv_penalty'] = -10
        elif inv_days_change > 5:
            score -= 5
            details['inv_penalty'] = -5
        elif inv_days_change < -15:
            score += 10
            details['inv_penalty'] = 10
        elif inv_days_change < -5:
            score += 5
            details['inv_penalty'] = 5
        else:
            details['inv_penalty'] = 0
    else:
        details['inv_penalty'] = 0
    
    # 5. Margin Stability 評分 (NEW V2.3)
    if margin_stability is not None:
        if margin_stability >= 85:
            score += 10
            details['stability_bonus'] = 10
        elif margin_stability >= 70:
            score += 5
            details['stability_bonus'] = 5
        elif margin_stability < 40:
            score -= 10
            details['stability_bonus'] = -10
        else:
            details['stability_bonus'] = 0
    else:
        details['stability_bonus'] = 0
    
    # 6. Asset Growth 評分 (NEW V2.3, 反向因子)
    if asset_growth is not None:
        if asset_growth < 0:
            score += 10
            details['asset_growth_bonus'] = 10
        elif asset_growth < 10:
            score += 5
            details['asset_growth_bonus'] = 5
        elif asset_growth > 40:
            score -= 15
            details['asset_growth_bonus'] = -15
        elif asset_growth > 20:
            score -= 8
            details['asset_growth_bonus'] = -8
        else:
            details['asset_growth_bonus'] = 0
    else:
        details['asset_growth_bonus'] = 0
    
    return score, details


def determine_health_rating_v2(score: int, ccr_ttm: float | None, 
                                sloan_ratio: float | None) -> str:
    """
    根據評分與關鍵指標決定健康等級 - V2.1 Sloan 加權版
    
    Args:
        score: 綜合評分
        ccr_ttm: TTM 獲利含金量
        sloan_ratio: Sloan Ratio (應計項比率)
    
    Returns:
        健康等級標籤
    """
    # 檢查 Sloan Ratio 紅線條件 (最優先)
    if sloan_ratio is not None and sloan_ratio > 0.20:
        return "🚫 F級：拒絕往來 (財報警示)"
    
    if sloan_ratio is not None and sloan_ratio > 0.10:
        return "🛑 D級：高風險 (財務虛胖)"
    
    # 檢查分數條件
    if score < 40:
        return "🛑 D級：高風險"
    
    # 檢查雙重警示條件
    if sloan_ratio is not None and sloan_ratio > 0.05 and (ccr_ttm is None or ccr_ttm < 0.5):
        return "⚠️ C級：警示 (Sloan+CCR雙殺)"
    
    # 正常評級
    if score >= 90:
        return "🏆 S級：優質生"
    elif score >= 80:
        return "⭐ A級：質優生"
    elif score >= 70:
        return "✅ B級：正常"
    else:
        return "⚠️ C級：警示"


def process_single_file(input_path: Path, output_path: Path):
    """
    處理單一檔案的分析
    
    Args:
        input_path: 輸入檔案路徑 (structural_change_report_v2.csv)
        output_path: 輸出檔案路徑
    """
    print(f"\n📂 讀取分析清單: {input_path}")
    try:
        input_df = pd.read_csv(input_path, encoding='utf-8-sig')
        print(f"✅ 共載入 {len(input_df)} 支股票")
    except Exception as e:
        print(f"❌ 讀取清單失敗: {e}")
        return
    
    print()
    print("-" * 70)
    print("🏥 開始執行防禦型財務體檢...")
    print("-" * 70)
    
    results = []
    error_count = 0
    batch_size = 5
    
    for i, row in input_df.iterrows():
        ticker_tw = row['Ticker']
        ticker = ticker_tw.replace('.TW', '')
        company_name = row.get('Company_Name', '')
        # 支援 Pool Analyser 和 Shadow Gem Detector 兩種格式
        score_v1 = row.get('Score', row.get('Gem_Score', None))
        result_tag = row.get('Result_Tag', row.get('Gem_Type', ''))
        
        idx = i + 1
        print(f"\n[{idx}/{len(input_df)}] 體檢 {ticker} ({company_name})...")
        
        try:
            # 從本地資料庫載入財務報表
            fin_data = fetch_financials_from_database(ticker_tw, quarters=8)
            
            if fin_data is None or len(fin_data) < 4:
                print(f"    ⚠️  財務數據不足")
                results.append({
                    'Ticker': ticker_tw,
                    'Company_Name': company_name,
                    'Health_Score': None,
                    'Health_Rating': "D級：數據不足",
                    'Score_V1': score_v1,
                    'Result_Tag_V1': result_tag
                })
                error_count += 1
                continue
            
            # 1. 計算 CCR_TTM
            ccr_ttm = calculate_ccr_ttm(fin_data)
            
            # 2. 計算 Sloan Ratio (核心防禦指標)
            sloan_ratio, sloan_status = calculate_sloan_ratio(fin_data)
            
            # 3. 計算 FCF
            fcf_status, fcf_value = calculate_fcf_status(fin_data)
            
            # 4. 計算存貨週轉天數風險 (YoY)
            inv_risk, inv_days_change, inv_days_current = calculate_inventory_days_risk(fin_data)
            
            # 5. NEW V2.3: 計算新因子
            fcf_yield_val = None
            margin_stability_val = None
            asset_growth_val = None
            fcf_yield_status = None
            stability_status = None
            asset_growth_status = None
            
            if FACTOR_V3_AVAILABLE:
                # FCF Yield
                fcf_result = calculate_fcf_yield(ticker_tw)
                fcf_yield_val = fcf_result.get('fcf_yield')
                fcf_yield_status = fcf_result.get('fcf_yield_status')
                
                # Margin Stability
                stability_result = calculate_margin_stability(ticker_tw)
                margin_stability_val = stability_result.get('margin_stability_score')
                stability_status = stability_result.get('stability_status')
                
                # Asset Growth
                ag_result = calculate_asset_growth(ticker_tw)
                asset_growth_val = ag_result.get('asset_growth')
                asset_growth_status = ag_result.get('asset_growth_status')
            
            # 6. 計算健康評分 (V2.3 多因子整合版)
            health_score, score_details = calculate_health_score(
                ccr_ttm, fcf_value, sloan_ratio, inv_days_change,
                fcf_yield_val, margin_stability_val, asset_growth_val
            )
            
            # 7. 決定健康等級
            health_rating = determine_health_rating_v2(
                health_score, ccr_ttm, sloan_ratio
            )
            
            # 8. 儲存結果 (V2.3 擴展欄位)
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Health_Score': health_score,
                'CCR_TTM': round(ccr_ttm, 2) if ccr_ttm is not None else None,
                'FCF_Status': fcf_status,
                'FCF_Value': round(fcf_value / 1000, 2) if fcf_value is not None else None,  # 轉換為百萬
                # NEW V2.3 因子
                'FCF_Yield': fcf_yield_val,
                'FCF_Yield_Status': fcf_yield_status,
                'Margin_Stability': margin_stability_val,
                'Stability_Status': stability_status,
                'Asset_Growth': asset_growth_val,
                'Asset_Growth_Status': asset_growth_status,
                # 原有因子
                'Sloan_Ratio': sloan_ratio,
                'Sloan_Status': sloan_status,
                'Inv_Days': round(inv_days_current, 1) if inv_days_current is not None else None,
                'Inv_Days_Change': round(inv_days_change, 1) if inv_days_change is not None else None,
                'Inv_Risk': inv_risk,
                'Health_Rating': health_rating,
                'Score_Details': json.dumps(score_details, ensure_ascii=False),
                'Score_V1': score_v1,
                'Result_Tag_V1': result_tag
            })
            
            # 顯示結果
            if sloan_ratio is not None and sloan_ratio > 0.10:
                rating_icon = "🚫"  # 財務虛胖
            elif health_score >= 90:
                rating_icon = "🏆"
            elif health_score >= 80:
                rating_icon = "⭐"
            elif health_score >= 70:
                rating_icon = "✅"
            else:
                rating_icon = "⚠️"
            
            print(f"    {rating_icon} 健康評分: {health_score} 分 | {health_rating}")
            print(f"       CCR_TTM: {ccr_ttm:.2f}" if ccr_ttm else "       CCR_TTM: N/A")
            # 新版 FCF Yield 顯示
            if fcf_yield_val is not None:
                print(f"       FCF Yield: {fcf_yield_val}% | {fcf_yield_status}")
            else:
                print(f"       FCF: {fcf_status}")
            print(f"       Sloan Ratio: {sloan_ratio:.4f} | {sloan_status}" if sloan_ratio else f"       Sloan Ratio: N/A")
            # 新因子顯示
            if margin_stability_val is not None:
                print(f"       穩定度: {margin_stability_val} | {stability_status}")
            if asset_growth_val is not None:
                print(f"       資產成長: {asset_growth_val}% | {asset_growth_status}")
            if inv_days_current is not None:
                inv_change_str = f"{inv_days_change:+.1f}天" if inv_days_change is not None else "N/A"
                print(f"       存貨天數: {inv_days_current:.0f}天 (YoY: {inv_change_str}) | {inv_risk}")
            else:
                print(f"       存貨天數: {inv_risk}")
        
        except Exception as e:
            print(f"    ❌ 體檢錯誤: {str(e)}")
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Health_Rating': "D級：數據不足",
                'Score_V1': score_v1,
                'Result_Tag_V1': result_tag
            })
            error_count += 1
        
        # 分批暫停
        if idx % batch_size == 0 and idx < len(input_df):
            delay = random.uniform(1, 2)
            print(f"\n    ⏳ 已處理 {idx} 支股票，暫停 {delay:.1f} 秒...")
            time.sleep(delay)
    
    # 生成報告
    print()
    print("=" * 70)
    print("✅ 健康檢查完成！")
    print("=" * 70)
    
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"📁 報告已儲存: {output_path}")
    
    # 統計摘要
    print()
    print("-" * 70)
    print("📋 健康評級統計:")
    print("-" * 70)
    
    if not results_df.empty and 'Health_Rating' in results_df.columns:
        rating_counts = results_df['Health_Rating'].value_counts()
        for rating, count in rating_counts.items():
            print(f"   {rating}: {count} 支")
    
    # 高風險警示 (含 Sloan Ratio 過高者)
    print()
    print("-" * 70)
    print("🚫 財務虛胖警示清單 (Sloan Ratio > 0.10 或 Score < 40):")
    print("-" * 70)
    
    # 條件：Sloan > 0.10 或 Score < 40
    high_risk = results_df[
        ((results_df['Health_Score'].notna()) & (results_df['Health_Score'] < 40)) |
        ((results_df['Sloan_Ratio'].notna()) & (results_df['Sloan_Ratio'] > 0.10))
    ]
    
    if not high_risk.empty:
        for _, row in high_risk.iterrows():
            sloan = row.get('Sloan_Ratio')
            sloan_display = f"{sloan:.4f}" if pd.notna(sloan) else "N/A"
            print(f"   🚫 {row['Ticker']} ({row['Company_Name']})")
            print(f"      評分: {row['Health_Score']} | {row['Health_Rating']}")
            print(f"      Sloan Ratio: {sloan_display} | CCR_TTM: {row['CCR_TTM']}")
            print()
    else:
        print("   ✅ 無財務虛胖標的")
    
    print()
    print(f"❌ 數據異常/錯誤: {error_count} 支")


def main():
    """
    主程式
    """
    print("=" * 70)
    print("🏥 Health Checker V2.3 - 防禦型財務體檢 (多因子整合版)")
    print("=" * 70)
    print("✨ 核心改進:")
    print("   1. CCR 改用 TTM (避免單季波動)")
    print("   2. 🚫 Sloan Ratio 核心防禦：>0.1 = 財務虛胖 = 拒絕往來")
    print("   3. 📦 存貨天數 YoY 變化：惡化 = 去化能力變差 = 營運風險")
    print("   4. 評分制防禦機制 (Sloan -30/-50分, 存貨 -5/-15/-20分)")
    print()
    print("📊 NEW V2.3 新增因子:")
    print("   5. 📈 FCF Yield：自由現金流收益率（取代只看正負）")
    print("   6. 📊 Margin Stability：盈利穩定度（OPM/GPM 波動）")
    print("   7. 💰 Asset Growth：投資強度（避免「越擴越爛」）")
    print()
    print(f"🔧 Factor V3 模組: {'✅ 已載入' if FACTOR_V3_AVAILABLE else '❌ 未找到'}")
    print()
    print(f"📦 離線模式: {'✅ 啟用 (僅讀取本地資料庫)' if OFFLINE_MODE else '❌ 停用 (可能呼叫 API)'}")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    script_dir = Path(__file__).parent
    stock_pool_dir = script_dir.parent.parent.parent / "Stock_Pool"
    
    # 讀取 V2 版本的結構變化報告
    input_files = [
        "structural_change_report_v2.csv",
        "hidden_gems_report_v2.csv",  # 隱藏寶石也要體檢
        # 如果 V1 還存在也可以處理
        "structural_change_report.csv"
    ]
    
    output_mapping = {
        "structural_change_report_v2.csv": "final_health_check_report_v2.csv",
        "hidden_gems_report_v2.csv": "hidden_gems_health_check_report_v2.csv",
        "structural_change_report.csv": "final_health_check_report_v2_from_v1.csv"
    }
    
    for input_file in input_files:
        input_path = stock_pool_dir / input_file
        
        if not input_path.exists():
            print(f"⚠️  檔案不存在，跳過: {input_file}")
            continue
        
        output_file = output_mapping.get(input_file, f"health_check_v2_{input_file}")
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

