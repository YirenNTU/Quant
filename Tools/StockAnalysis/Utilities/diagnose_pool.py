import json
import os
import pandas as pd
try:
    from tej_tool import yf
except ImportError:
    import sys
    # 添加 Data 資料夾到 Python 路徑
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))
    from tej_tool import yf

# 讀取清單，隨機挑選幾支股票進行診斷
list_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Stock_Pool", "list.json")
with open(list_path, 'r') as f:
    tickers = list(json.load(f).keys())

# 挑選前 3 支股票來診斷
test_tickers = tickers[:3]

print("="*50)
print("TEJ 資料源診斷 (Pool Analyser Debug)")
print("="*50)

for ticker in test_tickers:
    print(f"\n🔍 診斷股票: {ticker}")
    stock = yf.Ticker(ticker)
    fin = stock.quarterly_financials
    
    if fin is None or fin.empty:
        print("❌ 無法取得財務報表 (Empty)")
        continue
        
    print(f"✅ 取得 {fin.shape[1]} 季資料")
    print(f"   日期欄位: {fin.columns.tolist()}")
    
    # 檢查關鍵欄位
    if 'Gross Profit' in fin.index and 'Total Revenue' in fin.index:
        rev = fin.loc['Total Revenue']
        gp = fin.loc['Gross Profit']
        
        print("\n📊 營收與毛利數據 (檢查是否為累計數):")
        for date, r, g in zip(rev.index, rev, gp):
            gpm = (g / r) * 100 if r != 0 else 0
            print(f"   {date}: 營收={r:,.0f}, 毛利={g:,.0f}, GPM={gpm:.2f}%")
            
        # 檢查是否為累計數特徵：Q4 通常是 Q1 的 4 倍左右？
    else:
        print("❌ 缺少 'Gross Profit' 或 'Total Revenue' 欄位")
        print("   現有欄位:", fin.index.tolist())



