#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================
🔍 TEJ API 探索工具 (API Explorer)
=====================================================
用於探索您的 TEJ 帳戶資訊、可用資料表、欄位結構等。

功能：
1. 顯示帳戶資訊 (額度、權限)
2. 列出所有可用資料表
3. 查看特定資料表的欄位結構
4. 下載範例資料
"""

import tejapi
import pandas as pd
from datetime import datetime, timedelta
import json

# ==========================================
# TEJ API 設定
# ==========================================
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

# 您已知有權限的資料表
KNOWN_TABLES = [
    'TWN/AFESTM1',      # 財務資料_公司自結數(17個科目)
    'TWN/AINVFINB',     # 財務資料_會計師簽證財務資料(83個科目)
    'TWN/APIDV1',       # 股利公告&發放資料庫
    'TWN/APIMT1',       # 股利政策
    'TWN/APIPRCD',      # 交易資料-股價資料(名目股價)
    'TWN/APISALE',      # 月營收
    'TWN/APISALE1',     # 月營收(版本別)
    'TWN/APISHRACT',    # 交易資料-籌碼資料(三大法人、融資券、當沖)
    'TWN/APISHRACTW',   # 交易資料-籌碼資料(集保庫存)
    'TWN/APISTK1',      # 資本形成
    'TWN/APISTKATTR',   # 交易資料_股票日交易註記資訊
    'TWN/APISTOCK',     # 證券屬性資料表
    'TWN/TRADEDAY_TWSE' # 交易資料-交易日期表
]


def print_section(title):
    """列印區塊標題"""
    print()
    print("=" * 70)
    print(f"📊 {title}")
    print("=" * 70)


def get_account_info():
    """取得帳戶資訊"""
    print_section("帳戶資訊 (Account Info)")
    
    try:
        info = tejapi.ApiConfig.info()
        print(f"API Key: {TEJ_API_KEY[:10]}...{TEJ_API_KEY[-5:]}")
        print()
        
        if isinstance(info, dict):
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print(info)
            
    except Exception as e:
        print(f"❌ 無法取得帳戶資訊: {e}")


def list_available_tables():
    """列出所有可用資料表"""
    print_section("可用資料表 (Available Tables)")
    
    print("📋 您的訂閱包含以下資料表：\n")
    
    table_descriptions = {
        'TWN/AFESTM1': '財務資料_公司自結數 (17個科目) - 公司自行公布的初步財務數據',
        'TWN/AINVFINB': '財務資料_會計師簽證 (83個科目) - 經會計師查核的完整財報',
        'TWN/APIDV1': '股利公告&發放資料庫 - 現金/股票股利資訊',
        'TWN/APIMT1': '股利政策 - 公司股利發放政策',
        'TWN/APIPRCD': '股價資料 (名目股價) - 每日開高低收量',
        'TWN/APISALE': '月營收 - 每月營業收入',
        'TWN/APISALE1': '月營收(版本別) - 含修正版本的月營收',
        'TWN/APISHRACT': '籌碼資料 - 三大法人、融資券、當沖',
        'TWN/APISHRACTW': '籌碼資料 - 集保庫存分佈',
        'TWN/APISTK1': '資本形成 - 股本變動、增資減資',
        'TWN/APISTKATTR': '交易註記 - 處置股、警示股等',
        'TWN/APISTOCK': '證券屬性 - 公司基本資料、產業分類',
        'TWN/TRADEDAY_TWSE': '交易日期表 - 台灣證交所開市日期'
    }
    
    for table in KNOWN_TABLES:
        desc = table_descriptions.get(table, '(無說明)')
        print(f"  📁 {table}")
        print(f"     └─ {desc}")
        print()


def explore_table_structure(table_name, sample_ticker='2330'):
    """探索特定資料表的欄位結構"""
    print_section(f"資料表結構: {table_name}")
    
    try:
        # 嘗試抓取少量資料來看欄位
        if 'PRCD' in table_name or 'SALE' in table_name or 'SHRACT' in table_name:
            # 時序資料，需要指定日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            data = tejapi.get(
                table_name,
                coid=sample_ticker,
                mdate={'gte': start_date, 'lte': end_date},
                opts={'limit': 5}
            )
        elif 'STOCK' in table_name or 'STKATTR' in table_name:
            # 屬性資料，直接抓
            data = tejapi.get(
                table_name,
                coid=sample_ticker,
                opts={'limit': 5}
            )
        elif 'FINB' in table_name or 'FESTM' in table_name:
            # 財報資料
            data = tejapi.get(
                table_name,
                coid=sample_ticker,
                opts={'limit': 5, 'sort': 'mdate.desc'}
            )
        elif 'TRADEDAY' in table_name:
            # 交易日期表
            data = tejapi.get(
                table_name,
                opts={'limit': 5, 'sort': 'mdate.desc'}
            )
        else:
            # 其他
            data = tejapi.get(
                table_name,
                opts={'limit': 5}
            )
        
        if len(data) == 0:
            print(f"⚠️ 無法取得範例資料")
            return
        
        # 顯示欄位資訊
        print(f"\n📋 欄位數量: {len(data.columns)} 個")
        print(f"📋 範例筆數: {len(data)} 筆")
        print()
        
        print("欄位名稱 (Column Names):")
        print("-" * 50)
        
        for i, col in enumerate(data.columns, 1):
            dtype = str(data[col].dtype)
            sample_val = data[col].iloc[0] if len(data) > 0 else 'N/A'
            
            # 截斷過長的值
            sample_str = str(sample_val)
            if len(sample_str) > 30:
                sample_str = sample_str[:27] + '...'
            
            print(f"  {i:3}. {col:20} ({dtype:10}) 範例: {sample_str}")
        
        print()
        print("完整範例資料 (前5筆):")
        print("-" * 50)
        print(data.to_string())
        
    except Exception as e:
        print(f"❌ 探索失敗: {e}")


def download_sample_data(table_name, ticker='2330', output_format='csv'):
    """下載範例資料"""
    print_section(f"下載範例資料: {table_name}")
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        if 'PRCD' in table_name:
            data = tejapi.get(
                table_name,
                coid=ticker,
                mdate={'gte': start_date, 'lte': end_date},
                paginate=True
            )
        elif 'FINB' in table_name:
            data = tejapi.get(
                table_name,
                coid=ticker,
                opts={'limit': 20, 'sort': 'mdate.desc'},
                paginate=True
            )
        else:
            data = tejapi.get(
                table_name,
                coid=ticker,
                paginate=True
            )
        
        if len(data) == 0:
            print(f"⚠️ 無資料")
            return
        
        # 儲存檔案
        filename = f"sample_{table_name.replace('/', '_')}_{ticker}.{output_format}"
        
        if output_format == 'csv':
            data.to_csv(filename, index=False, encoding='utf-8-sig')
        elif output_format == 'json':
            data.to_json(filename, orient='records', force_ascii=False, indent=2)
        elif output_format == 'xlsx':
            data.to_excel(filename, index=False)
        
        print(f"✅ 已儲存: {filename}")
        print(f"   筆數: {len(data)}")
        print(f"   欄位: {len(data.columns)}")
        
    except Exception as e:
        print(f"❌ 下載失敗: {e}")


def interactive_menu():
    """互動式選單"""
    while True:
        print()
        print("=" * 70)
        print("🔍 TEJ API 探索工具 - 主選單")
        print("=" * 70)
        print()
        print("  1. 查看帳戶資訊")
        print("  2. 列出所有可用資料表")
        print("  3. 探索特定資料表結構")
        print("  4. 下載範例資料")
        print("  5. 快速探索所有資料表欄位")
        print("  0. 離開")
        print()
        
        choice = input("請選擇 (0-5): ").strip()
        
        if choice == '0':
            print("👋 再見！")
            break
        elif choice == '1':
            get_account_info()
        elif choice == '2':
            list_available_tables()
        elif choice == '3':
            print("\n可用資料表:")
            for i, t in enumerate(KNOWN_TABLES, 1):
                print(f"  {i}. {t}")
            idx = input("\n請輸入編號或資料表名稱: ").strip()
            
            try:
                if idx.isdigit():
                    table = KNOWN_TABLES[int(idx) - 1]
                else:
                    table = idx
                
                ticker = input("請輸入股票代碼 (預設 2330): ").strip() or '2330'
                explore_table_structure(table, ticker)
            except:
                print("❌ 無效的選擇")
                
        elif choice == '4':
            print("\n可用資料表:")
            for i, t in enumerate(KNOWN_TABLES, 1):
                print(f"  {i}. {t}")
            idx = input("\n請輸入編號或資料表名稱: ").strip()
            
            try:
                if idx.isdigit():
                    table = KNOWN_TABLES[int(idx) - 1]
                else:
                    table = idx
                
                ticker = input("請輸入股票代碼 (預設 2330): ").strip() or '2330'
                fmt = input("請輸入格式 csv/json/xlsx (預設 csv): ").strip() or 'csv'
                download_sample_data(table, ticker, fmt)
            except:
                print("❌ 無效的選擇")
                
        elif choice == '5':
            print("\n🔄 正在探索所有資料表...")
            for table in KNOWN_TABLES:
                try:
                    explore_table_structure(table, '2330')
                except Exception as e:
                    print(f"❌ {table}: {e}")
                print("\n" + "-" * 70 + "\n")
        else:
            print("❌ 無效的選擇，請輸入 0-5")


def quick_explore_all():
    """快速探索所有資料表（非互動模式）"""
    print_section("快速探索所有資料表")
    
    for table in KNOWN_TABLES:
        try:
            print(f"\n\n{'#'*70}")
            print(f"# {table}")
            print(f"{'#'*70}")
            explore_table_structure(table, '2330')
        except Exception as e:
            print(f"❌ {table}: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == '--info':
            get_account_info()
        elif cmd == '--list':
            list_available_tables()
        elif cmd == '--explore':
            table = sys.argv[2] if len(sys.argv) > 2 else 'TWN/APIPRCD'
            ticker = sys.argv[3] if len(sys.argv) > 3 else '2330'
            explore_table_structure(table, ticker)
        elif cmd == '--download':
            table = sys.argv[2] if len(sys.argv) > 2 else 'TWN/APIPRCD'
            ticker = sys.argv[3] if len(sys.argv) > 3 else '2330'
            download_sample_data(table, ticker)
        elif cmd == '--all':
            quick_explore_all()
        else:
            print("用法:")
            print("  python explore_tej_api.py           # 互動模式")
            print("  python explore_tej_api.py --info    # 查看帳戶資訊")
            print("  python explore_tej_api.py --list    # 列出資料表")
            print("  python explore_tej_api.py --explore TWN/APIPRCD 2330  # 探索特定表")
            print("  python explore_tej_api.py --download TWN/APIPRCD 2330 # 下載範例")
            print("  python explore_tej_api.py --all     # 探索所有表")
    else:
        # 互動模式
        interactive_menu()

