#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Forensic Analyzer V2 的数据获取与计算逻辑
"""

import tejapi
import pandas as pd
from datetime import datetime

# TEJ API 設定
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("=" * 70)
print("🧪 Forensic Analyzer V2 - 数据获取测试")
print("=" * 70)
print()

# 测试股票
test_ticker = "2330"
print(f"📊 测试股票: {test_ticker} (台积电)")
print()

# ==========================================
# 测试 1: 财务数据抓取
# ==========================================
print("-" * 70)
print("测试 1: 财务数据抓取 (TWN/AINVFINB)")
print("-" * 70)

try:
    fin_data = tejapi.get(
        'TWN/AINVFINB',
        coid=test_ticker,
        opts={'limit': 8, 'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(fin_data)} 季数据")
    
    # 检查关键栏位
    key_cols = ['a7210', 'a2402', 'a7300', 'a0010', 'a3900', 'a3100', 'a3501', 'r105']
    available = [col for col in key_cols if col in fin_data.columns]
    missing = [col for col in key_cols if col not in fin_data.columns]
    
    print(f"可用栏位: {available}")
    if missing:
        print(f"⚠️  缺少栏位: {missing}")
    print()
    
    # 显示关键数据
    display_cols = ['mdate'] + [col for col in ['a7210', 'a2402', 'a0010', 'a3900'] if col in fin_data.columns]
    print("近 4 季关键数据:")
    print(fin_data.head(4)[display_cols])
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    fin_data = None
    print()

# ==========================================
# 测试 2: Sloan Ratio 计算
# ==========================================
print("-" * 70)
print("测试 2: Sloan Ratio 计算")
print("-" * 70)

if fin_data is not None:
    try:
        fin_data = fin_data.sort_values('mdate', ascending=False).reset_index(drop=True)
        
        net_income = fin_data.loc[0, 'a2402'] if 'a2402' in fin_data.columns else None
        ocf = fin_data.loc[0, 'a7210'] if 'a7210' in fin_data.columns else None
        icf = fin_data.loc[0, 'a7300'] if 'a7300' in fin_data.columns else None
        total_assets = fin_data.loc[0, 'a0010'] if 'a0010' in fin_data.columns else None
        
        print(f"📊 Sloan Ratio 数据:")
        print(f"   税后净利 (a2402): {net_income:,.0f} 千元" if net_income else "   税后净利: N/A")
        print(f"   营业现金流 (a7210): {ocf:,.0f} 千元" if ocf else "   OCF: N/A")
        print(f"   投资现金流 (a7300): {icf:,.0f} 千元" if icf else "   ICF: N/A")
        print(f"   总资产 (a0010): {total_assets:,.0f} 千元" if total_assets else "   总资产: N/A")
        print()
        
        if all(v is not None and pd.notna(v) for v in [net_income, ocf, total_assets]) and total_assets > 0:
            if icf is None or pd.isna(icf):
                icf = 0
            
            sloan_ratio = (net_income - ocf - icf) / abs(total_assets)
            
            print(f"📈 Sloan Ratio = {sloan_ratio:.4f}")
            
            if sloan_ratio > 0.2:
                print("   🛑 盈余品质极差！(> 0.2)")
            elif sloan_ratio > 0.1:
                print("   ⚠️  盈余品质差 (> 0.1)")
            elif sloan_ratio < 0.05:
                print("   ✅ 盈余品质优良 (< 0.05)")
            else:
                print("   ➡️  盈余品质正常")
        print()
    
    except Exception as e:
        print(f"❌ 计算错误: {e}")
        print()

# ==========================================
# 测试 3: 虚胖获利检测
# ==========================================
print("-" * 70)
print("测试 3: 虚胖获利检测")
print("-" * 70)

if fin_data is not None:
    try:
        pretax_income = fin_data.loc[0, 'a3900'] if 'a3900' in fin_data.columns else None
        net_income = fin_data.loc[0, 'a2402'] if 'a2402' in fin_data.columns else None
        
        print(f"📊 虚胖检测数据:")
        print(f"   税前纯益 (a3900): {pretax_income:,.0f} 千元" if pretax_income and pd.notna(pretax_income) else "   税前纯益: N/A")
        print(f"   税后净利 (a2402): {net_income:,.0f} 千元" if net_income and pd.notna(net_income) else "   税后净利: N/A")
        print()
        
        if pretax_income is not None and net_income is not None and pd.notna(pretax_income) and pd.notna(net_income) and net_income != 0:
            hollow_ratio = pretax_income / net_income
            quality_warning = hollow_ratio < 0.5
            
            print(f"📈 本业获利比 = {hollow_ratio*100:.1f}%")
            
            if quality_warning:
                print("   🛑 虚胖警示！获利多来自业外")
            elif hollow_ratio > 1.0:
                print("   ✅ 本业强劲（可能有税务效益）")
            else:
                print("   ✅ 获利结构正常")
        print()
    
    except Exception as e:
        print(f"❌ 计算错误: {e}")
        print()

# ==========================================
# 测试 4: F-Score 简化计算
# ==========================================
print("-" * 70)
print("测试 4: Piotroski F-Score 简化计算")
print("-" * 70)

if fin_data is not None and len(fin_data) >= 5:
    try:
        f_score = 0
        details = []
        
        ni = fin_data.loc[0, 'a2402']
        ta = fin_data.loc[0, 'a0010']
        ocf = fin_data.loc[0, 'a7210']
        
        ni_yoy = fin_data.loc[4, 'a2402']
        ta_yoy = fin_data.loc[4, 'a0010']
        
        # 1. ROA > 0
        if ni is not None and ta is not None and ta > 0:
            roa = ni / ta
            if roa > 0:
                f_score += 1
                details.append("ROA > 0 ✅")
            else:
                details.append("ROA <= 0 ❌")
        
        # 2. OCF > 0
        if ocf is not None and ocf > 0:
            f_score += 1
            details.append("OCF > 0 ✅")
        else:
            details.append("OCF <= 0 ❌")
        
        # 3. ROA 增加 (YoY)
        if all(v is not None and pd.notna(v) for v in [ni, ta, ni_yoy, ta_yoy]) and ta > 0 and ta_yoy > 0:
            roa_curr = ni / ta
            roa_yoy = ni_yoy / ta_yoy
            if roa_curr > roa_yoy:
                f_score += 1
                details.append("ROA 增加 ✅")
            else:
                details.append("ROA 下降 ❌")
        
        # 4. OCF > Net Income
        if ocf is not None and ni is not None and ocf > ni:
            f_score += 1
            details.append("OCF > NI ✅")
        else:
            details.append("OCF <= NI ❌")
        
        # 简化：假设杠杆/流动性 +3
        f_score += 3
        details.append("杠杆/流动性 +3 (简化)")
        
        print(f"📈 F-Score = {f_score}/9")
        print()
        for d in details:
            print(f"   {d}")
        print()
        
        if f_score >= 7:
            print("   🏆 财务实力强劲！")
        elif f_score >= 4:
            print("   ✅ 财务实力正常")
        else:
            print("   ⚠️  财务实力弱")
        print()
    
    except Exception as e:
        print(f"❌ 计算错误: {e}")
        print()

# ==========================================
# 测试 5: Forensic Score 综合评分模拟
# ==========================================
print("-" * 70)
print("测试 5: Forensic Score 综合评分模拟")
print("-" * 70)

# 模拟不同情境
scenarios = [
    {"sloan": 0.03, "f_score": 8, "hollow": 1.1, "roic": 0.18},
    {"sloan": 0.12, "f_score": 6, "hollow": 0.85, "roic": 0.10},
    {"sloan": 0.08, "f_score": 3, "hollow": 0.90, "roic": 0.12},
    {"sloan": 0.15, "f_score": 5, "hollow": 0.40, "roic": 0.08},
    {"sloan": 0.25, "f_score": 2, "hollow": 0.35, "roic": 0.05},
]

print("\n📋 Forensic Score 模拟计算:")
print("-" * 80)
print(f"{'Sloan':<8} {'F-Score':<10} {'Hollow%':<10} {'ROIC%':<8} {'Score':<8} {'评级':<20}")
print("-" * 80)

for s in scenarios:
    sloan = s['sloan']
    f_score = s['f_score']
    hollow = s['hollow']
    roic = s['roic']
    quality_warning = hollow < 0.5
    
    # 计算分数
    score = 80  # 基础分
    
    # Sloan 惩罚
    if sloan > 0.2:
        score -= 25
    elif sloan > 0.1:
        score -= 15
    elif sloan < 0.05:
        score += 5
    
    # F-Score
    if f_score < 4:
        score -= 20
    elif f_score >= 7:
        score += 10
    
    # 虚胖
    if quality_warning:
        score -= 25
    
    # ROIC
    if roic > 0.15:
        score += 10
    
    score = max(0, min(100, score))
    
    # 评级
    if score >= 90:
        verdict = "AAA 优质"
    elif score >= 80:
        verdict = "AA 健康"
    elif score >= 70:
        verdict = "A 正常"
    elif score >= 60:
        verdict = "B 留意"
    elif score >= 40:
        verdict = "C 风险"
    else:
        verdict = "D 高风险"
    
    print(f"{sloan:<8.2f} {f_score:<10} {hollow*100:<10.0f} {roic*100:<8.0f} {score:<8} {verdict:<20}")

print()
print("=" * 70)
print("✅ 测试完成！")
print("=" * 70)

