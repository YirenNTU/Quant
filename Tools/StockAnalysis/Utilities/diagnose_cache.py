import json
import os
import pandas as pd
import pickle

# 直接讀取快取目錄
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tej_cache")

print("="*50)
print("TEJ 快取資料診斷 (Offline Debug)")
print("="*50)

if not os.path.exists(CACHE_DIR):
    print("❌ 快取目錄不存在")
    exit()

files = [f for f in os.listdir(CACHE_DIR) if f.endswith('financials.pkl')]
print(f"📂 發現 {len(files)} 份財報快取檔案")

# 挑選前 3 份有效的快取來診斷
count = 0
for filename in files:
    if count >= 3: break
    
    ticker = filename.split('_')[0]
    file_path = os.path.join(CACHE_DIR, filename)
    
    print(f"\n🔍 診斷股票: {ticker} (From Cache)")
    
    try:
        # 快取存的是 tuple (fin, bs, cf)
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
            
        # 相容性處理：有時候可能存的是 dataframe，有時候是 tuple
        if isinstance(data, tuple):
            fin = data[0]
        else:
            fin = data
            
        if fin is None or fin.empty:
            print("❌ 快取內容為空")
            continue
            
        print(f"✅ 取得 {fin.shape[1]} 季資料")
        print(f"   日期欄位: {fin.columns.tolist()}")
        
        # 檢查關鍵欄位
        if 'Total Revenue' in fin.index:
            rev = fin.loc['Total Revenue']
            # 嘗試找毛利
            gp = fin.loc['Gross Profit'] if 'Gross Profit' in fin.index else None
            
            print("\n📊 營收數據 (檢查是否為累計數):")
            # 排序日期以方便觀察
            rev = rev.sort_index()
            
            prev_rev = 0
            for date, r in rev.items():
                r_val = float(r) if r is not None else 0
                
                # 簡單判斷：如果 Q4 遠大於 Q1，且 Q2 > Q1，極可能是累計數
                # 這裡印出數值讓使用者判斷
                gp_val = float(gp[date]) if gp is not None and pd.notna(gp[date]) else 0
                gpm = (gp_val / r_val) * 100 if r_val != 0 else 0
                
                print(f"   {date}: 營收={r_val:,.0f}, 毛利={gp_val:,.0f}, GPM={gpm:.2f}%")
                
        else:
            print("❌ 缺少 'Total Revenue' 欄位")
            print("   現有欄位:", fin.index.tolist())
            
        count += 1
        
    except Exception as e:
        print(f"❌ 讀取失敗: {e}")



