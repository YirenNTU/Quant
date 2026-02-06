import tejapi
import pandas as pd

# 使用您設定的 API Key
TEJ_API_KEY = "K1ccQEAEVTu5323tVSPUFLHvet7jRc"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

def check_table(table_name, description):
    print(f"正在測試資料表: {table_name} ({description})...")
    try:
        # 嘗試抓取台積電 (2330) 的一筆資料
        data = tejapi.get(table_name,
                          coid='2330',
                          opts={'limit': 1},
                          paginate=False)
        if len(data) > 0:
            print(f"✅ 成功! 您有 {table_name} 的權限。")
            return True
        else:
            print(f"❓ {table_name} 回傳資料為空 (但無報錯)。")
            return True
    except Exception as e:
        print(f"❌ 失敗: {str(e)}")
        return False

print("="*50)
print("TEJ 權限診斷工具")
print("="*50)

# 測試關鍵資料表
tables_to_test = [
    ('TWN/AIND', '公司基本資料'),
    ('TWN/APR01', '股價資料(除權息調整)'),
    ('TWN/AIM1A', '財務資料(IFRS累季)'),
    ('TWN/APIP', '股價資料(未調整)'),
    ('TWN/EWPRCD', '證券交易資料表(未調整)'), # 某些方案可能用這個
]

results = {}
for table, desc in tables_to_test:
    results[table] = check_table(table, desc)
    print("-" * 30)

print("\n診斷結果:")
if results['TWN/APR01'] and results['TWN/AIM1A']:
    print("✨ 您的權限完整，可以正常執行分析工具。")
    print("如果仍有問題，可能是該特定股票 (1102, 1210...) 不在您的授權範圍內。")
else:
    print("⚠️ 您的權限似乎缺少部分關鍵資料表。")
    print("請確認您購買的 TEJ 方案是否包含：")
    print("1. 上市(櫃)調整股價(日) - TWN/APR01")
    print("2. IFRS財務會計科目說明(季) - TWN/AIM1A")

