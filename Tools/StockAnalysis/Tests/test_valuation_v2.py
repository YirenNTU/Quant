#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Valuation Analyzer V2 的数据获取与计算逻辑
"""

import tejapi
import pandas as pd
from datetime import datetime, timedelta

# TEJ API 設定
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print("=" * 70)
print("🧪 Valuation Analyzer V2 - 数据获取测试")
print("=" * 70)
print()

# ==========================================
# 测试 1: 市场状态判断 (0050 vs MA200)
# ==========================================
print("-" * 70)
print("测试 1: 市场状态判断 (0050 vs MA200)")
print("-" * 70)

prices = None
bench_return = None

try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=400)  # 抓更多天确保有 200 天数据
    
    benchmark_data = tejapi.get(
        'TWN/APIPRCD',
        coid='0050',
        mdate={'gte': start_date.strftime('%Y-%m-%d'),
               'lte': end_date.strftime('%Y-%m-%d')},
        opts={'sort': 'mdate.asc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(benchmark_data)} 天 0050 数据")
    
    if 'close_d' in benchmark_data.columns and len(benchmark_data) >= 200:
        prices = benchmark_data['close_d'].dropna()
        
        ma200 = prices.iloc[-200:].mean()
        current_price = prices.iloc[-1]
        distance_pct = (current_price - ma200) / ma200 * 100
        
        print(f"\n🏛️ 市场状态分析:")
        print(f"   0050 收盘价: {current_price:.2f}")
        print(f"   MA200: {ma200:.2f}")
        print(f"   距离 MA200: {distance_pct:+.2f}%")
        print()
        
        if current_price > ma200:
            print("   📈 判断: 🐂 牛市 (BULL)")
            print("   → RS 门槛: > 1.05 (强者恒强)")
            market_regime = 'Bull'
        else:
            print("   📉 判断: 🐻 熊市 (BEAR)")
            print("   → RS 门槛: > 0.95 (抗跌即可)")
            market_regime = 'Bear'
    else:
        print("⚠️  数据不足，无法判断市场状态")
        market_regime = 'Neutral'
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    market_regime = 'Neutral'
    print()

# ==========================================
# 测试 2: 个股 RS Ratio 计算
# ==========================================
test_ticker = "2330"
print("-" * 70)
print(f"测试 2: 个股 RS Ratio 计算 ({test_ticker})")
print("-" * 70)

try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=200)
    
    stock_data = tejapi.get(
        'TWN/APIPRCD',
        coid=test_ticker,
        mdate={'gte': start_date.strftime('%Y-%m-%d'),
               'lte': end_date.strftime('%Y-%m-%d')},
        opts={'sort': 'mdate.desc'},
        paginate=True
    )
    
    print(f"✅ 成功抓取 {len(stock_data)} 天 {test_ticker} 数据")
    
    if 'close_d' in stock_data.columns and len(stock_data) >= 120:
        # 个股报酬
        stock_latest = stock_data.loc[0, 'close_d']
        stock_past = stock_data.loc[119, 'close_d']
        stock_return = (stock_latest / stock_past) - 1
        
        # 大盘报酬 (使用之前的 benchmark_data)
        if prices is not None and len(prices) >= 120:
            bench_latest = prices.iloc[-1]
            bench_past = prices.iloc[-120]
            bench_return = (bench_latest / bench_past) - 1
        else:
            bench_return = 0.1  # 默认值
        
        # RS Ratio
        rs_ratio = (1 + stock_return) / (1 + bench_return)
        
        print(f"\n📊 RS Ratio 计算:")
        print(f"   {test_ticker} 120天报酬: {stock_return*100:.2f}%")
        print(f"   0050 120天报酬: {bench_return*100:.2f}%")
        print(f"   RS Ratio: {rs_ratio:.3f}")
        print()
        
        # 根据市场状态评估
        if market_regime == 'Bull':
            threshold = 1.05
            if rs_ratio > 1.10:
                status = "🚀 极强 (牛市)"
                passed = True
            elif rs_ratio > threshold:
                status = "✅ 强势 (牛市)"
                passed = True
            else:
                status = "⚠️ 未达标 (牛市)"
                passed = False
        else:
            threshold = 0.95
            if rs_ratio > 1.05:
                status = "🛡️ 极抗跌 (熊市)"
                passed = True
            elif rs_ratio > threshold:
                status = "✅ 抗跌 (熊市)"
                passed = True
            else:
                status = "🛑 不抗跌 (熊市)"
                passed = False
        
        print(f"   RS 状态: {status}")
        print(f"   通过门槛: {'✅ 是' if passed else '❌ 否'} (门槛 = {threshold})")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 3: PE/PB Percentile 计算
# ==========================================
print("-" * 70)
print(f"测试 3: PE/PB Percentile 计算 ({test_ticker})")
print("-" * 70)

try:
    if stock_data is not None:
        # PE Percentile
        if 'per' in stock_data.columns:
            valid_pe = stock_data['per'].dropna()
            valid_pe = valid_pe[(valid_pe > 0) & (valid_pe < 200)]
            
            if len(valid_pe) >= 30:
                current_pe = valid_pe.iloc[0]
                pe_min = valid_pe.min()
                pe_max = valid_pe.max()
                pe_percentile = (current_pe - pe_min) / (pe_max - pe_min)
                
                print(f"📊 PE 分析:")
                print(f"   当前 PE: {current_pe:.2f}")
                print(f"   历史范围: {pe_min:.2f} ~ {pe_max:.2f}")
                print(f"   PE Percentile: {pe_percentile*100:.1f}%")
                
                if pe_percentile < 0.3:
                    print("   ✅ 估值: 低估")
                elif pe_percentile > 0.7:
                    print("   ⚠️  估值: 高估")
                else:
                    print("   ➡️  估值: 合理")
                print()
        
        # PB Percentile
        if 'pbr' in stock_data.columns:
            valid_pb = stock_data['pbr'].dropna()
            valid_pb = valid_pb[(valid_pb > 0) & (valid_pb < 50)]
            
            if len(valid_pb) >= 30:
                current_pb = valid_pb.iloc[0]
                pb_min = valid_pb.min()
                pb_max = valid_pb.max()
                pb_percentile = (current_pb - pb_min) / (pb_max - pb_min)
                
                print(f"📊 PB 分析:")
                print(f"   当前 PB: {current_pb:.2f}")
                print(f"   历史范围: {pb_min:.2f} ~ {pb_max:.2f}")
                print(f"   PB Percentile: {pb_percentile*100:.1f}%")
                print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# ==========================================
# 测试 4: 决策矩阵模拟
# ==========================================
print("-" * 70)
print("测试 4: 决策矩阵模拟")
print("-" * 70)

# 模拟不同情境
scenarios = [
    {"regime": "Bull", "pe_pct": 0.2, "rs_ratio": 1.12, "rs_pass": True},
    {"regime": "Bull", "pe_pct": 0.2, "rs_ratio": 1.02, "rs_pass": False},
    {"regime": "Bear", "pe_pct": 0.2, "rs_ratio": 0.98, "rs_pass": True},
    {"regime": "Bear", "pe_pct": 0.2, "rs_ratio": 0.88, "rs_pass": False},
    {"regime": "Bull", "pe_pct": 0.8, "rs_ratio": 0.95, "rs_pass": False},
]

print("\n📋 决策矩阵测试:")
print("-" * 60)
print(f"{'市场':<8} {'估值%':<8} {'RS Ratio':<10} {'RS通过':<8} {'决策':<20}")
print("-" * 60)

for s in scenarios:
    regime = s['regime']
    pe_pct = s['pe_pct']
    rs_ratio = s['rs_ratio']
    rs_pass = s['rs_pass']
    
    is_undervalued = pe_pct < 0.3
    is_overvalued = pe_pct > 0.7
    
    if regime == 'Bull':
        if is_undervalued and rs_pass:
            decision = "🔥 Strong Buy"
        elif is_undervalued:
            decision = "📈 Accumulate"
        elif is_overvalued and not rs_pass:
            decision = "📉 Trim"
        elif is_overvalued and rs_pass:
            decision = "⚠️ Hold (Caution)"
        elif rs_pass:
            decision = "✅ Hold"
        else:
            decision = "➡️ Hold"
    else:  # Bear
        if is_undervalued and rs_pass:
            decision = "📊 Accumulate"
        elif is_undervalued:
            decision = "👀 Watch"
        elif is_overvalued:
            decision = "🛑 Trim"
        elif rs_pass:
            decision = "✅ Hold"
        else:
            decision = "⚠️ Reduce"
    
    print(f"{regime:<8} {pe_pct*100:.0f}%{'':<5} {rs_ratio:<10.3f} {'✅' if rs_pass else '❌':<8} {decision:<20}")

print()
print("=" * 70)
print("✅ 测试完成！")
print("=" * 70)

