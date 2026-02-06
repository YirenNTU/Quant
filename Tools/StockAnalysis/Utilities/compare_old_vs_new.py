#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舊系統 vs 新系統對比分析
=========================
展示「絕對趨勢」與「相對強度」的判斷差異
"""

# import yfinance as yf
try:
    from tej_tool import yf
except ImportError:
    import sys
    import os
    # 添加 Data 資料夾到 Python 路徑
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))
    from tej_tool import yf

import pandas as pd
from datetime import datetime, timedelta


def calculate_ma_trend(ticker: str) -> dict | None:
    """
    舊系統：計算 MA20/MA60 絕對趨勢
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        
        if hist.empty or len(hist) < 60:
            return None
        
        close_prices = hist['Close']
        current_price = close_prices.iloc[-1]
        
        ma20 = close_prices.rolling(window=20).mean().iloc[-1]
        ma60 = close_prices.rolling(window=60).mean().iloc[-1]
        
        if pd.isna(ma20) or pd.isna(ma60):
            return None
        
        # 舊判斷邏輯
        if current_price > ma20 and ma20 > ma60:
            trend = "🔥 多頭強勢"
        elif current_price < ma60:
            trend = "🛑 空頭/轉弱"
        elif ma20 > current_price > ma60:
            trend = "⚠️ 回檔整理"
        else:
            trend = "🔄 整理中"
        
        return {
            'trend': trend,
            'current_price': current_price,
            'ma20': ma20,
            'ma60': ma60
        }
    except:
        return None


def calculate_rs(ticker: str, sector_etf: str = "0050.TW") -> dict | None:
    """
    新系統：計算相對強度
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        stock = yf.Ticker(ticker)
        stock_hist = stock.history(start=start_date, end=end_date)
        
        etf = yf.Ticker(sector_etf)
        etf_hist = etf.history(start=start_date, end=end_date)
        
        if stock_hist.empty or etf_hist.empty:
            return None
        
        stock_prices = stock_hist['Close'].iloc[-120:]
        etf_prices = etf_hist['Close'].iloc[-120:]
        
        if len(stock_prices) < 2 or len(etf_prices) < 2:
            return None
        
        stock_return = (stock_prices.iloc[-1] / stock_prices.iloc[0]) - 1
        sector_return = (etf_prices.iloc[-1] / etf_prices.iloc[0]) - 1
        
        rs_ratio = (1 + stock_return) / (1 + sector_return)
        
        # 新判斷邏輯
        if rs_ratio > 1.1:
            trend = "🚀 相對強勢（產業龍頭）"
        elif rs_ratio > 1.0:
            trend = "💪 相對強勢"
        elif rs_ratio > 0.9:
            trend = "➡️ 相對持平"
        else:
            trend = "⚠️ 相對弱勢"
        
        return {
            'trend': trend,
            'rs_ratio': rs_ratio,
            'stock_return': stock_return,
            'sector_return': sector_return
        }
    except:
        return None


def compare_stock(ticker: str, pe_status: str = "低估"):
    """
    對比單一股票的判斷差異
    
    Args:
        ticker: 股票代碼
        pe_status: 估值狀態（低估/合理/高估）
    """
    print(f"\n{'='*70}")
    print(f"📊 {ticker}")
    print(f"{'='*70}")
    
    # 取得股票資訊
    stock = yf.Ticker(ticker)
    info = stock.info
    name = info.get('longName', info.get('shortName', ticker))
    print(f"公司: {name}")
    print(f"假設估值: {pe_status}")
    print()
    
    # 舊系統判斷
    old_data = calculate_ma_trend(ticker)
    print("【舊系統】絕對趨勢 (MA20/MA60):")
    if old_data:
        print(f"   趨勢: {old_data['trend']}")
        print(f"   價格: {old_data['current_price']:.2f}")
        print(f"   MA20: {old_data['ma20']:.2f} | MA60: {old_data['ma60']:.2f}")
        
        # 舊系統決策
        if pe_status == "低估":
            if "空頭" in old_data['trend']:
                old_decision = "低估 ⚠️(接刀小心)"
            elif "多頭" in old_data['trend']:
                old_decision = "低估 💎(強烈買進)"
            else:
                old_decision = "低估 → 買進"
        else:
            old_decision = f"{pe_status} → 觀望"
        
        print(f"   決策: {old_decision}")
    else:
        print("   ⚠️ 無法計算")
        old_decision = "N/A"
    
    print()
    
    # 新系統判斷
    new_data = calculate_rs(ticker)
    print("【新系統】相對強度 (RS vs 0050.TW):")
    if new_data:
        print(f"   趨勢: {new_data['trend']}")
        print(f"   RS比率: {new_data['rs_ratio']:.3f}")
        print(f"   個股報酬: {new_data['stock_return']*100:+.2f}%")
        print(f"   產業報酬: {new_data['sector_return']*100:+.2f}%")
        print(f"   超額報酬: {(new_data['stock_return'] - new_data['sector_return'])*100:+.2f}%")
        
        # 新系統決策
        if pe_status == "低估":
            if "相對弱勢" in new_data['trend']:
                new_decision = "低估 ⚠️(相對弱勢，謹慎)"
            elif "產業龍頭" in new_data['trend']:
                new_decision = "低估 💎💎(產業龍頭，強烈買進)"
            elif "相對強勢" in new_data['trend']:
                new_decision = "低估 💎(相對強勢，買進)"
            else:
                new_decision = "低估 ✅(可考慮)"
        else:
            new_decision = f"{pe_status} → 觀望"
        
        print(f"   決策: {new_decision}")
    else:
        print("   ⚠️ 無法計算")
        new_decision = "N/A"
    
    print()
    
    # 對比分析
    print("【差異分析】:")
    if old_data and new_data:
        print(f"   舊判斷: {old_decision}")
        print(f"   新判斷: {new_decision}")
        print()
        
        # 分析差異原因
        if old_decision != new_decision:
            print("   🔍 為何不同？")
            
            # 情境 1：產業整體下跌，但個股相對抗跌
            if "空頭" in old_data['trend'] and "強勢" in new_data['trend']:
                print("      ✅ 舊系統誤判：產業整體下跌，但個股相對抗跌")
                print("      → 新系統正確識別出「產業內的強者」")
            
            # 情境 2：產業整體上漲，但個股漲幅落後
            elif "多頭" in old_data['trend'] and "弱勢" in new_data['trend']:
                print("      ✅ 舊系統誤判：產業整體上漲，但個股漲幅落後")
                print("      → 新系統正確識別出「相對弱勢」")
            
            # 情境 3：絕對價格持平，但相對產業強勢
            elif "整理" in old_data['trend'] and "強勢" in new_data['trend']:
                print("      ✅ 舊系統保守：股價整理中")
                print("      → 新系統發現相對強勢（可能是轉機股）")
            
            else:
                print("      → 兩系統識別角度不同，新系統更關注「相對表現」")


def main():
    """
    主程式：對比多支股票
    """
    print("=" * 70)
    print("🔬 舊系統 vs 新系統對比分析")
    print("=" * 70)
    print(f"⏰ 分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("說明：")
    print("   舊系統 = 絕對趨勢 (MA20/MA60)")
    print("   新系統 = 相對強度 (RS vs Sector ETF)")
    print()
    
    # 測試案例
    test_cases = [
        ("2330.TW", "合理"),  # 台積電
        ("2317.TW", "低估"),  # 鴻海
        ("2454.TW", "低估"),  # 聯發科
        ("2882.TW", "低估"),  # 國泰金
    ]
    
    for ticker, pe_status in test_cases:
        compare_stock(ticker, pe_status)
    
    print("=" * 70)
    print("📝 總結")
    print("=" * 70)
    print()
    print("【新系統優勢】:")
    print("   1. ✅ 排除產業整體波動的影響")
    print("   2. ✅ 精準識別「產業內的強者」")
    print("   3. ✅ 有效避免「價值陷阱」")
    print("   4. ✅ 提早發現「轉機股」")
    print()
    print("【適用情境】:")
    print("   • 產業整體下跌，但個股相對抗跌 → 新系統識別為「強勢」")
    print("   • 產業整體上漲，但個股漲幅落後 → 新系統識別為「弱勢」")
    print("   • 個股便宜但相對產業走弱 → 新系統警示「價值陷阱」")
    print()


if __name__ == "__main__":
    main()

