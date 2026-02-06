#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valuation Analyzer V2.3 - 市場狀態自適應估值系統（12-1 Momentum 升級版）
========================================================================
根據市場狀態（牛/熊市）動態調整估值標準，避免牛市買不到、熊市接刀。

核心改進：
1. 🏛️ Market Regime Detection：判斷大盤 vs MA200
2. 🚀 12-1 Momentum：取代 RS Ratio，更穩定的動能因子
3. 💡 Hybrid Valuation：EPS>0 用 PE / EPS<0 用 PB（抓轉機股）
4. 🎯 Decision Matrix：Strong Buy / Accumulate / Hold / Trim
5. 🎯 融資融券情緒因子整合

NEW V2.3 升級：
- 12-1 Momentum 取代原有 RS Ratio（去除短期噪音）
- 整合融資融券情緒因子
- 改善決策矩陣權重

資料源：本地資料庫 (Stock_Pool/Database/)
- 股價資料：從 price JSON 載入
- PE/PB：從 price JSON 的 per/pbr 欄位
- 使用 2330 (台積電) 作為大盤代理

輸出檔案：
final_valuation_report_v2.csv: 含市場狀態調整的估值報告

執行方式：
  python valuation_analyzer_v2.py

必要前置步驟：
  1. 先執行 data_downloader.py 下載資料
  2. 確保 Stock_Pool/Database/ 有 JSON 資料
  3. 確保 Stock_Pool/final_health_check_report_v2.csv 存在
"""

import pandas as pd
import numpy as np
import io
import time
import random
import json
from pathlib import Path
from datetime import datetime, timedelta

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
        calculate_momentum_12_1,
        calculate_margin_trading,
        calculate_max_drawdown
    )
    FACTOR_V3_AVAILABLE = True
except ImportError:
    FACTOR_V3_AVAILABLE = False
    print("⚠️ factor_analyzer_v3 未找到，將使用舊版 RS Ratio")

# 取得 loader 實例
loader = tej_tool.loader

# 大盤代理股票 (2330 台積電，因 0050 ETF 未在資料庫中)
BENCHMARK_TICKER = "2330.TW"


def fetch_benchmark_data(ticker: str = None, days: int = 250) -> pd.DataFrame | None:
    """
    從本地資料庫載入大盤代理數據（用於判斷市場狀態）
    使用 2330 (台積電) 作為大盤代理
    
    Args:
        ticker: 股票代碼（預設使用 BENCHMARK_TICKER）
        days: 需要的天數
    
    Returns:
        包含 mdate, close_d 的 DataFrame
    """
    try:
        ticker = ticker or BENCHMARK_TICKER
        
        # 從 tej_tool 載入股價資料
        price_df = loader.get_history(ticker, period_days=days)
        
        if price_df is None or price_df.empty:
            print(f"    ⚠️  找不到大盤代理數據 ({ticker})")
            return None
        
        # 確保有需要的欄位
        if 'close_d' not in price_df.columns:
            # 嘗試使用其他收盤價欄位
            close_col = None
            for col in ['close_d', 'Close', 'close', 'adj_close']:
                if col in price_df.columns:
                    close_col = col
                    break
            
            if close_col is None:
                print(f"    ⚠️  大盤數據缺少收盤價欄位")
                return None
            
            price_df['close_d'] = price_df[close_col]
        
        return price_df
    
    except Exception as e:
        print(f"    ❌ 載入大盤數據錯誤: {e}")
        return None


def fetch_stock_price_data(ticker: str, days: int = 750) -> pd.DataFrame | None:
    """
    從本地資料庫載入個股股價數據（含 PE, PB）
    
    Args:
        ticker: 股票代碼 (可含 .TW 或純數字)
        days: 需要的天數
    
    Returns:
        包含 mdate, close_d, per, pbr 的 DataFrame
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 從 tej_tool 載入股價資料
        price_df = loader.get_history(ticker_tw, period_days=days)
        
        if price_df is None or price_df.empty:
            return None
        
        return price_df
    
    except Exception:
        return None


def detect_market_regime(benchmark_data: pd.DataFrame) -> dict:
    """
    判斷市場狀態 (Market Regime)
    
    邏輯：
    - 大盤收盤價 > MA200 → 牛市 (Bull)
    - 大盤收盤價 < MA200 → 熊市 (Bear)
    
    Returns:
        {
            'regime': 'Bull' | 'Bear',
            'current_price': float,
            'ma200': float,
            'distance_pct': float (距離 MA200 的百分比)
        }
    """
    try:
        if benchmark_data is None or len(benchmark_data) < 200:
            return {'regime': 'Neutral', 'current_price': None, 'ma200': None, 'distance_pct': None}
        
        # 確保按日期升序排列（日期可能是 index 或欄位）
        if 'mdate' in benchmark_data.columns:
            benchmark_data = benchmark_data.sort_values('mdate', ascending=True).reset_index(drop=True)
        else:
            # 日期是 index
            benchmark_data = benchmark_data.sort_index(ascending=True)
        
        # 找到收盤價欄位
        close_col = None
        for col in ['close_d', 'Close', 'close', 'adj_close']:
            if col in benchmark_data.columns:
                close_col = col
                break
        
        if close_col is None:
            return {'regime': 'Neutral', 'current_price': None, 'ma200': None, 'distance_pct': None}
        
        # 計算 MA200
        prices = benchmark_data[close_col].dropna()
        if len(prices) < 200:
            return {'regime': 'Neutral', 'current_price': None, 'ma200': None, 'distance_pct': None}
        
        ma200 = prices.iloc[-200:].mean()
        current_price = prices.iloc[-1]
        
        # 計算距離百分比
        distance_pct = (current_price - ma200) / ma200 * 100
        
        # 判斷市場狀態
        if current_price > ma200:
            regime = 'Bull'
        else:
            regime = 'Bear'
        
        return {
            'regime': regime,
            'current_price': current_price,
            'ma200': ma200,
            'distance_pct': distance_pct
        }
    
    except Exception as e:
        print(f"    ⚠️  判斷市場狀態錯誤: {e}")
        return {'regime': 'Neutral', 'current_price': None, 'ma200': None, 'distance_pct': None}


def calculate_rs_ratio(stock_data: pd.DataFrame, benchmark_data: pd.DataFrame, 
                        period: int = 120) -> float | None:
    """
    計算 RS Ratio (相對強度比率)
    
    公式：RS Ratio = (1 + 個股報酬) / (1 + 大盤報酬)
    - > 1.0 表示強於大盤
    - < 1.0 表示弱於大盤
    """
    try:
        if stock_data is None or benchmark_data is None:
            return None
        
        if len(stock_data) < period or len(benchmark_data) < period:
            return None
        
        # 找到收盤價欄位
        def get_close_col(df):
            for col in ['close_d', 'Close', 'close', 'adj_close']:
                if col in df.columns:
                    return col
            return None
        
        stock_close_col = get_close_col(stock_data)
        bench_close_col = get_close_col(benchmark_data)
        
        if stock_close_col is None or bench_close_col is None:
            return None
        
        # 確保按日期排序（日期可能是 index）
        if 'mdate' in stock_data.columns:
            stock_data = stock_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        else:
            stock_data = stock_data.sort_index(ascending=False).reset_index(drop=True)
        
        if 'mdate' in benchmark_data.columns:
            benchmark_data = benchmark_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        else:
            benchmark_data = benchmark_data.sort_index(ascending=False).reset_index(drop=True)
        
        # 計算個股報酬
        stock_latest = stock_data.loc[0, stock_close_col]
        stock_past = stock_data.loc[min(period-1, len(stock_data)-1), stock_close_col]
        
        if pd.isna(stock_latest) or pd.isna(stock_past) or stock_past == 0:
            return None
        
        stock_return = (stock_latest / stock_past) - 1
        
        # 計算大盤報酬
        bench_latest = benchmark_data.loc[0, bench_close_col]
        bench_past = benchmark_data.loc[min(period-1, len(benchmark_data)-1), bench_close_col]
        
        if pd.isna(bench_latest) or pd.isna(bench_past) or bench_past == 0:
            return None
        
        bench_return = (bench_latest / bench_past) - 1
        
        # 計算 RS Ratio
        if (1 + bench_return) == 0:
            return None
        
        rs_ratio = (1 + stock_return) / (1 + bench_return)
        
        return rs_ratio
    
    except Exception:
        return None


def calculate_pe_percentile(stock_data: pd.DataFrame) -> tuple[float | None, float | None, bool]:
    """
    計算 PE Percentile（歷史 PE 區間位置）
    
    Returns:
        (當前 PE, PE Percentile, 是否有效 EPS)
    """
    try:
        if stock_data is None or 'per' not in stock_data.columns:
            return None, None, False
        
        # 按日期排序（日期可能是 index）
        if 'mdate' in stock_data.columns:
            stock_data = stock_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        else:
            stock_data = stock_data.sort_index(ascending=False).reset_index(drop=True)
        
        # 過濾有效 PE (排除負數和極端值)
        valid_pe = stock_data['per'].dropna()
        valid_pe = valid_pe[(valid_pe > 0) & (valid_pe < 200)]
        
        if len(valid_pe) < 30:
            return None, None, False
        
        current_pe = valid_pe.iloc[0]
        
        # 檢查是否有正 EPS
        has_positive_eps = current_pe > 0
        
        if not has_positive_eps:
            return current_pe, None, False
        
        # 計算百分位
        pe_min = valid_pe.min()
        pe_max = valid_pe.max()
        
        if pe_max - pe_min > 0:
            percentile = (current_pe - pe_min) / (pe_max - pe_min)
        else:
            percentile = 0.5
        
        percentile = max(0, min(1, percentile))
        
        return current_pe, percentile, True
    
    except Exception:
        return None, None, False


def calculate_pb_percentile(stock_data: pd.DataFrame) -> tuple[float | None, float | None]:
    """
    計算 PB Percentile（用於虧損股轉機評估）
    
    Returns:
        (當前 PB, PB Percentile)
    """
    try:
        if stock_data is None or 'pbr' not in stock_data.columns:
            return None, None
        
        # 按日期排序（日期可能是 index）
        if 'mdate' in stock_data.columns:
            stock_data = stock_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        else:
            stock_data = stock_data.sort_index(ascending=False).reset_index(drop=True)
        
        # 過濾有效 PB
        valid_pb = stock_data['pbr'].dropna()
        valid_pb = valid_pb[(valid_pb > 0) & (valid_pb < 50)]
        
        if len(valid_pb) < 30:
            return None, None
        
        current_pb = valid_pb.iloc[0]
        
        # 計算百分位
        pb_min = valid_pb.min()
        pb_max = valid_pb.max()
        
        if pb_max - pb_min > 0:
            percentile = (current_pb - pb_min) / (pb_max - pb_min)
        else:
            percentile = 0.5
        
        percentile = max(0, min(1, percentile))
        
        return current_pb, percentile
    
    except Exception:
        return None, None


def evaluate_rs_strength(rs_ratio: float | None, market_regime: str) -> tuple[str, bool]:
    """
    根據市場狀態評估 RS 強度（舊版，保留兼容）
    
    動態門檻：
    - 牛市：RS Ratio > 1.05 (強者恆強)
    - 熊市：RS Ratio > 0.95 (抗跌即可)
    
    Returns:
        (RS 狀態描述, 是否通過門檻)
    """
    if rs_ratio is None:
        return "N/A", False
    
    if market_regime == 'Bull':
        threshold = 1.05
        if rs_ratio > 1.10:
            return "🚀 極強 (Bull)", True
        elif rs_ratio > threshold:
            return "✅ 強勢 (Bull)", True
        elif rs_ratio > 1.0:
            return "➡️ 持平", False
        else:
            return "⚠️ 弱勢", False
    
    else:  # Bear or Neutral
        threshold = 0.95
        if rs_ratio > 1.05:
            return "🛡️ 極抗跌 (Bear)", True
        elif rs_ratio > threshold:
            return "✅ 抗跌 (Bear)", True
        elif rs_ratio > 0.90:
            return "➡️ 略跌", False
        else:
            return "🛑 重挫", False


def evaluate_momentum_12_1(momentum: float | None, market_regime: str) -> tuple[str, bool]:
    """
    根據市場狀態評估 12-1 Momentum（NEW V2.3）
    
    動態門檻：
    - 牛市：Momentum > 15% (強者恆強)
    - 熊市：Momentum > 0% (正向動能即可)
    
    Returns:
        (動能狀態描述, 是否通過門檻)
    """
    if momentum is None:
        return "N/A", False
    
    if market_regime == 'Bull':
        threshold = 15
        if momentum > 30:
            return "🚀 極強動能 (Bull)", True
        elif momentum > threshold:
            return "✅ 強勢動能 (Bull)", True
        elif momentum > 5:
            return "➡️ 正向", False
        elif momentum > -5:
            return "⚡ 中性", False
        else:
            return "⚠️ 弱勢", False
    
    else:  # Bear or Neutral
        threshold = 0
        if momentum > 15:
            return "🛡️ 極抗跌 (Bear)", True
        elif momentum > threshold:
            return "✅ 正向動能 (Bear)", True
        elif momentum > -10:
            return "➡️ 微弱", False
        else:
            return "🛑 弱勢", False


def evaluate_margin_sentiment(margin_score: int | None, sentiment: str | None) -> tuple[str, bool]:
    """
    評估融資融券情緒（NEW V2.3）
    
    Returns:
        (情緒描述, 是否為正面訊號)
    """
    if margin_score is None:
        return "N/A", False
    
    if margin_score >= 65:
        return f"✅ 籌碼正向 ({sentiment})", True
    elif margin_score >= 50:
        return f"➡️ 籌碼中性", False
    elif margin_score >= 35:
        return f"⚠️ 籌碼偏空", False
    else:
        return f"🛑 籌碼警示 ({sentiment})", False


def determine_decision(valuation_percentile: float | None, rs_pass: bool, 
                        market_regime: str, valuation_type: str,
                        momentum_pass: bool = False, margin_positive: bool = False) -> tuple[str, str]:
    """
    決策矩陣（V2.3 多因子整合版）
    
    Args:
        valuation_percentile: PE 或 PB 的百分位
        rs_pass: RS 是否通過門檻（舊版兼容）
        market_regime: 市場狀態 (Bull/Bear)
        valuation_type: 使用的估值類型 (PE/PB)
        momentum_pass: 12-1 Momentum 是否通過門檻（NEW）
        margin_positive: 融資融券情緒是否正向（NEW）
    
    Returns:
        (決策, 說明)
    """
    if valuation_percentile is None:
        return "Hold", "估值數據不足"
    
    # 使用新動能因子（優先）或舊 RS
    signal_pass = momentum_pass if FACTOR_V3_AVAILABLE else rs_pass
    signal_name = "動能" if FACTOR_V3_AVAILABLE else "RS"
    
    # 估值判斷
    is_undervalued = valuation_percentile < 0.3
    is_overvalued = valuation_percentile > 0.7
    is_fair = not is_undervalued and not is_overvalued
    
    # 多因子加成
    bullish_signals = sum([signal_pass, margin_positive])
    
    # 決策矩陣（V2.3 升級版）
    if market_regime == 'Bull':
        if is_undervalued and bullish_signals >= 2:
            return "🔥 Strong Buy", f"低估 + {signal_name}強 + 籌碼正向 ({valuation_type})"
        elif is_undervalued and signal_pass:
            return "🔥 Strong Buy", f"低估 + {signal_name}強 + 多頭 ({valuation_type})"
        elif is_undervalued and margin_positive:
            return "📈 Accumulate", f"低估 + 籌碼正向 ({valuation_type})"
        elif is_undervalued:
            return "📈 Accumulate", f"低估但{signal_name}未達標 ({valuation_type})"
        elif is_overvalued and not signal_pass:
            return "📉 Trim", f"高估 + {signal_name}轉弱 ({valuation_type})"
        elif is_overvalued and signal_pass:
            return "⚠️ Hold (Caution)", f"高估但動能強 ({valuation_type})"
        elif signal_pass:
            return "✅ Hold", f"估值合理 + {signal_name}強 ({valuation_type})"
        else:
            return "➡️ Hold", f"估值合理 ({valuation_type})"
    
    else:  # Bear
        if is_undervalued and bullish_signals >= 2:
            return "📊 Accumulate", f"低估 + 抗跌 + 籌碼正向 ({valuation_type})"
        elif is_undervalued and signal_pass:
            return "📊 Accumulate", f"低估 + 抗跌 + 空頭 ({valuation_type})"
        elif is_undervalued:
            return "👀 Watch", f"低估但不抗跌，等企穩 ({valuation_type})"
        elif is_overvalued:
            return "🛑 Trim", f"高估 + 熊市 ({valuation_type})"
        elif signal_pass:
            return "✅ Hold", f"抗跌標的 ({valuation_type})"
        else:
            return "⚠️ Reduce", f"不抗跌 ({valuation_type})"


def process_single_file(input_path: Path, output_path: Path, market_info: dict, benchmark_data: pd.DataFrame):
    """
    處理單一檔案的分析
    """
    print(f"\n📂 讀取健康檢查報告: {input_path}")
    try:
        input_df = pd.read_csv(input_path, encoding='utf-8-sig')
        print(f"✅ 共載入 {len(input_df)} 支股票")
    except Exception as e:
        print(f"❌ 讀取報告失敗: {e}")
        return
    
    print()
    print("-" * 70)
    if market_info['distance_pct'] is not None:
        print(f"📊 市場狀態: {market_info['regime']} ({market_info['distance_pct']:+.2f}% vs MA200)")
    else:
        print(f"📊 市場狀態: {market_info['regime']}")
    print("-" * 70)
    print("📈 開始執行市場自適應估值分析...")
    print("-" * 70)
    
    results = []
    error_count = 0
    batch_size = 5
    
    for i, row in input_df.iterrows():
        ticker_tw = row['Ticker']
        ticker = ticker_tw.replace('.TW', '')
        company_name = row.get('Company_Name', '')
        health_score = row.get('Health_Score', None)
        health_rating = row.get('Health_Rating', '')
        
        idx = i + 1
        print(f"\n[{idx}/{len(input_df)}] 分析 {ticker} ({company_name})...")
        
        try:
            # 1. 抓取股價數據
            stock_data = fetch_stock_price_data(ticker, days=750)
            
            if stock_data is None or len(stock_data) < 30:
                print(f"    ⚠️  股價數據不足")
                results.append({
                    'Ticker': ticker_tw,
                    'Company_Name': company_name,
                    'Decision': "Hold",
                    'Decision_Reason': "數據不足",
                    'Health_Score': health_score
                })
                error_count += 1
                continue
            
            # 2. 計算 RS Ratio (舊版兼容)
            rs_ratio = calculate_rs_ratio(stock_data, benchmark_data, period=120)
            rs_status, rs_pass = evaluate_rs_strength(rs_ratio, market_info['regime'])
            
            # 2.1 NEW V2.3: 計算 12-1 Momentum
            momentum_12_1 = None
            momentum_status = None
            momentum_pass = False
            margin_score = None
            margin_sentiment = None
            margin_positive = False
            max_drawdown = None
            current_drawdown = None
            
            if FACTOR_V3_AVAILABLE:
                # 12-1 Momentum
                mom_result = calculate_momentum_12_1(ticker_tw)
                momentum_12_1 = mom_result.get('momentum_12_1')
                momentum_status, momentum_pass = evaluate_momentum_12_1(momentum_12_1, market_info['regime'])
                
                # 融資融券情緒
                margin_result = calculate_margin_trading(ticker_tw)
                margin_score = margin_result.get('margin_score')
                margin_sentiment = margin_result.get('margin_sentiment')
                _, margin_positive = evaluate_margin_sentiment(margin_score, margin_sentiment)
                
                # Max Drawdown
                dd_result = calculate_max_drawdown(ticker_tw)
                max_drawdown = dd_result.get('max_drawdown')
                current_drawdown = dd_result.get('current_drawdown')
            
            # 3. 混合估值法
            current_pe, pe_percentile, has_positive_eps = calculate_pe_percentile(stock_data)
            current_pb, pb_percentile = calculate_pb_percentile(stock_data)
            
            # 決定使用哪種估值
            if has_positive_eps and pe_percentile is not None:
                valuation_type = "PE"
                valuation_percentile = pe_percentile
                valuation_value = current_pe
            else:
                valuation_type = "PB"
                valuation_percentile = pb_percentile
                valuation_value = current_pb
            
            # 4. 決策矩陣 (V2.3 多因子版)
            decision, decision_reason = determine_decision(
                valuation_percentile, rs_pass, market_info['regime'], valuation_type,
                momentum_pass=momentum_pass, margin_positive=margin_positive
            )
            
            # 5. 取得當前股價
            close_col = None
            for col in ['close_d', 'Close', 'close']:
                if col in stock_data.columns:
                    close_col = col
                    break
            current_price = stock_data.iloc[0][close_col] if close_col else None
            
            # 6. 儲存結果 (V2.3 擴展欄位)
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Current_Price': round(current_price, 2) if current_price else None,
                'Decision': decision,
                'Decision_Reason': decision_reason,
                'Market_Regime': market_info['regime'],
                # NEW V2.3: 12-1 Momentum
                'Momentum_12_1': momentum_12_1,
                'Momentum_Status': momentum_status,
                'Momentum_Pass': momentum_pass,
                # 舊版 RS (保留兼容)
                'RS_Ratio': round(rs_ratio, 3) if rs_ratio is not None else None,
                'RS_Status': rs_status,
                'RS_Pass': rs_pass,
                # NEW V2.3: 融資融券情緒
                'Margin_Score': margin_score,
                'Margin_Sentiment': margin_sentiment,
                'Margin_Positive': margin_positive,
                # NEW V2.3: Max Drawdown
                'Max_Drawdown': max_drawdown,
                'Current_Drawdown': current_drawdown,
                # 估值
                'Valuation_Type': valuation_type,
                'PE': round(current_pe, 2) if current_pe is not None else None,
                'PE_Percentile': round(pe_percentile * 100, 1) if pe_percentile is not None else None,
                'PB': round(current_pb, 2) if current_pb is not None else None,
                'PB_Percentile': round(pb_percentile * 100, 1) if pb_percentile is not None else None,
                'Health_Score': health_score,
                'Health_Rating': health_rating
            })
            
            # 顯示結果
            decision_icon = "🔥" if "Strong" in decision else ("📈" if "Accumulate" in decision else ("📉" if "Trim" in decision else "➡️"))
            print(f"    {decision_icon} {decision}")
            print(f"       {decision_reason}")
            # 新版動能顯示
            if momentum_12_1 is not None:
                print(f"       動能 12-1: {momentum_12_1:.1f}% ({momentum_status})")
            else:
                print(f"       RS: {rs_ratio:.3f} ({rs_status})" if rs_ratio else "       RS: N/A")
            # 融資融券
            if margin_score is not None:
                print(f"       籌碼: {margin_sentiment} (分數: {margin_score})")
            # MDD
            if max_drawdown is not None:
                print(f"       MDD: {max_drawdown:.1f}% | 當前回撤: {current_drawdown:.1f}%")
            # 估值
            print(f"       {valuation_type}: {valuation_value:.2f} (Percentile: {valuation_percentile*100:.1f}%)" if valuation_percentile else f"       {valuation_type}: N/A")
        
        except Exception as e:
            print(f"    ❌ 分析錯誤: {str(e)}")
            results.append({
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Decision': "Hold",
                'Decision_Reason': "分析錯誤",
                'Health_Score': health_score
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
    print("📈 估值分析完成！")
    print("=" * 70)
    
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"📁 報告已儲存: {output_path}")
    
    # 統計摘要
    print()
    print("-" * 70)
    print("📋 決策統計:")
    print("-" * 70)
    
    if not results_df.empty and 'Decision' in results_df.columns:
        decision_counts = results_df['Decision'].value_counts()
        for decision, count in decision_counts.items():
            print(f"   {decision}: {count} 支")
    
    # Strong Buy 清單
    print()
    print("-" * 70)
    print("🔥 Strong Buy / Accumulate 清單:")
    print("-" * 70)
    
    buy_df = results_df[
        results_df['Decision'].str.contains('Strong Buy|Accumulate', na=False)
    ]
    
    if not buy_df.empty:
        for _, row in buy_df.iterrows():
            print(f"   {row['Decision']} | {row['Ticker']} ({row['Company_Name']})")
            print(f"      {row['Decision_Reason']}")
            print(f"      RS: {row['RS_Ratio']} | {row['Valuation_Type']}: {row.get('PE', row.get('PB'))}")
            print()
    else:
        print("   （無符合條件的標的）")
    
    print(f"❌ 數據異常/錯誤: {error_count} 支")


def main():
    """
    主程式
    """
    print("=" * 70)
    print("💰 Valuation Analyzer V2.3 - 市場自適應估值系統（多因子升級版）")
    print("=" * 70)
    print("✨ 核心改進:")
    print("   1. Market Regime：判斷牛/熊市 (MA200)")
    print("   2. Hybrid Valuation：EPS>0 用 PE / EPS<0 用 PB")
    print("   3. Decision Matrix：Strong Buy / Accumulate / Trim")
    print()
    print("🚀 NEW V2.3 升級:")
    print("   4. 12-1 Momentum：取代 RS Ratio（去除短期噪音）")
    print("   5. 融資融券情緒因子：台股超有效的籌碼指標")
    print("   6. Max Drawdown：風控指標整合")
    print()
    print(f"📦 離線模式: {'✅ 啟用 (僅讀取本地資料庫)' if OFFLINE_MODE else '❌ 停用 (可能呼叫 API)'}")
    print(f"🔧 Factor V3 模組: {'✅ 已載入' if FACTOR_V3_AVAILABLE else '❌ 未找到 (使用舊版 RS)'}")
    print(f"📊 大盤代理: {BENCHMARK_TICKER} (因 0050 ETF 未在資料庫)")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 載入大盤代理數據並判斷市場狀態
    print("-" * 70)
    print("🏛️ 偵測市場狀態...")
    print("-" * 70)
    
    benchmark_data = fetch_benchmark_data(BENCHMARK_TICKER, days=250)
    market_info = detect_market_regime(benchmark_data)
    
    benchmark_name = BENCHMARK_TICKER.replace('.TW', '')
    if market_info['regime'] == 'Bull':
        print(f"📈 市場狀態: 🐂 牛市 (BULL)")
        print(f"   {benchmark_name} 收盤: {market_info['current_price']:.2f}")
        print(f"   MA200: {market_info['ma200']:.2f}")
        print(f"   距離 MA200: {market_info['distance_pct']:+.2f}%")
        print()
        print("   → RS 門檻: > 1.05 (強者恆強)")
    elif market_info['regime'] == 'Bear':
        print(f"📉 市場狀態: 🐻 熊市 (BEAR)")
        print(f"   {benchmark_name} 收盤: {market_info['current_price']:.2f}")
        print(f"   MA200: {market_info['ma200']:.2f}")
        print(f"   距離 MA200: {market_info['distance_pct']:+.2f}%")
        print()
        print("   → RS 門檻: > 0.95 (抗跌即可)")
    else:
        print("⚠️  市場狀態: 無法判斷（數據不足）")
    
    # 2. 設定路徑
    script_dir = Path(__file__).parent
    stock_pool_dir = script_dir.parent.parent.parent / "Stock_Pool"
    
    input_files = [
        "final_health_check_report_v2.csv",
        "hidden_gems_health_check_report_v2.csv",  # 隱藏寶石體檢報告
        "final_health_check_report.csv"
    ]
    
    output_mapping = {
        "final_health_check_report_v2.csv": "final_valuation_report_v2.csv",
        "hidden_gems_health_check_report_v2.csv": "hidden_gems_valuation_report_v2.csv",
        "final_health_check_report.csv": "final_valuation_report_v2_from_v1.csv"
    }
    
    # 3. 處理每個檔案
    for input_file in input_files:
        input_path = stock_pool_dir / input_file
        
        if not input_path.exists():
            print(f"\n⚠️  檔案不存在，跳過: {input_file}")
            continue
        
        output_file = output_mapping.get(input_file, f"valuation_v2_{input_file}")
        output_path = stock_pool_dir / output_file
        
        print(f"\n{'='*70}")
        print(f"📄 處理檔案: {input_file}")
        print(f"{'='*70}")
        
        process_single_file(input_path, output_path, market_info, benchmark_data)
    
    print()
    print(f"⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

