#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================
🔍 TEJ 完整資料表結構探索
=====================================================
自動探索所有您有權限的資料表，並輸出詳細欄位說明
"""

import tejapi
import pandas as pd
from datetime import datetime, timedelta

# TEJ API 設定
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

# 測試用股票代碼
TEST_TICKER = '2330'

def explore_table(table_name, description):
    """探索單一資料表"""
    print(f"\n{'='*80}")
    print(f"📊 {table_name}")
    print(f"   {description}")
    print('='*80)
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # 根據資料表類型調整查詢方式
        if 'PRCD' in table_name or 'SALE' in table_name or 'SHRACT' in table_name:
            data = tejapi.get(
                table_name,
                coid=TEST_TICKER,
                mdate={'gte': start_date, 'lte': end_date},
                opts={'limit': 3, 'sort': 'mdate.desc'}
            )
        elif 'FINB' in table_name or 'FESTM' in table_name:
            data = tejapi.get(
                table_name,
                coid=TEST_TICKER,
                opts={'limit': 3, 'sort': 'mdate.desc'}
            )
        elif 'DV1' in table_name or 'STK1' in table_name or 'MT1' in table_name:
            data = tejapi.get(
                table_name,
                coid=TEST_TICKER,
                opts={'limit': 3, 'sort': 'mdate.desc'}
            )
        else:
            data = tejapi.get(
                table_name,
                coid=TEST_TICKER,
                opts={'limit': 3}
            )
        
        if len(data) == 0:
            print("⚠️ 無資料")
            return None
        
        print(f"\n欄位數量: {len(data.columns)} 個")
        print(f"\n{'欄位名稱':<25} {'資料類型':<15} {'範例值'}")
        print("-" * 80)
        
        columns_info = []
        for col in data.columns:
            dtype = str(data[col].dtype)
            sample = str(data[col].iloc[0]) if len(data) > 0 else 'N/A'
            if len(sample) > 40:
                sample = sample[:37] + '...'
            
            print(f"{col:<25} {dtype:<15} {sample}")
            columns_info.append({'column': col, 'dtype': dtype, 'sample': sample})
        
        return columns_info
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return None


def main():
    print("=" * 80)
    print("🔍 TEJ API 完整資料表結構探索")
    print(f"   測試股票: {TEST_TICKER} (台積電)")
    print(f"   時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 定義要探索的資料表
    tables = [
        ('TWN/APIPRCD', '股價資料 - 每日開高低收量、PE、PB'),
        ('TWN/AINVFINB', '財務資料 - 會計師簽證(83個科目)'),
        ('TWN/APISALE', '月營收 - 每月營業收入'),
        ('TWN/APISTOCK', '證券屬性 - 產業分類、公司資料'),
        ('TWN/APISHRACT', '籌碼資料 - 三大法人、融資券'),
        ('TWN/APIDV1', '股利資料 - 現金/股票股利'),
        ('TWN/APISTK1', '資本形成 - 股本變動'),
        ('TWN/AFESTM1', '自結數 - 公司自行公布財務'),
    ]
    
    results = {}
    for table_name, desc in tables:
        cols = explore_table(table_name, desc)
        if cols:
            results[table_name] = cols
    
    # 輸出摘要
    print("\n\n" + "=" * 80)
    print("📋 資料表摘要")
    print("=" * 80)
    
    for table_name, cols in results.items():
        print(f"\n{table_name}: {len(cols)} 個欄位")
    
    print("\n✅ 探索完成！")


if __name__ == "__main__":
    main()

