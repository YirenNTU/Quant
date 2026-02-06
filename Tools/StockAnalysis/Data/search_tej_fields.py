import tejapi
import pandas as pd

# 設定您的 Key
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("="*50)
print("TEJ 欄位偵測工具")
print("="*50)

def inspect_table(table_name, coid='2330'):
    print(f"\n🔍 正在偵測資料表: {table_name}")
    try:
        # 抓取台積電最近一筆資料
        data = tejapi.get(table_name,
                          coid=coid,
                          opts={'limit': 1},
                          paginate=False)
        
        if len(data) > 0:
            print("✅ 抓取成功！欄位清單如下：")
            columns = data.columns.tolist()
            # 每行印 5 個欄位
            for i in range(0, len(columns), 5):
                print(columns[i:i+5])
                
            # 嘗試印出第一筆資料的內容 (前 5 個欄位)
            print("\n📝 資料範例 (前5欄):")
            print(data.iloc[0].head(5))
        else:
            print("⚠️ 成功連線但無資料 (可能需要換個股票代碼試試)")
            
    except Exception as e:
        print(f"❌ 偵測失敗: {str(e)}")

# 1. 偵測股價表
inspect_table('TWN/APIPRCD')

# 2. 偵測財報表 (這是最重要的！)
inspect_table('TWN/AINVFINB')

# 3. 偵測基本資料表
inspect_table('TWN/APISTOCK')

