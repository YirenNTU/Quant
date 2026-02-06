#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shadow Gem Detector V2 - 隱藏寶石捕捉器（離線模式）
======================================================
找出真正的潛力股，從本地資料庫分析潛力指標。

核心指標：
1. 📊 營收加速度：從季度營收計算 YoY 加速
2. 📊 PSR Percentile：當前 PSR 在歷史區間的位置
3. 📈 RS 強度：相對大盤的強弱度
4. 🔬 研發動能：R&D 佔營收比變化

資料源：本地資料庫 (Stock_Pool/Database/)
- 股價資料：psr_tej, Close
- 財務資料：Revenue, Gross Profit, Research And Development
- 籌碼資料：qfii_ex, fund_ex, qfii_pct (需先執行 data_downloader.py)

輸出檔案：
hidden_gems_report_v2.csv: 隱藏寶石報告

執行方式：
  python shadow_gem_detector_v2.py

必要前置步驟：
  1. 先執行 data_downloader.py 下載資料
  2. 確保 Stock_Pool/Database/ 有 JSON 資料
"""

import pandas as pd
import numpy as np
import io
import json
import time
import random
from pathlib import Path
from datetime import datetime, timedelta

# 添加 Data 資料夾到 Python 路徑
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))

# 使用 tej_tool 讀取本地資料庫
import tej_tool
from tej_tool import OFFLINE_MODE

# 取得 loader 實例
loader = tej_tool.loader

# 大盤代理股票 (2330 台積電)
BENCHMARK_TICKER = "2330.TW"


def fetch_price_data(ticker: str, days: int = 750) -> pd.DataFrame | None:
    """
    從本地資料庫載入股價數據 (含 PSR)
    
    Args:
        ticker: 股票代碼 (可含 .TW 或純數字)
        days: 需要的天數
    
    Returns:
        股價 DataFrame
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        price_df = loader.get_history(ticker_tw, period_days=days)
        
        if price_df is None or price_df.empty:
            return None
        
        return price_df
    except Exception:
        return None


def fetch_financials(ticker: str, quarters: int = 8) -> pd.DataFrame | None:
    """
    從本地資料庫載入財務數據
    
    Args:
        ticker: 股票代碼 (可含 .TW 或純數字)
        quarters: 需要的季數
    
    Returns:
        財務報表 DataFrame (以日期為列)
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        fin_raw, bs_raw, cf_raw = loader.get_financials(ticker_tw, quarters=quarters)
        
        if fin_raw is None or fin_raw.empty:
            return None
        
        # 處理重複的日期欄位
        unique_dates = []
        seen_dates = set()
        for col in fin_raw.columns:
            base_date = col.split('.')[0]
            if base_date not in seen_dates:
                unique_dates.append(col)
                seen_dates.add(base_date)
        
        # 建立 DataFrame
        records = []
        for col in unique_dates[:quarters]:
            base_date = col.split('.')[0]
            try:
                record = {'mdate': pd.to_datetime(base_date)}
                
                # Revenue
                if 'Total Revenue' in fin_raw.index:
                    record['revenue'] = fin_raw.loc['Total Revenue', col]
                elif 'Revenue' in fin_raw.index:
                    record['revenue'] = fin_raw.loc['Revenue', col]
                
                # R&D
                if 'Research And Development' in fin_raw.index:
                    record['rd_expense'] = fin_raw.loc['Research And Development', col]
                
                # Gross Profit
                if 'Gross Profit' in fin_raw.index:
                    record['gross_profit'] = fin_raw.loc['Gross Profit', col]
                
                records.append(record)
            except Exception:
                continue
        
        if not records:
            return None
        
        result_df = pd.DataFrame(records)
        result_df = result_df.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        return result_df
    except Exception:
        return None


def calculate_revenue_acceleration(fin_data: pd.DataFrame) -> tuple[float | None, bool]:
    """
    計算營收加速度 (使用季度營收 YoY)
    
    公式：最新一季 YoY - 前一季 YoY（加速度）
    
    Args:
        fin_data: 財務報表 DataFrame (含 mdate, revenue)
    
    Returns:
        (加速度 %, 是否創 4 季新高)
    """
    try:
        if fin_data is None or len(fin_data) < 5:
            return None, False
        
        if 'revenue' not in fin_data.columns:
            return None, False
        
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 確保有足夠數據
        rev_0 = fin_data.loc[0, 'revenue']  # 最新一季
        rev_1 = fin_data.loc[1, 'revenue'] if len(fin_data) > 1 else None
        rev_4 = fin_data.loc[4, 'revenue'] if len(fin_data) > 4 else None  # 去年同季
        rev_5 = fin_data.loc[5, 'revenue'] if len(fin_data) > 5 else None
        
        if pd.isna(rev_0) or pd.isna(rev_4) or rev_4 == 0:
            return None, False
        
        # 最新一季 YoY
        yoy_0 = (rev_0 - rev_4) / abs(rev_4) * 100
        
        # 前一季 YoY
        if pd.notna(rev_1) and pd.notna(rev_5) and rev_5 != 0:
            yoy_1 = (rev_1 - rev_5) / abs(rev_5) * 100
            acceleration = yoy_0 - yoy_1  # 加速度
        else:
            acceleration = yoy_0  # 若無法計算加速度，返回 YoY
        
        # 檢查營收是否創 4 季新高
        latest_rev = rev_0
        past_max_rev = fin_data.loc[1:4, 'revenue'].max() if len(fin_data) > 4 else None
        is_new_high = latest_rev >= past_max_rev if pd.notna(latest_rev) and pd.notna(past_max_rev) else False
        
        return acceleration, is_new_high
    
    except Exception:
        return None, False


def calculate_chip_trend(chip_data: pd.DataFrame) -> dict | None:
    """
    計算籌碼趨勢
    
    分析最近 4 週的外資、投信買賣超趨勢
    
    Args:
        chip_data: 籌碼 DataFrame (from tej_tool.loader.get_chip)
                   需包含 qfii_ex, fund_ex 欄位
    
    Returns:
        籌碼趨勢字典
    """
    # 無籌碼資料時返回中性結果
    if chip_data is None or chip_data.empty:
        return {
            'qfii_net_4w': None,
            'fund_net_4w': None,
            'qfii_pct_change': None,
            'chip_trend': "➡️ N/A (無籌碼資料)"
        }
    
    try:
        # 確保有需要的欄位
        if 'qfii_ex' not in chip_data.columns or 'fund_ex' not in chip_data.columns:
            return {
                'qfii_net_4w': None,
                'fund_net_4w': None,
                'qfii_pct_change': None,
                'chip_trend': "➡️ N/A (欄位不足)"
            }
        
        # 計算近 4 週 (約 20 個交易日) 累計買賣超
        recent_data = chip_data.head(20)  # 假設資料已按日期降序排列
        
        qfii_net_4w = recent_data['qfii_ex'].sum()
        fund_net_4w = recent_data['fund_ex'].sum()
        
        # 計算外資持股變化 (如果有)
        qfii_pct_change = None
        if 'qfii_pct' in chip_data.columns and len(chip_data) >= 20:
            latest_pct = chip_data['qfii_pct'].iloc[0]
            older_pct = chip_data['qfii_pct'].iloc[min(19, len(chip_data)-1)]
            if pd.notna(latest_pct) and pd.notna(older_pct):
                qfii_pct_change = latest_pct - older_pct
        
        # 判斷趨勢
        if qfii_net_4w > 0 and fund_net_4w > 0:
            chip_trend = "🔥 雙多 (外資+投信買超)"
        elif qfii_net_4w > 0:
            chip_trend = "📈 外資買超"
        elif fund_net_4w > 0:
            chip_trend = "📊 投信買超"
        elif qfii_net_4w < 0 and fund_net_4w < 0:
            chip_trend = "⚠️ 雙空 (外資+投信賣超)"
        else:
            chip_trend = "➡️ 中性"
        
        return {
            'qfii_net_4w': int(qfii_net_4w) if pd.notna(qfii_net_4w) else None,
            'fund_net_4w': int(fund_net_4w) if pd.notna(fund_net_4w) else None,
            'qfii_pct_change': round(qfii_pct_change, 2) if qfii_pct_change else None,
            'chip_trend': chip_trend
        }
    
    except Exception as e:
        return {
            'qfii_net_4w': None,
            'fund_net_4w': None,
            'qfii_pct_change': None,
            'chip_trend': f"➡️ N/A (計算錯誤: {e})"
        }


def calculate_psr_percentile(price_data: pd.DataFrame) -> tuple[float | None, float | None]:
    """
    計算 PSR Percentile
    
    當前 PSR 在過去歷史區間的位置
    
    Args:
        price_data: 股價 DataFrame
    
    Returns:
        (當前 PSR, PSR Percentile)
    """
    try:
        if price_data is None or len(price_data) < 30:
            return None, None
        
        # 按日期排序（日期可能是 index）
        if 'mdate' in price_data.columns:
            price_data = price_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        else:
            price_data = price_data.sort_index(ascending=False).reset_index(drop=True)
        
        # 找到 PSR 欄位
        psr_col = None
        for col in ['psr_tej', 'PSR', 'psr']:
            if col in price_data.columns:
                psr_col = col
                break
        
        if psr_col is None:
            return None, None
        
        # 過濾有效 PSR
        valid_psr = price_data[psr_col].dropna()
        valid_psr = valid_psr[valid_psr > 0]
        
        if len(valid_psr) < 30:
            return None, None
        
        current_psr = valid_psr.iloc[0]
        
        # 計算百分位
        psr_min = valid_psr.min()
        psr_max = valid_psr.max()
        
        if psr_max - psr_min > 0:
            percentile = (current_psr - psr_min) / (psr_max - psr_min)
        else:
            percentile = 0.5
        
        percentile = max(0, min(1, percentile))
        
        return current_psr, percentile
    
    except Exception:
        return None, None


def calculate_relative_strength(price_data: pd.DataFrame, benchmark_data: pd.DataFrame = None) -> float | None:
    """
    計算相對強度 (RS vs 大盤)
    
    使用本地資料庫的價格數據計算
    
    Args:
        price_data: 個股價格 DataFrame
        benchmark_data: 大盤價格 DataFrame
    
    Returns:
        RS 比率（個股報酬 - 大盤報酬）
    """
    try:
        if price_data is None or len(price_data) < 120:
            return None
        
        # 找到收盤價欄位
        close_col = None
        for col in ['close_d', 'Close', 'close']:
            if col in price_data.columns:
                close_col = col
                break
        
        if close_col is None:
            return None
        
        # 按日期排序
        if 'mdate' in price_data.columns:
            price_data = price_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        else:
            price_data = price_data.sort_index(ascending=False).reset_index(drop=True)
        
        # 取 120 天報酬
        latest_price = price_data.loc[0, close_col]
        past_price = price_data.loc[min(119, len(price_data)-1), close_col]
        
        if pd.isna(latest_price) or pd.isna(past_price) or past_price == 0:
            return None
        
        stock_return = (latest_price / past_price) - 1
        
        # 計算大盤報酬
        if benchmark_data is not None and len(benchmark_data) >= 120:
            # 找到大盤收盤價欄位
            bench_close_col = None
            for col in ['close_d', 'Close', 'close']:
                if col in benchmark_data.columns:
                    bench_close_col = col
                    break
            
            if bench_close_col is not None:
                if 'mdate' in benchmark_data.columns:
                    benchmark_data = benchmark_data.sort_values('mdate', ascending=False).reset_index(drop=True)
                else:
                    benchmark_data = benchmark_data.sort_index(ascending=False).reset_index(drop=True)
                
                benchmark_latest = benchmark_data.loc[0, bench_close_col]
                benchmark_past = benchmark_data.loc[min(119, len(benchmark_data)-1), bench_close_col]
                
                if pd.notna(benchmark_latest) and pd.notna(benchmark_past) and benchmark_past != 0:
                    benchmark_return = (benchmark_latest / benchmark_past) - 1
                    rs = stock_return - benchmark_return
                    return rs
        
        return stock_return  # 若無法取得大盤，返回絕對報酬
    
    except Exception:
        return None


def calculate_rd_momentum(fin_data: pd.DataFrame) -> float | None:
    """
    計算研發費用佔營收比變化
    
    Args:
        fin_data: 財務報表 DataFrame (含 rd_expense, revenue)
    
    Returns:
        R&D 動能（最新佔比 - 過去平均佔比）
    """
    try:
        if fin_data is None or len(fin_data) < 4:
            return None
        
        # 檢查研發費用欄位
        if 'rd_expense' not in fin_data.columns or 'revenue' not in fin_data.columns:
            return None
        
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        # 最新季 R&D / 營收
        latest_rd = fin_data.loc[0, 'rd_expense']
        latest_rev = fin_data.loc[0, 'revenue']
        
        if pd.isna(latest_rd) or pd.isna(latest_rev) or latest_rev == 0:
            return None
        
        latest_ratio = latest_rd / latest_rev
        
        # 過去 4 季平均
        past_ratios = []
        for i in range(1, min(5, len(fin_data))):
            rd = fin_data.loc[i, 'rd_expense']
            rev = fin_data.loc[i, 'revenue']
            if pd.notna(rd) and pd.notna(rev) and rev != 0:
                past_ratios.append(rd / rev)
        
        if not past_ratios:
            return None
        
        past_avg = np.mean(past_ratios)
        momentum = latest_ratio - past_avg
        
        return momentum
    
    except Exception:
        return None


def calculate_gem_score(rev_acc: float | None, is_new_high: bool,
                         chip_data: dict | None, rs: float | None,
                         psr_percentile: float | None, rd_momentum: float | None) -> tuple[int, dict]:
    """
    計算隱藏寶石評分
    
    評分標準：
    - 基礎分：40 分
    - 營收加速 (YoY 擴大) > 5%：+30 分
    - 大戶籌碼增加（外資+投信買超）：+20 分
    - RS 強度 > 10%：+20 分
    - 研發費用佔比增加：+10 分
    - 營收創新高 + PSR < 20%：+10 分 (價值確認)
    """
    score = 40  # 基礎分
    details = {'base': 40}
    
    # 1. 營收加速 (+30)
    if rev_acc is not None and rev_acc > 5:
        score += 30
        details['rev_acc_bonus'] = 30
    elif rev_acc is not None and rev_acc > 0:
        score += 15
        details['rev_acc_bonus'] = 15
    else:
        details['rev_acc_bonus'] = 0
    
    # 2. 籌碼集中 (+20) - 離線模式不支援
    if chip_data is not None:
        qfii_net = chip_data.get('qfii_net_4w')
        fund_net = chip_data.get('fund_net_4w')
        
        # 確保 qfii_net 和 fund_net 不是 None
        qfii_net = qfii_net if qfii_net is not None else 0
        fund_net = fund_net if fund_net is not None else 0
        
        if qfii_net > 0 and fund_net > 0:
            score += 20
            details['chip_bonus'] = 20
        elif qfii_net > 0 or fund_net > 0:
            score += 10
            details['chip_bonus'] = 10
        else:
            details['chip_bonus'] = 0
    else:
        details['chip_bonus'] = 0
    
    # 3. RS 強度 (+20)
    if rs is not None:
        if rs > 0.1:  # 強於大盤 10%+
            score += 20
            details['rs_bonus'] = 20
        elif rs > 0:  # 強於大盤
            score += 10
            details['rs_bonus'] = 10
        else:
            details['rs_bonus'] = 0
    else:
        details['rs_bonus'] = 0
    
    # 4. 研發動能 (+10)
    if rd_momentum is not None and rd_momentum > 0:
        score += 10
        details['rd_bonus'] = 10
    else:
        details['rd_bonus'] = 0
    
    # 5. 價值確認：營收新高 + PSR 低檔 (+10)
    if is_new_high and psr_percentile is not None and psr_percentile < 0.2:
        score += 10
        details['value_bonus'] = 10
    else:
        details['value_bonus'] = 0
    
    return score, details


def determine_gem_type_v2(score: int, rev_acc: float | None, chip_trend: str | None,
                           is_new_high: bool, psr_percentile: float | None) -> str:
    """
    判斷隱藏寶石類型
    """
    if score >= 100:
        return "💎💎💎 SSS級隱藏寶石"
    elif score >= 80:
        if chip_trend and "雙多" in chip_trend:
            return "💎💎 S級：法人共識潛力股"
        elif is_new_high and psr_percentile and psr_percentile < 0.3:
            return "💎💎 S級：價值轉機股"
        else:
            return "💎💎 S級：強勢潛力股"
    elif score >= 60:
        if rev_acc and rev_acc > 10:
            return "💎 A級：營收爆發型"
        elif chip_trend and ("買超" in chip_trend or "雙多" in chip_trend):
            return "💎 A級：籌碼卡位型"
        else:
            return "💎 A級：潛力關注"
    elif score >= 50:
        return "⭐ B級：觀察名單"
    else:
        return "ℹ️  C級：持續追蹤"


def main():
    """
    主程式
    """
    print("=" * 70)
    print("💎 Shadow Gem Detector V2 - 隱藏寶石捕捉器（離線模式）")
    print("=" * 70)
    print("✨ 核心指標:")
    print("   1. 營收加速度：季度 YoY 加速")
    print("   2. PSR Percentile：歷史區間位置")
    print("   3. RS 強度：相對大盤強弱")
    print("   4. 研發動能：R&D 佔營收比變化")
    print()
    print(f"📦 離線模式: {'✅ 啟用 (僅讀取本地資料庫)' if OFFLINE_MODE else '❌ 停用 (可能呼叫 API)'}")
    print(f"📊 大盤代理: {BENCHMARK_TICKER}")
    print("🎯 籌碼資料: 若已下載則自動載入 (需先執行 data_downloader.py)")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 設定路徑
    script_dir = Path(__file__).parent
    list_json_path = script_dir.parent.parent.parent / "Stock_Pool" / "list.json"
    structural_path = script_dir.parent.parent.parent / "Stock_Pool" / "structural_change_report_v2.csv"
    output_path = script_dir.parent.parent.parent / "Stock_Pool" / "hidden_gems_report_v2.csv"
    
    # 讀取股票清單
    print(f"📂 讀取股票清單: {list_json_path}")
    try:
        with open(list_json_path, 'r', encoding='utf-8') as f:
            company_dict = json.load(f)
        tickers = [ticker.replace('.TW', '') for ticker in company_dict.keys()]
        print(f"✅ 共載入 {len(tickers)} 支股票")
    except Exception as e:
        print(f"❌ 讀取清單失敗: {e}")
        return
    
    # 讀取已有的結構變化報告以排除已入選股票
    existing_elite = set()
    try:
        if structural_path.exists():
            structural_df = pd.read_csv(structural_path, encoding='utf-8-sig')
            existing_elite = set(structural_df['Ticker'].str.replace('.TW', '').tolist())
            print(f"📊 現有 Elite 名單: {len(existing_elite)} 支股票")
    except Exception:
        pass
    
    # 載入大盤資料（用於計算 RS）
    print(f"\n📈 載入大盤代理數據 ({BENCHMARK_TICKER})...")
    benchmark_data = fetch_price_data(BENCHMARK_TICKER, days=750)
    if benchmark_data is not None:
        print(f"   ✅ 大盤資料載入成功 ({len(benchmark_data)} 筆)")
    else:
        print(f"   ⚠️  大盤資料載入失敗，RS 將使用絕對報酬")
    
    print()
    print("-" * 70)
    print("🔍 開始掃描隱藏寶石...")
    print("-" * 70)
    
    results = []
    error_count = 0
    batch_size = 10
    
    for i, ticker in enumerate(tickers, 1):
        ticker_tw = f"{ticker}.TW"
        company_name = company_dict.get(ticker_tw, '')
        
        print(f"\n[{i}/{len(tickers)}] 掃描 {ticker} ({company_name})...")
        
        try:
            # 1. 載入財務數據並計算營收加速度
            fin_data = fetch_financials(ticker_tw, quarters=8)
            rev_acc, is_new_high = calculate_revenue_acceleration(fin_data)
            
            # 2. 籌碼數據 (從本地資料庫或 API)
            chip_data = loader.get_chip(ticker_tw, days=30)
            chip_metrics = calculate_chip_trend(chip_data)
            
            # 3. 載入股價數據 (含 PSR)
            price_data = fetch_price_data(ticker_tw, days=750)
            current_psr, psr_percentile = calculate_psr_percentile(price_data)
            
            # 4. 計算 RS（與大盤比較）
            rs = calculate_relative_strength(price_data, benchmark_data)
            
            # 5. 計算研發動能
            rd_momentum = calculate_rd_momentum(fin_data)
            
            # 6. 計算評分
            gem_score, score_details = calculate_gem_score(
                rev_acc, is_new_high, chip_metrics, rs, psr_percentile, rd_momentum
            )
            
            # 7. 判斷類型
            chip_trend = chip_metrics.get('chip_trend', '') if chip_metrics else ''
            gem_type = determine_gem_type_v2(gem_score, rev_acc, chip_trend, is_new_high, psr_percentile)
            
            # 8. 儲存結果
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Gem_Score': gem_score,
                'Gem_Type': gem_type,
                'Rev_Acc': round(rev_acc, 2) if rev_acc is not None else None,
                'Rev_New_High': is_new_high,
                'Chip_Trend': chip_trend,
                'QFII_Net_4W': chip_metrics.get('qfii_net_4w') if chip_metrics else None,
                'Fund_Net_4W': chip_metrics.get('fund_net_4w') if chip_metrics else None,
                'RS': round(rs * 100, 2) if rs is not None else None,
                'PSR': round(current_psr, 2) if current_psr is not None else None,
                'PSR_Percentile': round(psr_percentile * 100, 1) if psr_percentile is not None else None,
                'RD_Momentum': round(rd_momentum * 100, 2) if rd_momentum is not None else None,
                'In_Elite_List': ticker in existing_elite,
                'Score_Details': json.dumps(score_details, ensure_ascii=False)
            })
            
            # 顯示結果
            icon = "💎" if gem_score >= 60 else ("⭐" if gem_score >= 50 else "ℹ️")
            print(f"    {icon} 評分: {gem_score} 分 | {gem_type}")
            print(f"       營收加速: {rev_acc:.1f}%" if rev_acc else "       營收加速: N/A")
            print(f"       籌碼: {chip_trend}")
            print(f"       RS: {rs*100:.1f}%" if rs else "       RS: N/A")
        
        except Exception as e:
            print(f"    ❌ 處理錯誤: {str(e)}")
            error_count += 1
        
        # 分批暫停
        if i % batch_size == 0 and i < len(tickers):
            delay = random.uniform(1.5, 2.5)
            print(f"\n    ⏳ 已處理 {i} 支股票，暫停 {delay:.1f} 秒...")
            time.sleep(delay)
    
    # 生成報告
    print()
    print("=" * 70)
    print("📈 掃描完成！")
    print("=" * 70)
    
    results_df = pd.DataFrame(results)
    
    # 過濾隱藏寶石 (Score >= 50 且不在 Elite 名單)
    gems_df = results_df[
        (results_df['Gem_Score'] >= 50) & 
        (~results_df['In_Elite_List'])
    ].copy()
    
    # 按分數排序
    gems_df = gems_df.sort_values('Gem_Score', ascending=False)
    
    # 儲存
    gems_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"📁 隱藏寶石報告已儲存: {output_path}")
    print(f"   （共 {len(gems_df)} 支符合條件的潛力股）")
    
    # 統計
    print()
    print("-" * 70)
    print("📋 寶石評級統計:")
    print("-" * 70)
    
    if not gems_df.empty:
        type_counts = gems_df['Gem_Type'].value_counts()
        for gem_type, count in type_counts.items():
            print(f"   {gem_type}: {count} 支")
    
    # Top 10 展示
    print()
    print("-" * 70)
    print("💎 Top 10 隱藏寶石:")
    print("-" * 70)
    
    for idx, row in gems_df.head(10).iterrows():
        print(f"\n   {row['Gem_Score']} 分 | {row['Ticker']} ({row['Company_Name']})")
        print(f"      {row['Gem_Type']}")
        print(f"      營收加速: {row['Rev_Acc']}% | RS: {row['RS']}%")
        print(f"      籌碼: {row['Chip_Trend']} | PSR: {row['PSR']} ({row['PSR_Percentile']}%)")
    
    print()
    print(f"❌ 數據異常/錯誤: {error_count} 支")
    print(f"⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

