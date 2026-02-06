#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Analyzer V3 - 多因子量化分析系統
==============================================
整合學術研究與台股實戰因子，提供更完整的量化分析框架。

核心因子 (6 大類)：
1. 📈 FCF Yield：自由現金流收益率（取代單純 FCF 正負）
2. 🚀 12-1 Momentum：去除短期噪音的動能因子
3. 📊 Margin Stability：盈利穩定度（OPM/GPM 波動）
4. 💰 Asset Growth：投資強度（避免「越擴越爛」）
5. 📉 Max Drawdown：最大回撤（風控指標）
6. 🎯 Margin Trading：融資融券情緒因子（台股超實用）

資料來源：
- 本地資料庫 (Stock_Pool/Database/*.json)
- 籌碼資料：chip (long_t, short_t, s_l_pct)
- 財務資料：financials, balance_sheet, cashflow
- 股價資料：price

執行方式：
  python factor_analyzer_v3.py

必要前置步驟：
  1. 先執行 data_downloader.py 下載資料
  2. 確保 Stock_Pool/Database/ 有 JSON 資料
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime
from io import StringIO
from glob import glob

# 添加 Data 資料夾到 Python 路徑
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))

# 使用 tej_tool 讀取本地資料庫
import tej_tool
from tej_tool import OFFLINE_MODE

# 取得 loader 實例
loader = tej_tool.loader

# ==========================================
# 本地資料庫設定
# ==========================================
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Stock_Pool", "Database")


# ==========================================
# Factor 1: FCF Yield
# ==========================================
def calculate_fcf_yield(ticker: str) -> dict:
    """
    計算 FCF Yield（自由現金流收益率）
    
    公式：FCF Yield = FCF_TTM / Market Cap
           FCF = OCF - CapEx (使用 ICF 絕對值近似)
    
    優點：比單純看 FCF 正負更能量化價值
    
    Returns:
        {
            'fcf_yield': float (百分比),
            'fcf_ttm': float (千元),
            'market_cap': float (千元),
            'fcf_yield_status': str
        }
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 取得財務資料
        fin_raw, bs_raw, cf_raw = loader.get_financials(ticker_tw, quarters=8)
        
        if cf_raw is None or cf_raw.empty:
            return {'fcf_yield': None, 'fcf_ttm': None, 'market_cap': None, 'fcf_yield_status': "數據不足"}
        
        # 取得股價資料（含 mktcap）
        price_df = loader.get_history(ticker_tw, period_days=30)
        
        if price_df is None or price_df.empty:
            return {'fcf_yield': None, 'fcf_ttm': None, 'market_cap': None, 'fcf_yield_status': "數據不足"}
        
        # 提取 OCF 和 ICF（近 4 季）
        # 處理重複日期欄位
        unique_dates = []
        seen_dates = set()
        for col in cf_raw.columns:
            base_date = col.split('.')[0]
            if base_date not in seen_dates:
                unique_dates.append(col)
                seen_dates.add(base_date)
        
        if len(unique_dates) < 4:
            return {'fcf_yield': None, 'fcf_ttm': None, 'market_cap': None, 'fcf_yield_status': "季數不足"}
        
        # 計算 TTM OCF 和 CapEx
        ocf_ttm = 0
        icf_ttm = 0
        
        for col in unique_dates[:4]:
            if 'Operating Cash Flow' in cf_raw.index:
                ocf_val = cf_raw.loc['Operating Cash Flow', col]
                if pd.notna(ocf_val):
                    ocf_ttm += float(ocf_val)
            
            if 'Investing Cash Flow' in cf_raw.index:
                icf_val = cf_raw.loc['Investing Cash Flow', col]
                if pd.notna(icf_val):
                    icf_ttm += float(icf_val)
        
        # CapEx ≈ |ICF| (投資現金流通常為負)
        capex_ttm = abs(icf_ttm) if icf_ttm < 0 else 0
        
        # FCF = OCF - CapEx
        fcf_ttm = ocf_ttm - capex_ttm
        
        # 取得 Market Cap
        mktcap = None
        if 'mktcap' in price_df.columns:
            mktcap = price_df['mktcap'].iloc[-1]
        elif 'mktcap' in price_df.columns:
            mktcap = price_df['mktcap'].dropna().iloc[-1] if not price_df['mktcap'].dropna().empty else None
        
        if mktcap is None or mktcap == 0:
            return {'fcf_yield': None, 'fcf_ttm': fcf_ttm, 'market_cap': None, 'fcf_yield_status': "無市值資料"}
        
        # FCF Yield = FCF / Market Cap (轉換為百分比)
        fcf_yield = (fcf_ttm / mktcap) * 100
        
        # 判斷狀態
        if fcf_yield > 8:
            status = "🏆 極佳 (>8%)"
        elif fcf_yield > 5:
            status = "✅ 優良 (5-8%)"
        elif fcf_yield > 2:
            status = "✅ 健康 (2-5%)"
        elif fcf_yield > 0:
            status = "⚡ 偏低 (0-2%)"
        elif fcf_yield > -5:
            status = "⚠️ 負值 (-5~0%)"
        else:
            status = "🚫 警示 (<-5%)"
        
        return {
            'fcf_yield': round(fcf_yield, 2),
            'fcf_ttm': round(fcf_ttm / 1000, 2),  # 轉為百萬
            'market_cap': round(mktcap / 1000, 2),  # 轉為百萬
            'fcf_yield_status': status
        }
    
    except Exception as e:
        return {'fcf_yield': None, 'fcf_ttm': None, 'market_cap': None, 'fcf_yield_status': f"計算錯誤: {e}"}


# ==========================================
# Factor 2: 12-1 Momentum
# ==========================================
def calculate_momentum_12_1(ticker: str) -> dict:
    """
    計算 12-1 動能因子
    
    公式：過去 12 個月報酬 - 最近 1 個月報酬
    
    原理：
    - 避免短期 mean reversion（最近 1 月漲多回檔）
    - 保留中期動能效應
    - 學術研究證實有效（Jegadeesh & Titman）
    
    Returns:
        {
            'momentum_12_1': float (百分比),
            'return_12m': float,
            'return_1m': float,
            'momentum_status': str
        }
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 取得股價資料（至少需要 252+21 交易日 ≈ 13 個月）
        price_df = loader.get_history(ticker_tw, period_days=400)
        
        if price_df is None or price_df.empty:
            return {'momentum_12_1': None, 'return_12m': None, 'return_1m': None, 'momentum_status': "數據不足"}
        
        # 找到收盤價欄位
        close_col = None
        for col in ['Close', 'close_d', 'close']:
            if col in price_df.columns:
                close_col = col
                break
        
        if close_col is None:
            return {'momentum_12_1': None, 'return_12m': None, 'return_1m': None, 'momentum_status': "無收盤價"}
        
        # 確保按日期排序（最新在後）
        if hasattr(price_df.index, 'sort_values'):
            price_df = price_df.sort_index(ascending=True)
        
        prices = price_df[close_col].dropna()
        
        if len(prices) < 252:  # 至少需要 1 年資料
            return {'momentum_12_1': None, 'return_12m': None, 'return_1m': None, 'momentum_status': "數據不足 (<252日)"}
        
        # 計算報酬
        current_price = prices.iloc[-1]
        price_1m_ago = prices.iloc[-22] if len(prices) >= 22 else prices.iloc[0]
        price_12m_ago = prices.iloc[-252] if len(prices) >= 252 else prices.iloc[0]
        
        if price_12m_ago == 0 or price_1m_ago == 0:
            return {'momentum_12_1': None, 'return_12m': None, 'return_1m': None, 'momentum_status': "價格為零"}
        
        # 12 個月報酬
        return_12m = (current_price / price_12m_ago - 1) * 100
        
        # 最近 1 個月報酬
        return_1m = (current_price / price_1m_ago - 1) * 100
        
        # 12-1 動能
        momentum_12_1 = return_12m - return_1m
        
        # 判斷狀態
        if momentum_12_1 > 30:
            status = "🚀 極強動能 (>30%)"
        elif momentum_12_1 > 15:
            status = "🔥 強勢 (15-30%)"
        elif momentum_12_1 > 5:
            status = "✅ 正向 (5-15%)"
        elif momentum_12_1 > -5:
            status = "➡️ 中性 (-5~5%)"
        elif momentum_12_1 > -15:
            status = "⚠️ 弱勢 (-15~-5%)"
        else:
            status = "🛑 極弱 (<-15%)"
        
        return {
            'momentum_12_1': round(momentum_12_1, 2),
            'return_12m': round(return_12m, 2),
            'return_1m': round(return_1m, 2),
            'momentum_status': status
        }
    
    except Exception as e:
        return {'momentum_12_1': None, 'return_12m': None, 'return_1m': None, 'momentum_status': f"計算錯誤: {e}"}


# ==========================================
# Factor 3: Margin Stability
# ==========================================
def calculate_margin_stability(ticker: str) -> dict:
    """
    計算盈利穩定度（Margin Stability）
    
    公式：
    - GPM_Volatility = std(GPM) over 12 quarters
    - OPM_Volatility = std(OPM) over 12 quarters
    - Stability Score = 100 - (GPM_Vol + OPM_Vol) * 2
    
    原理：
    - 低波動的利潤率 = 穩定的競爭優勢
    - 高波動 = 週期性強或護城河弱
    
    Returns:
        {
            'gpm_volatility': float,
            'opm_volatility': float,
            'margin_stability_score': float,
            'stability_status': str
        }
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 取得財務資料（需要 12 季）
        fin_raw, bs_raw, cf_raw = loader.get_financials(ticker_tw, quarters=16)
        
        if fin_raw is None or fin_raw.empty:
            return {'gpm_volatility': None, 'opm_volatility': None, 
                    'margin_stability_score': None, 'stability_status': "數據不足"}
        
        # 處理重複日期欄位
        unique_dates = []
        seen_dates = set()
        for col in fin_raw.columns:
            base_date = col.split('.')[0]
            if base_date not in seen_dates:
                unique_dates.append(col)
                seen_dates.add(base_date)
        
        if len(unique_dates) < 8:  # 至少需要 8 季
            return {'gpm_volatility': None, 'opm_volatility': None,
                    'margin_stability_score': None, 'stability_status': "季數不足"}
        
        # 提取 Revenue, Gross Profit, Operating Income
        gpm_list = []
        opm_list = []
        
        for col in unique_dates[:12]:  # 最多用 12 季
            try:
                revenue = None
                gross_profit = None
                operating_income = None
                
                if 'Total Revenue' in fin_raw.index:
                    revenue = fin_raw.loc['Total Revenue', col]
                elif 'Revenue' in fin_raw.index:
                    revenue = fin_raw.loc['Revenue', col]
                
                if 'Gross Profit' in fin_raw.index:
                    gross_profit = fin_raw.loc['Gross Profit', col]
                
                if 'Operating Income' in fin_raw.index:
                    operating_income = fin_raw.loc['Operating Income', col]
                elif 'EBIT' in fin_raw.index:
                    operating_income = fin_raw.loc['EBIT', col]
                
                if pd.notna(revenue) and revenue != 0:
                    if pd.notna(gross_profit):
                        gpm_list.append(float(gross_profit) / float(revenue) * 100)
                    if pd.notna(operating_income):
                        opm_list.append(float(operating_income) / float(revenue) * 100)
            except Exception:
                continue
        
        if len(gpm_list) < 6 or len(opm_list) < 6:
            return {'gpm_volatility': None, 'opm_volatility': None,
                    'margin_stability_score': None, 'stability_status': "有效季數不足"}
        
        # 計算波動率（標準差）
        gpm_volatility = np.std(gpm_list)
        opm_volatility = np.std(opm_list)
        
        # 穩定度分數 (100 - 波動懲罰)
        # 波動率每 1% 扣 2 分
        stability_score = 100 - (gpm_volatility + opm_volatility) * 2
        stability_score = max(0, min(100, stability_score))  # 限制在 0-100
        
        # 判斷狀態
        if stability_score >= 85:
            status = "🏆 極穩定 (≥85)"
        elif stability_score >= 70:
            status = "✅ 穩定 (70-85)"
        elif stability_score >= 55:
            status = "⚡ 中等 (55-70)"
        elif stability_score >= 40:
            status = "⚠️ 波動大 (40-55)"
        else:
            status = "🛑 高波動 (<40)"
        
        return {
            'gpm_volatility': round(gpm_volatility, 2),
            'opm_volatility': round(opm_volatility, 2),
            'margin_stability_score': round(stability_score, 1),
            'stability_status': status
        }
    
    except Exception as e:
        return {'gpm_volatility': None, 'opm_volatility': None,
                'margin_stability_score': None, 'stability_status': f"計算錯誤: {e}"}


# ==========================================
# Factor 4: Asset Growth
# ==========================================
def calculate_asset_growth(ticker: str) -> dict:
    """
    計算 Asset Growth（資產成長率）
    
    公式：Asset Growth = (Total Assets_t - Total Assets_t-4) / Total Assets_t-4
    
    原理（Novy-Marx 研究）：
    - 高資產擴張 = 未來報酬較差（過度投資、資本錯配）
    - 低資產成長 = 謹慎經營、資本效率高
    - 負向因子：Asset Growth 越低越好
    
    Returns:
        {
            'asset_growth': float (百分比),
            'total_assets_current': float,
            'total_assets_yoy': float,
            'asset_growth_status': str
        }
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 取得資產負債表
        fin_raw, bs_raw, cf_raw = loader.get_financials(ticker_tw, quarters=8)
        
        if bs_raw is None or bs_raw.empty:
            return {'asset_growth': None, 'total_assets_current': None,
                    'total_assets_yoy': None, 'asset_growth_status': "數據不足"}
        
        # 處理重複日期欄位
        unique_dates = []
        seen_dates = set()
        for col in bs_raw.columns:
            base_date = col.split('.')[0]
            if base_date not in seen_dates:
                unique_dates.append(col)
                seen_dates.add(base_date)
        
        if len(unique_dates) < 5:  # 需要至少 5 季（當季 + 去年同季）
            return {'asset_growth': None, 'total_assets_current': None,
                    'total_assets_yoy': None, 'asset_growth_status': "季數不足"}
        
        # 取得 Total Assets
        if 'Total Assets' not in bs_raw.index:
            return {'asset_growth': None, 'total_assets_current': None,
                    'total_assets_yoy': None, 'asset_growth_status': "無資產資料"}
        
        # 當季資產
        current_assets = bs_raw.loc['Total Assets', unique_dates[0]]
        
        # 去年同季資產 (index 4)
        yoy_assets = bs_raw.loc['Total Assets', unique_dates[4]] if len(unique_dates) > 4 else None
        
        if pd.isna(current_assets) or pd.isna(yoy_assets) or yoy_assets == 0:
            return {'asset_growth': None, 'total_assets_current': float(current_assets) if pd.notna(current_assets) else None,
                    'total_assets_yoy': None, 'asset_growth_status': "YoY 資料不足"}
        
        # 計算 Asset Growth
        asset_growth = (float(current_assets) - float(yoy_assets)) / abs(float(yoy_assets)) * 100
        
        # 判斷狀態（反向因子：越低越好）
        if asset_growth < 0:
            status = "🏆 收縮 (<0%，謹慎經營)"
        elif asset_growth < 10:
            status = "✅ 穩健 (0-10%)"
        elif asset_growth < 20:
            status = "⚡ 適度擴張 (10-20%)"
        elif asset_growth < 40:
            status = "⚠️ 高速擴張 (20-40%)"
        else:
            status = "🚫 過度擴張 (>40%)"
        
        return {
            'asset_growth': round(asset_growth, 2),
            'total_assets_current': round(float(current_assets) / 1000, 2),  # 轉為百萬
            'total_assets_yoy': round(float(yoy_assets) / 1000, 2),
            'asset_growth_status': status
        }
    
    except Exception as e:
        return {'asset_growth': None, 'total_assets_current': None,
                'total_assets_yoy': None, 'asset_growth_status': f"計算錯誤: {e}"}


# ==========================================
# Factor 5: Max Drawdown
# ==========================================
def calculate_max_drawdown(ticker: str, lookback_days: int = 252) -> dict:
    """
    計算最大回撤（Max Drawdown）
    
    公式：MDD = (Peak - Trough) / Peak
    
    用途：
    - 風控指標，反映下檔風險
    - 低 MDD = 抗跌能力強
    
    Returns:
        {
            'max_drawdown': float (百分比，負值),
            'drawdown_period_days': int,
            'current_drawdown': float,
            'drawdown_status': str
        }
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 取得股價資料
        price_df = loader.get_history(ticker_tw, period_days=lookback_days + 30)
        
        if price_df is None or price_df.empty:
            return {'max_drawdown': None, 'drawdown_period_days': None,
                    'current_drawdown': None, 'drawdown_status': "數據不足"}
        
        # 找到收盤價欄位
        close_col = None
        for col in ['Close', 'close_d', 'close']:
            if col in price_df.columns:
                close_col = col
                break
        
        if close_col is None:
            return {'max_drawdown': None, 'drawdown_period_days': None,
                    'current_drawdown': None, 'drawdown_status': "無收盤價"}
        
        # 確保按日期排序
        if hasattr(price_df.index, 'sort_values'):
            price_df = price_df.sort_index(ascending=True)
        
        prices = price_df[close_col].dropna()
        
        if len(prices) < 60:  # 至少需要 60 天
            return {'max_drawdown': None, 'drawdown_period_days': None,
                    'current_drawdown': None, 'drawdown_status': "數據不足 (<60日)"}
        
        # 計算累積最高點
        rolling_max = prices.expanding().max()
        
        # 計算回撤
        drawdowns = (prices - rolling_max) / rolling_max * 100
        
        # 最大回撤
        max_drawdown = drawdowns.min()
        
        # 找出最大回撤發生的位置和持續天數
        mdd_idx = drawdowns.idxmin()
        peak_idx = rolling_max.loc[:mdd_idx].idxmax() if isinstance(mdd_idx, (pd.Timestamp, str)) else None
        
        # 計算回撤持續天數
        try:
            if peak_idx is not None and mdd_idx is not None:
                drawdown_period = (pd.Timestamp(mdd_idx) - pd.Timestamp(peak_idx)).days
            else:
                drawdown_period = None
        except Exception:
            drawdown_period = None
        
        # 當前回撤
        current_drawdown = drawdowns.iloc[-1]
        
        # 判斷狀態
        if max_drawdown > -10:
            status = "🏆 低波動 (MDD>-10%)"
        elif max_drawdown > -20:
            status = "✅ 穩健 (-20~-10%)"
        elif max_drawdown > -30:
            status = "⚡ 中等 (-30~-20%)"
        elif max_drawdown > -50:
            status = "⚠️ 高波動 (-50~-30%)"
        else:
            status = "🛑 極高風險 (MDD<-50%)"
        
        return {
            'max_drawdown': round(max_drawdown, 2),
            'drawdown_period_days': drawdown_period,
            'current_drawdown': round(current_drawdown, 2),
            'drawdown_status': status
        }
    
    except Exception as e:
        return {'max_drawdown': None, 'drawdown_period_days': None,
                'current_drawdown': None, 'drawdown_status': f"計算錯誤: {e}"}


# ==========================================
# Factor 6: Margin Trading (融資融券)
# ==========================================
def calculate_margin_trading(ticker: str) -> dict:
    """
    計算融資融券情緒因子
    
    核心指標：
    1. 融資餘額變化率 (4週)
    2. 融券餘額變化率 (4週)
    3. 券資比 (short/long ratio)
    4. 融資使用率變化
    
    原理（台股特有）：
    - 融資增加 = 散戶看多（逆向指標）
    - 融券增加 = 放空壓力（軋空潛力）
    - 券資比高 = 軋空機會
    
    Returns:
        {
            'margin_long_change': float (融資變化%),
            'margin_short_change': float (融券變化%),
            'short_long_ratio': float (券資比),
            'margin_sentiment': str,
            'margin_score': int
        }
    """
    try:
        ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
        
        # 取得籌碼資料
        chip_df = loader.get_chip(ticker_tw, days=60)
        
        if chip_df is None or chip_df.empty:
            return {'margin_long_change': None, 'margin_short_change': None,
                    'short_long_ratio': None, 'margin_sentiment': "無籌碼資料", 'margin_score': 50}
        
        # 確保有需要的欄位
        required_cols = ['long_t', 'short_t']
        if not all(col in chip_df.columns for col in required_cols):
            return {'margin_long_change': None, 'margin_short_change': None,
                    'short_long_ratio': None, 'margin_sentiment': "欄位不足", 'margin_score': 50}
        
        # 按日期排序（最新在前）
        if 'mdate' in chip_df.columns:
            chip_df = chip_df.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        if len(chip_df) < 20:  # 至少需要 4 週資料
            return {'margin_long_change': None, 'margin_short_change': None,
                    'short_long_ratio': None, 'margin_sentiment': "數據不足", 'margin_score': 50}
        
        # 最新資料
        latest_long = chip_df.loc[0, 'long_t']
        latest_short = chip_df.loc[0, 'short_t']
        
        # 4 週前資料 (約 20 個交易日)
        idx_4w = min(19, len(chip_df) - 1)
        past_long = chip_df.loc[idx_4w, 'long_t']
        past_short = chip_df.loc[idx_4w, 'short_t']
        
        # 計算變化率
        margin_long_change = None
        margin_short_change = None
        
        if pd.notna(latest_long) and pd.notna(past_long) and past_long != 0:
            margin_long_change = (latest_long - past_long) / abs(past_long) * 100
        
        if pd.notna(latest_short) and pd.notna(past_short) and past_short != 0:
            margin_short_change = (latest_short - past_short) / abs(past_short) * 100
        elif pd.notna(latest_short) and past_short == 0 and latest_short > 0:
            margin_short_change = 100  # 從 0 增加
        
        # 券資比
        short_long_ratio = None
        if 's_l_pct' in chip_df.columns:
            short_long_ratio = chip_df.loc[0, 's_l_pct']
        elif pd.notna(latest_long) and latest_long > 0 and pd.notna(latest_short):
            short_long_ratio = latest_short / latest_long * 100
        
        # 計算情緒分數 (基礎 50 分)
        score = 50
        sentiment_parts = []
        
        # 融資變化評分（逆向指標）
        if margin_long_change is not None:
            if margin_long_change > 20:
                score -= 15  # 融資大增 = 散戶瘋狂 = 警示
                sentiment_parts.append("融資大增⚠️")
            elif margin_long_change > 10:
                score -= 8
                sentiment_parts.append("融資增加")
            elif margin_long_change < -20:
                score += 15  # 融資大減 = 散戶出場 = 機會
                sentiment_parts.append("融資大減✅")
            elif margin_long_change < -10:
                score += 8
                sentiment_parts.append("融資減少")
        
        # 融券變化評分（軋空潛力）
        if margin_short_change is not None:
            if margin_short_change > 30:
                score += 10  # 融券大增 = 軋空機會
                sentiment_parts.append("融券大增🎯")
            elif margin_short_change > 15:
                score += 5
                sentiment_parts.append("融券增加")
            elif margin_short_change < -30:
                score -= 5  # 空方回補完畢
                sentiment_parts.append("融券大減")
        
        # 券資比評分
        if short_long_ratio is not None:
            if short_long_ratio > 30:
                score += 10  # 高券資比 = 軋空潛力高
                sentiment_parts.append("高券資比🔥")
            elif short_long_ratio > 15:
                score += 5
        
        score = max(0, min(100, score))
        
        # 組合情緒描述
        if not sentiment_parts:
            sentiment = "➡️ 中性"
        else:
            sentiment = " / ".join(sentiment_parts)
        
        return {
            'margin_long_change': round(margin_long_change, 2) if margin_long_change is not None else None,
            'margin_short_change': round(margin_short_change, 2) if margin_short_change is not None else None,
            'short_long_ratio': round(short_long_ratio, 2) if short_long_ratio is not None else None,
            'margin_sentiment': sentiment,
            'margin_score': score
        }
    
    except Exception as e:
        return {'margin_long_change': None, 'margin_short_change': None,
                'short_long_ratio': None, 'margin_sentiment': f"計算錯誤: {e}", 'margin_score': 50}


# ==========================================
# 綜合因子評分
# ==========================================
def calculate_composite_score(fcf: dict, momentum: dict, stability: dict, 
                               asset_growth: dict, drawdown: dict, margin: dict) -> tuple[int, str, dict]:
    """
    計算綜合因子評分
    
    權重配置：
    - FCF Yield: 20%
    - 12-1 Momentum: 20%
    - Margin Stability: 15%
    - Asset Growth: 15% (反向)
    - Max Drawdown: 10%
    - Margin Trading: 20%
    
    Returns:
        (總分, 評級, 細節)
    """
    score = 0
    details = {}
    
    # 1. FCF Yield (20%)
    fcf_score = 0
    if fcf.get('fcf_yield') is not None:
        yield_val = fcf['fcf_yield']
        if yield_val > 8:
            fcf_score = 20
        elif yield_val > 5:
            fcf_score = 17
        elif yield_val > 2:
            fcf_score = 14
        elif yield_val > 0:
            fcf_score = 10
        elif yield_val > -5:
            fcf_score = 5
        else:
            fcf_score = 0
    details['fcf_yield_score'] = fcf_score
    score += fcf_score
    
    # 2. 12-1 Momentum (20%)
    mom_score = 0
    if momentum.get('momentum_12_1') is not None:
        mom_val = momentum['momentum_12_1']
        if mom_val > 30:
            mom_score = 20
        elif mom_val > 15:
            mom_score = 17
        elif mom_val > 5:
            mom_score = 14
        elif mom_val > -5:
            mom_score = 10
        elif mom_val > -15:
            mom_score = 5
        else:
            mom_score = 0
    details['momentum_score'] = mom_score
    score += mom_score
    
    # 3. Margin Stability (15%)
    stab_score = 0
    if stability.get('margin_stability_score') is not None:
        stab_val = stability['margin_stability_score']
        stab_score = int(stab_val / 100 * 15)
    details['stability_score'] = stab_score
    score += stab_score
    
    # 4. Asset Growth (15%, 反向因子)
    ag_score = 0
    if asset_growth.get('asset_growth') is not None:
        ag_val = asset_growth['asset_growth']
        if ag_val < 0:
            ag_score = 15
        elif ag_val < 10:
            ag_score = 12
        elif ag_val < 20:
            ag_score = 9
        elif ag_val < 40:
            ag_score = 5
        else:
            ag_score = 0
    details['asset_growth_score'] = ag_score
    score += ag_score
    
    # 5. Max Drawdown (10%)
    dd_score = 0
    if drawdown.get('max_drawdown') is not None:
        dd_val = drawdown['max_drawdown']
        if dd_val > -10:
            dd_score = 10
        elif dd_val > -20:
            dd_score = 8
        elif dd_val > -30:
            dd_score = 6
        elif dd_val > -50:
            dd_score = 3
        else:
            dd_score = 0
    details['drawdown_score'] = dd_score
    score += dd_score
    
    # 6. Margin Trading (20%)
    margin_score = int(margin.get('margin_score', 50) / 100 * 20)
    details['margin_trading_score'] = margin_score
    score += margin_score
    
    # 決定評級
    if score >= 85:
        rating = "🏆 SSS級：全能優質股"
    elif score >= 75:
        rating = "💎 S級：強烈推薦"
    elif score >= 65:
        rating = "🔥 A級：優質候選"
    elif score >= 55:
        rating = "✅ B級：穩健持有"
    elif score >= 45:
        rating = "➡️ C級：中性觀望"
    elif score >= 35:
        rating = "⚠️ D級：謹慎評估"
    else:
        rating = "🛑 F級：避開"
    
    return score, rating, details


# ==========================================
# 單股完整分析
# ==========================================
def analyze_stock(ticker: str) -> dict:
    """
    對單一股票執行完整 6 因子分析
    
    Args:
        ticker: 股票代碼
    
    Returns:
        完整分析結果字典
    """
    ticker_tw = ticker if ticker.endswith('.TW') else f"{ticker}.TW"
    
    # 計算各因子
    fcf_result = calculate_fcf_yield(ticker_tw)
    momentum_result = calculate_momentum_12_1(ticker_tw)
    stability_result = calculate_margin_stability(ticker_tw)
    asset_growth_result = calculate_asset_growth(ticker_tw)
    drawdown_result = calculate_max_drawdown(ticker_tw)
    margin_result = calculate_margin_trading(ticker_tw)
    
    # 計算綜合分數
    composite_score, rating, score_details = calculate_composite_score(
        fcf_result, momentum_result, stability_result,
        asset_growth_result, drawdown_result, margin_result
    )
    
    return {
        'ticker': ticker_tw,
        'composite_score': composite_score,
        'rating': rating,
        'score_details': score_details,
        'fcf': fcf_result,
        'momentum': momentum_result,
        'stability': stability_result,
        'asset_growth': asset_growth_result,
        'drawdown': drawdown_result,
        'margin_trading': margin_result
    }


# ==========================================
# 主程式
# ==========================================
def main():
    """主程式"""
    print("=" * 70)
    print("📊 Factor Analyzer V3 - 多因子量化分析系統")
    print("=" * 70)
    print("✨ 核心因子:")
    print("   1. 📈 FCF Yield：自由現金流收益率")
    print("   2. 🚀 12-1 Momentum：去噪動能因子")
    print("   3. 📊 Margin Stability：盈利穩定度")
    print("   4. 💰 Asset Growth：投資強度 (反向)")
    print("   5. 📉 Max Drawdown：最大回撤")
    print("   6. 🎯 Margin Trading：融資融券情緒")
    print()
    print(f"📦 離線模式: {'✅ 啟用' if OFFLINE_MODE else '❌ 停用'}")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 設定路徑
    script_dir = Path(__file__).parent
    list_json_path = script_dir.parent.parent.parent / "Stock_Pool" / "list.json"
    output_path = script_dir.parent.parent.parent / "Stock_Pool" / "factor_analysis_v3.csv"
    
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
    
    print()
    print("-" * 70)
    print("🔍 開始多因子分析...")
    print("-" * 70)
    
    results = []
    error_count = 0
    
    for i, ticker in enumerate(tickers, 1):
        ticker_tw = f"{ticker}.TW"
        company_name = company_dict.get(ticker_tw, '')
        
        print(f"\n[{i}/{len(tickers)}] 分析 {ticker} ({company_name})...")
        
        try:
            result = analyze_stock(ticker)
            
            # 扁平化結果
            flat_result = {
                'Ticker': ticker_tw,
                'Company_Name': company_name,
                'Composite_Score': result['composite_score'],
                'Rating': result['rating'],
                # FCF Yield
                'FCF_Yield': result['fcf']['fcf_yield'],
                'FCF_Yield_Status': result['fcf']['fcf_yield_status'],
                # Momentum
                'Momentum_12_1': result['momentum']['momentum_12_1'],
                'Return_12M': result['momentum']['return_12m'],
                'Return_1M': result['momentum']['return_1m'],
                'Momentum_Status': result['momentum']['momentum_status'],
                # Stability
                'GPM_Volatility': result['stability']['gpm_volatility'],
                'OPM_Volatility': result['stability']['opm_volatility'],
                'Stability_Score': result['stability']['margin_stability_score'],
                'Stability_Status': result['stability']['stability_status'],
                # Asset Growth
                'Asset_Growth': result['asset_growth']['asset_growth'],
                'Asset_Growth_Status': result['asset_growth']['asset_growth_status'],
                # Drawdown
                'Max_Drawdown': result['drawdown']['max_drawdown'],
                'Current_Drawdown': result['drawdown']['current_drawdown'],
                'Drawdown_Status': result['drawdown']['drawdown_status'],
                # Margin Trading
                'Margin_Long_Change': result['margin_trading']['margin_long_change'],
                'Margin_Short_Change': result['margin_trading']['margin_short_change'],
                'Short_Long_Ratio': result['margin_trading']['short_long_ratio'],
                'Margin_Sentiment': result['margin_trading']['margin_sentiment'],
                'Margin_Score': result['margin_trading']['margin_score'],
                # Score Details
                'Score_Details': json.dumps(result['score_details'], ensure_ascii=False)
            }
            
            results.append(flat_result)
            
            # 顯示結果
            icon = "🏆" if result['composite_score'] >= 75 else ("🔥" if result['composite_score'] >= 65 else ("✅" if result['composite_score'] >= 55 else "➡️"))
            print(f"    {icon} 綜合評分: {result['composite_score']} 分 | {result['rating']}")
            print(f"       FCF Yield: {result['fcf']['fcf_yield']}% | Momentum: {result['momentum']['momentum_12_1']}%")
            print(f"       Stability: {result['stability']['margin_stability_score']} | Asset Growth: {result['asset_growth']['asset_growth']}%")
            print(f"       MDD: {result['drawdown']['max_drawdown']}% | Margin: {result['margin_trading']['margin_sentiment']}")
        
        except Exception as e:
            print(f"    ❌ 分析錯誤: {str(e)}")
            error_count += 1
    
    # 生成報告
    print()
    print("=" * 70)
    print("📈 分析完成！")
    print("=" * 70)
    
    if not results:
        print("⚠️  沒有有效結果")
        return
    
    results_df = pd.DataFrame(results)
    
    # 按綜合分數排序
    results_df = results_df.sort_values('Composite_Score', ascending=False)
    
    # 儲存
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"📁 報告已儲存: {output_path}")
    
    # 統計
    print()
    print("-" * 70)
    print("📋 評級統計:")
    print("-" * 70)
    
    rating_counts = results_df['Rating'].value_counts()
    for rating, count in rating_counts.items():
        print(f"   {rating}: {count} 支")
    
    # Top 15 展示
    print()
    print("-" * 70)
    print("🏆 Top 15 綜合評分:")
    print("-" * 70)
    
    for idx, row in results_df.head(15).iterrows():
        print(f"\n   {row['Composite_Score']} 分 | {row['Ticker']} ({row['Company_Name']})")
        print(f"      {row['Rating']}")
        print(f"      FCF: {row['FCF_Yield']}% | Mom: {row['Momentum_12_1']}% | Stab: {row['Stability_Score']}")
        print(f"      AG: {row['Asset_Growth']}% | MDD: {row['Max_Drawdown']}% | Margin: {row['Margin_Score']}")
    
    print()
    print(f"❌ 數據異常/錯誤: {error_count} 支")
    print(f"⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

