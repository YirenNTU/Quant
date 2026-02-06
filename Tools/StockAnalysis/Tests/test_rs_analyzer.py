#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相對強度分析快速測試腳本
========================
快速測試 calculate_rs_vs_sector() 功能是否正常
"""

import yfinance as yf
from datetime import datetime
import sys
from pathlib import Path

# 添加路徑以便 import valuation_analyzer_v2
sys.path.insert(0, str(Path(__file__).parent.parent / "Analyzers"))

from valuation_analyzer_v2 import get_sector_etf, calculate_rs_vs_sector


def test_single_stock(ticker: str):
    """
    測試單一股票的相對強度分析
    """
    print(f"\n{'='*70}")
    print(f"📊 測試股票: {ticker}")
    print(f"{'='*70}")
    
    try:
        # 1. 取得股票資訊
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info:
            print(f"❌ 無法取得 {ticker} 的股票資訊")
            return
        
        company_name = info.get('longName', info.get('shortName', ticker))
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        
        print(f"公司名稱: {company_name}")
        print(f"產業分類: {sector} / {industry}")
        
        # 2. 取得對應的產業 ETF
        sector_etf = get_sector_etf(ticker, info)
        print(f"對應 ETF: {sector_etf}")
        
        # 3. 計算相對強度
        print(f"\n⏳ 計算相對強度（120天）...")
        rs_data = calculate_rs_vs_sector(ticker, info, period=120)
        
        if rs_data is None:
            print(f"❌ 無法計算相對強度")
            return
        
        # 4. 顯示結果
        print(f"\n✅ 相對強度分析結果:")
        print(f"{'─'*70}")
        
        rs_ratio = rs_data['rs_ratio']
        rs_percentile = rs_data['rs_percentile']
        trend_status = rs_data['trend_status']
        stock_return = rs_data['stock_return']
        sector_return = rs_data['sector_return']
        
        print(f"📈 RS 比率: {rs_ratio:.3f} ", end="")
        if rs_ratio > 1.1:
            print("🔥 (遠強於產業)")
        elif rs_ratio > 1.0:
            print("💪 (強於產業)")
        elif rs_ratio > 0.9:
            print("➡️ (接近產業)")
        else:
            print("⚠️ (弱於產業)")
        
        print(f"📊 RS 百分位: {rs_percentile*100:.1f}%")
        print(f"🎯 趨勢狀態: {trend_status}")
        print(f"\n📉 報酬率對比 (6個月):")
        print(f"   個股報酬: {stock_return*100:+.2f}%")
        print(f"   產業報酬: {sector_return*100:+.2f}%")
        print(f"   超額報酬: {(stock_return - sector_return)*100:+.2f}%")
        
        # 5. 投資建議
        print(f"\n💡 初步判斷:")
        if rs_ratio > 1.1 and rs_percentile > 0.7:
            print("   🏆 產業龍頭，相對強勢明顯")
            print("   → 若估值合理，可考慮買進")
        elif rs_ratio > 1.0:
            print("   ✅ 相對強勢，表現優於產業")
            print("   → 可納入觀察名單")
        elif rs_ratio < 0.9 and rs_percentile < 0.3:
            print("   ⚠️ 相對弱勢，落後產業")
            print("   → 即使便宜也要小心價值陷阱")
        else:
            print("   ➡️ 相對持平，跟隨產業走勢")
            print("   → 關注基本面變化")
        
    except Exception as e:
        print(f"❌ 測試時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """
    主測試程式
    """
    print("=" * 70)
    print("🔬 相對強度分析測試工具")
    print("=" * 70)
    print(f"⏰ 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 測試股票清單（涵蓋不同產業）
    test_tickers = [
        "2330.TW",  # 台積電（科技）
        "2317.TW",  # 鴻海（科技）
        "2882.TW",  # 國泰金（金融）
        "2454.TW",  # 聯發科（半導體）
        "2412.TW",  # 中華電（電信）
    ]
    
    print(f"\n📋 預計測試 {len(test_tickers)} 支股票:")
    for ticker in test_tickers:
        print(f"   - {ticker}")
    
    # 執行測試
    for ticker in test_tickers:
        test_single_stock(ticker)
        print()  # 空行分隔
    
    print("=" * 70)
    print("✅ 測試完成！")
    print("=" * 70)
    print("\n📝 使用說明:")
    print("   若所有股票都能正常顯示相對強度資訊，代表功能正常。")
    print("   若出現錯誤，請檢查 yfinance 是否能正常抓取台股數據。")
    print()
    print("🚀 下一步:")
    print("   確認測試通過後，可執行完整分析:")
    print("   python valuation_analyzer.py")


if __name__ == "__main__":
    main()

