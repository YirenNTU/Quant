#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Shadow Gem Detector V2 的数据获取与计算逻辑
"""

import tejapi
import pandas as pd
from datetime import datetime, timedelta

# TEJ API 設定
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("=" * 70)
print("🧪 Shadow Gem Detector V2 - 数据获取测试")
print("=" * 70)
print()

# 测试股票：聯發科 (2454) - 较容易有籌碼变化
test_ticker = "2454"
print(f"📊 测试股票: {test_ticker} (聯發科)")
print()

# ==========================================
# 测试 1: 月营收数据
# ==========================================
print("-" * 70)
print("测试 1: 月营收数据 (TWN/APISALE)")
print("-" * 70)

try:
    sales_data = tejapi.get(
        'TWN/APISALE',
        coid=test_ticker,
        opts={'limit': 15, 'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(sales_data)} 个月数据")
    
    if 'd0003' in sales_data.columns and 'd0001' in sales_data.columns:
        print(f"\n近 6 个月营收 YoY:")
        print(sales_data.head(6)[['mdate', 'd0001', 'd0003']])
        
        # 计算营收加速度
        if len(sales_data) >= 12:
            recent_3m_yoy = sales_data.loc[0:2, 'd0003'].mean()
            recent_12m_yoy = sales_data.loc[0:11, 'd0003'].mean()
            acceleration = recent_3m_yoy - recent_12m_yoy
            
            print(f"\n🚀 营收加速度计算:")
            print(f"   近 3 个月 YoY 平均: {recent_3m_yoy:.2f}%")
            print(f"   近 12 个月 YoY 平均: {recent_12m_yoy:.2f}%")
            print(f"   营收加速度: {acceleration:+.2f}%")
            
            # 检查营收是否创新高
            latest_rev = sales_data.loc[0, 'd0001']
            past_max_rev = sales_data.loc[1:11, 'd0001'].max()
            is_new_high = latest_rev >= past_max_rev
            print(f"   营收创 12 月新高: {'✅ 是' if is_new_high else '❌ 否'}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 2: 籌碼数据
# ==========================================
print("-" * 70)
print("测试 2: 籌碼数据 (TWN/APISHRACT)")
print("-" * 70)

try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    chip_data = tejapi.get(
        'TWN/APISHRACT',
        coid=test_ticker,
        mdate={'gte': start_date.strftime('%Y-%m-%d'),
               'lte': end_date.strftime('%Y-%m-%d')},
        opts={'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(chip_data)} 天籌碼数据")
    
    # 检查可用欄位
    chip_cols = ['qfii_ex', 'fund_ex', 'qfii_pct', 'fd_pct', 'tot_ex']
    available = [col for col in chip_cols if col in chip_data.columns]
    print(f"可用欄位: {available}")
    print()
    
    if len(chip_data) >= 5:
        print(f"近 5 天籌碼:")
        display_cols = ['mdate'] + available[:4]
        print(chip_data.head(5)[display_cols])
        print()
        
        # 计算近 4 周累积买卖超
        days_to_check = min(20, len(chip_data))
        
        if 'qfii_ex' in chip_data.columns:
            qfii_net = chip_data.loc[0:days_to_check-1, 'qfii_ex'].sum()
            print(f"📊 近 {days_to_check} 天外资累积买卖超: {qfii_net:,.0f} 张")
        
        if 'fund_ex' in chip_data.columns:
            fund_net = chip_data.loc[0:days_to_check-1, 'fund_ex'].sum()
            print(f"📊 近 {days_to_check} 天投信累积买卖超: {fund_net:,.0f} 张")
        
        if 'qfii_pct' in chip_data.columns:
            latest_pct = chip_data.loc[0, 'qfii_pct']
            oldest_pct = chip_data.loc[days_to_check-1, 'qfii_pct']
            pct_change = latest_pct - oldest_pct
            print(f"📊 外资持股比例变化: {pct_change:+.2f}%")
        
        # 判断籌碼趋势
        print()
        if qfii_net > 0 and fund_net > 0:
            print("🔥 籌碼趋势: 雙多 (外资+投信买超)")
        elif qfii_net > 0:
            print("📈 籌碼趋势: 外资买超")
        elif fund_net > 0:
            print("📊 籌碼趋势: 投信买超")
        elif qfii_net < 0 and fund_net < 0:
            print("⚠️  籌碼趋势: 雙空")
        else:
            print("➡️  籌碼趋势: 中性")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 3: PSR 数据
# ==========================================
print("-" * 70)
print("测试 3: PSR 数据 (TWN/APIPRCD)")
print("-" * 70)

try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=750)
    
    price_data = tejapi.get(
        'TWN/APIPRCD',
        coid=test_ticker,
        mdate={'gte': start_date.strftime('%Y-%m-%d'),
               'lte': end_date.strftime('%Y-%m-%d')},
        opts={'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(price_data)} 天股价数据")
    
    if 'psr_tej' in price_data.columns:
        valid_psr = price_data['psr_tej'].dropna()
        print(f"有效 PSR 数据: {len(valid_psr)} 笔")
        
        if len(valid_psr) >= 30:
            current_psr = valid_psr.iloc[0]
            psr_min = valid_psr.min()
            psr_max = valid_psr.max()
            
            percentile = (current_psr - psr_min) / (psr_max - psr_min)
            percentile = max(0, min(1, percentile))
            
            print(f"\n📊 PSR 分析:")
            print(f"   当前 PSR: {current_psr:.2f}")
            print(f"   历史 PSR 范围: {psr_min:.2f} ~ {psr_max:.2f}")
            print(f"   PSR Percentile: {percentile*100:.1f}%")
            
            if percentile < 0.2:
                print("   ✅ 处于历史低档 (< 20%)")
            elif percentile > 0.8:
                print("   ⚠️  处于历史高档 (> 80%)")
            else:
                print("   ➡️  处于历史中位")
    else:
        print("⚠️  缺少 PSR 欄位")
    
    # 计算 RS
    if 'close_d' in price_data.columns and len(price_data) >= 120:
        latest_price = price_data.loc[0, 'close_d']
        past_price = price_data.loc[119, 'close_d']
        
        if pd.notna(latest_price) and pd.notna(past_price) and past_price > 0:
            stock_return = (latest_price / past_price) - 1
            print(f"\n📈 120 天报酬率: {stock_return*100:.2f}%")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 4: 综合评分模拟
# ==========================================
print("-" * 70)
print("测试 4: 综合评分模拟")
print("-" * 70)

# 模拟数据
test_rev_acc = 8.5
test_is_new_high = True
test_qfii_net = 5000
test_fund_net = 2000
test_rs = 0.15
test_psr_percentile = 0.18
test_rd_momentum = 0.002

score = 40  # 基础分
print(f"基础分: {score}")

# 营收加速 (+30)
if test_rev_acc > 5:
    score += 30
    print(f"+ 营收加速 > 5%: +30 分 (加速度 = {test_rev_acc:.1f}%)")
elif test_rev_acc > 0:
    score += 15
    print(f"+ 营收加速 > 0%: +15 分 (加速度 = {test_rev_acc:.1f}%)")

# 籌碼集中 (+20)
if test_qfii_net > 0 and test_fund_net > 0:
    score += 20
    print(f"+ 籌碼雙多: +20 分 (外资 {test_qfii_net:+,} 张, 投信 {test_fund_net:+,} 张)")
elif test_qfii_net > 0 or test_fund_net > 0:
    score += 10
    print(f"+ 籌碼单多: +10 分")

# RS 强度 (+20)
if test_rs > 0.1:
    score += 20
    print(f"+ RS 强度 > 10%: +20 分 (RS = {test_rs*100:.1f}%)")
elif test_rs > 0:
    score += 10
    print(f"+ RS 强度 > 0%: +10 分 (RS = {test_rs*100:.1f}%)")

# 研发动能 (+10)
if test_rd_momentum > 0:
    score += 10
    print(f"+ 研发费用增加: +10 分")

# 价值确认 (+10)
if test_is_new_high and test_psr_percentile < 0.2:
    score += 10
    print(f"+ 营收新高 + PSR 低档: +10 分 (PSR Percentile = {test_psr_percentile*100:.1f}%)")

print()
print(f"💎 总分: {score} 分")

if score >= 100:
    print("   评级: SSS级 - 顶级隐藏宝石")
elif score >= 80:
    print("   评级: S级 - 强势潜力股")
elif score >= 60:
    print("   评级: A级 - 潜力关注")
elif score >= 50:
    print("   评级: B级 - 观察名单")
else:
    print("   评级: C级 - 持续追踪")

print()
print("=" * 70)
print("✅ 测试完成！")
print("=" * 70)

