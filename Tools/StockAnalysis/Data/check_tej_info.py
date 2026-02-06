import tejapi

# 設定您的 Key
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("="*50)
print("TEJ 帳號資訊查詢")
print("="*50)

try:
    print(f"正在查詢 Key: {TEJ_API_KEY} ...\n")
    info = tejapi.ApiConfig.info()
    
    print("✅ 查詢成功！您的帳號資訊如下：")
    print("-" * 30)
    
    # 顯示基本資訊
    user_info = info.get('user', {})
    print(f"使用者名稱: {user_info.get('name', 'N/A')}")
    print(f"有效期間: {info.get('startDate', 'N/A')} ~ {info.get('endDate', 'N/A')}")
    print(f"每日呼叫上限: {info.get('reqDayLimit', 'N/A')} 次")
    print(f"今日已呼叫: {info.get('todayReqCount', 'N/A')} 次")
    print("-" * 30)
    
    # 顯示可用資料表 (關鍵資訊)
    print("\n📚 您有權限的資料表 (Tables):")
    tables = user_info.get('tables', [])
    
    if tables:
        for table in tables:
            print(f"   - {table}")
    else:
        print("   ⚠️ 未發現可用資料表 (可能是試用版或權限設定問題)")
        
except Exception as e:
    print(f"❌ 查詢失敗: {str(e)}")

