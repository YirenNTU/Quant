#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Health Checker V2 的数据获取与计算逻辑
"""

import tejapi
import pandas as pd
from datetime import datetime

# TEJ API 設定
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("=" * 70)
print("🧪 Health Checker V2 - 数据获取测试")
print("=" * 70)
print()

# 测试股票：台积电 (2330)
test_ticker = "2330"
print(f"📊 测试股票: {test_ticker} (台积电)")
print()

# ==========================================
# 测试 1: 抓取财务数据
# ==========================================
print("-" * 70)
print("测试 1: 抓取财务数据 (TWN/AINVFINB)")
print("-" * 70)

try:
    fin_data = tejapi.get(
        'TWN/AINVFINB',
        coid=test_ticker,
        opts={'limit': 8, 'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(fin_data)} 季数据")
    print()
    
    # 檢查必要欄位
    required_cols = ['a7210', 'a2402', 'a7300', 'a2200', 'a3100', 'mdate']
    available = [col for col in required_cols if col in fin_data.columns]
    missing = [col for col in required_cols if col not in fin_data.columns]
    
    print(f"可用欄位: {available}")
    if missing:
        print(f"⚠️  缺少欄位: {missing}")
    print()
    
    # 顯示最近 5 季數據
    print("最近 5 季關鍵數據:")
    display_cols = ['mdate'] + [col for col in ['a7210', 'a2402', 'a7300', 'a2200', 'a3100'] if col in fin_data.columns]
    print(fin_data.head(5)[display_cols])
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()
    fin_data = None

# ==========================================
# 测试 2: 计算 CCR_TTM
# ==========================================
if fin_data is not None:
    print("-" * 70)
    print("测试 2: 计算 CCR_TTM (近四季加總)")
    print("-" * 70)
    
    try:
        if len(fin_data) >= 4 and 'a7210' in fin_data.columns and 'a2402' in fin_data.columns:
            # 近 4 季 OCF 加總
            ocf_ttm = fin_data.loc[0:3, 'a7210'].sum()
            
            # 近 4 季淨利加總
            ni_ttm = fin_data.loc[0:3, 'a2402'].sum()
            
            print(f"近 4 季 OCF 加總: {ocf_ttm:,.0f} 千元")
            print(f"近 4 季淨利加總: {ni_ttm:,.0f} 千元")
            
            if ni_ttm > 0:
                ccr_ttm = ocf_ttm / ni_ttm
                print(f"\n💰 CCR_TTM = {ccr_ttm:.2f}")
                
                if ccr_ttm > 1.0:
                    print("   ✅ 優秀！現金流 > 獲利 (CCR > 1.0)")
                elif ccr_ttm > 0.8:
                    print("   ✅ 良好 (CCR > 0.8)")
                elif ccr_ttm > 0.5:
                    print("   ⚠️  普通 (0.5 < CCR < 0.8)")
                else:
                    print("   🛑 警示 (CCR < 0.5)")
            else:
                print("\n⚠️  淨利為負，CCR 參考性低")
        else:
            print("⚠️  數據不足，無法計算 CCR_TTM")
        
        print()
    
    except Exception as e:
        print(f"❌ 计算错误: {e}")
        print()

# ==========================================
# 测试 3: 存货周转天数风险
# ==========================================
if fin_data is not None:
    print("-" * 70)
    print("测试 3: 存货周转天数风险 (自行計算)")
    print("-" * 70)
    
    try:
        if len(fin_data) >= 5 and 'a2200' in fin_data.columns and 'a3100' in fin_data.columns:
            # 計算本季存貨天數 = (存貨 / 營收) * 90
            current_inv = fin_data.loc[0, 'a2200']
            current_rev = fin_data.loc[0, 'a3100']
            current_days = (current_inv / current_rev) * 90 if current_rev != 0 else None
            
            # 計算去年同季存貨天數
            yoy_inv = fin_data.loc[4, 'a2200']
            yoy_rev = fin_data.loc[4, 'a3100']
            yoy_days = (yoy_inv / yoy_rev) * 90 if yoy_rev != 0 else None
            
            if current_days is not None and yoy_days is not None:
                print(f"本季存貨: {current_inv:,.0f} 千元 | 營收: {current_rev:,.0f} 千元")
                print(f"本季存貨天數: {current_days:.1f} 天")
                print(f"\n去年同季存貨天數: {yoy_days:.1f} 天")
                
                days_change = current_days - yoy_days
                print(f"\n📦 變化: {days_change:+.1f} 天")
                
                if days_change > 15:
                    print("   🛑 高風險！存貨積壓嚴重")
                elif days_change > 5:
                    print("   ⚠️  留意，存貨天數微升")
                elif days_change < -5:
                    print("   ✅ 健康！存貨週轉改善")
                else:
                    print("   ✅ 健康，存貨穩定")
            else:
                print("⚠️  無法計算存貨天數")
        else:
            print("⚠️  數據不足或缺少存貨/營收欄位")
        
        print()
    
    except Exception as e:
        print(f"❌ 计算错误: {e}")
        print()

# ==========================================
# 测试 4: FCF 計算
# ==========================================
if fin_data is not None:
    print("-" * 70)
    print("测试 4: 自由现金流 (FCF)")
    print("-" * 70)
    
    try:
        if 'a7210' in fin_data.columns and 'a7300' in fin_data.columns:
            ocf = fin_data.loc[0, 'a7210']
            icf = fin_data.loc[0, 'a7300']
            
            print(f"營業現金流 (OCF): {ocf:,.0f} 千元")
            print(f"投資現金流 (ICF): {icf:,.0f} 千元")
            
            # CapEx 估算 (ICF 為負表示支出)
            capex = abs(icf) if icf < 0 else 0
            fcf = ocf - capex
            
            print(f"CapEx (估算): {capex:,.0f} 千元")
            print(f"\n💵 FCF = {fcf:,.0f} 千元")
            
            if fcf > 0:
                print("   ✅ 正流入！公司有真實現金進帳")
            elif capex > ocf * 1.5:
                print("   ⚠️  負流出，但可能是擴產投資")
            else:
                print("   🛑 負流出，體質較弱")
        else:
            print("⚠️  缺少 OCF 或 ICF 欄位")
        
        print()
    
    except Exception as e:
        print(f"❌ 计算错误: {e}")
        print()

# ==========================================
# 测试 5: 綜合評分
# ==========================================
print("-" * 70)
print("测试 5: 綜合評分模擬")
print("-" * 70)

# 模擬數據
test_ccr_ttm = 1.15
test_fcf = 500000000  # 50萬千元 = 5000億
test_inv_days_change = -3  # 改善 3 天

score = 60  # 基礎分
print(f"基礎分: {score}")

# CCR_TTM 評分
if test_ccr_ttm > 0.8:
    score += 20
    print(f"+ CCR_TTM > 0.8: +20 分 (CCR = {test_ccr_ttm:.2f})")
    
    if test_ccr_ttm > 1.0:
        score += 10
        print(f"+ CCR_TTM > 1.0: +10 分 (額外加分)")

# FCF 評分
if test_fcf > 0:
    score += 10
    print(f"+ FCF > 0: +10 分 (FCF = {test_fcf/1000000:.0f} 百萬)")

# 存貨風險評分
if test_inv_days_change > 15:
    score -= 20
    print(f"- 存貨惡化 > 15天: -20 分")
elif test_inv_days_change > 5:
    score -= 10
    print(f"- 存貨惡化 5-15天: -10 分")
else:
    print(f"+ 存貨健康: 0 分 (變化 = {test_inv_days_change:+.1f}天)")

print()
print(f"🏆 總分: {score} 分")

if score >= 90:
    print("   評級: S級 - 優質生")
elif score >= 80:
    print("   評級: A級 - 質優生")
elif score >= 70:
    print("   評級: B級 - 正常")
elif score >= 40:
    print("   評級: C級 - 警示")
else:
    print("   評級: D級 - 高風險")

print()
print("=" * 70)
print("✅ 測試完成！")
print("=" * 70)

