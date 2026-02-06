#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Pool Analyser V2 的数据获取与计算逻辑
"""

import tejapi
import pandas as pd
from datetime import datetime

# TEJ API 設定
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("=" * 70)
print("🧪 Pool Analyser V2 - 数据获取测试")
print("=" * 70)
print()

# 测试股票：台积电 (2330)
test_ticker = "2330"
print(f"📊 测试股票: {test_ticker} (台积电)")
print()

# ==========================================
# 测试 1: 抓取季度财务数据
# ==========================================
print("-" * 70)
print("测试 1: 抓取季度财务数据 (TWN/AINVFINB)")
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
    print("最近 5 季数据:")
    print(fin_data.head(5)[['mdate', 'r105', 'r106', 'r112']])
    print()
    
    # 计算 YoY 斜率
    if len(fin_data) >= 5:
        gpm_latest = fin_data.loc[0, 'r105']
        gpm_yoy = fin_data.loc[4, 'r105']
        gpm_slope = gpm_latest - gpm_yoy
        
        opm_latest = fin_data.loc[0, 'r106']
        opm_yoy = fin_data.loc[4, 'r106']
        opm_slope = opm_latest - opm_yoy
        
        ol = opm_slope / gpm_slope if abs(gpm_slope) > 0.01 else 0
        
        print(f"📈 YoY 斜率计算结果:")
        print(f"   GPM: {gpm_latest:.2f}% (去年同季: {gpm_yoy:.2f}%) → 斜率: {gpm_slope:+.2f}%")
        print(f"   OPM: {opm_latest:.2f}% (去年同季: {opm_yoy:.2f}%) → 斜率: {opm_slope:+.2f}%")
        print(f"   Operating Leverage: {ol:.2f}")
        print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 2: 抓取月营收数据
# ==========================================
print("-" * 70)
print("测试 2: 抓取月营收数据 (TWN/APISALE)")
print("-" * 70)

try:
    sales_data = tejapi.get(
        'TWN/APISALE',
        coid=test_ticker,
        opts={'limit': 15, 'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(sales_data)} 个月数据")
    print()
    print("最近 12 个月营收 YoY:")
    print(sales_data.head(12)[['mdate', 'd0001', 'd0003']])
    print()
    
    # 计算月营收动能
    if len(sales_data) >= 12:
        recent_3m_yoy = sales_data.loc[0:2, 'd0003'].mean()
        recent_12m_yoy = sales_data.loc[0:11, 'd0003'].mean()
        momentum = recent_3m_yoy - recent_12m_yoy
        
        print(f"🚀 月营收动能计算结果:")
        print(f"   近 3 个月 YoY 平均: {recent_3m_yoy:.2f}%")
        print(f"   近 12 个月 YoY 平均: {recent_12m_yoy:.2f}%")
        print(f"   营收动能: {momentum:+.2f}%")
        print()
        
        if momentum > 5:
            print("   ✅ 营收加速！(动能 > 5%)")
        elif momentum > 0:
            print("   ➡️  营收持平")
        else:
            print("   ⚠️  营收减速")

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 3: 评分计算
# ==========================================
print()
print("-" * 70)
print("测试 3: 评分制计算")
print("-" * 70)

# 模拟数据
test_metrics = {
    'gpm_slope_yoy': 2.5,
    'opm_slope_yoy': 3.8,
    'operating_leverage': 1.52,
    'non_operating_ratio': 0.15
}
test_rev_momentum = 8.5

score = 60  # 基础分
print(f"基础分: {score}")

# OL > 1.2
if test_metrics['operating_leverage'] > 1.2:
    score += 20
    print(f"+ OL > 1.2: +20 分 (OL = {test_metrics['operating_leverage']:.2f})")

# GPM YoY > 0
if test_metrics['gpm_slope_yoy'] > 0:
    score += 10
    print(f"+ GPM YoY > 0: +10 分 (斜率 = {test_metrics['gpm_slope_yoy']:+.2f}%)")

# OPM YoY > 0
if test_metrics['opm_slope_yoy'] > 0:
    score += 10
    print(f"+ OPM YoY > 0: +10 分 (斜率 = {test_metrics['opm_slope_yoy']:+.2f}%)")

# 月营收加速 > 5%
if test_rev_momentum > 5:
    score += 10
    print(f"+ 月营收加速 > 5%: +10 分 (动能 = {test_rev_momentum:+.2f}%)")

# 业外比重 <= 30%
if test_metrics['non_operating_ratio'] <= 0.3:
    score += 10
    print(f"+ 业外比重 <= 30%: +10 分 (比重 = {test_metrics['non_operating_ratio']*100:.1f}%)")

print()
print(f"🏆 总分: {score} 分")

if score >= 90:
    print("   评级: SSS级 - 结构性扩张")
elif score >= 80:
    print("   评级: S级/A级 - 强势转强")
elif score >= 70:
    print("   评级: B级 - 潜力关注")
else:
    print("   评级: C级 - 持续观察")

print()
print("=" * 70)
print("✅ 测试完成！")
print("=" * 70)

