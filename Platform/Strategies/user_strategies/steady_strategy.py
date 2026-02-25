#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 均值回歸策略 - Mean Reversion Strategy
================================================================================

核心原理：
  市場在無趨勢（橫盤震盪）下，價格會回歸均值。
  RSI 過冷做多、過熱迴避，價格回到布林中軌附近出場。

關鍵安全機制 — 趨勢濾網：
  趨勢明確時均值回歸會被打爆，因此必須過濾：
  1) MA200 斜率 < 0 → 空頭趨勢，不做均值回歸
  2) ADX > 30 → 趨勢太強，不做均值回歸
  兩道濾網同時通過才給分，避免在單邊行情中接刀

因子結構：
  1) RSI 超賣訊號 (40%)：RSI-14 越低分越高，RSI<30 最強
  2) Bollinger 偏離 (30%)：價格在布林帶下緣 → 回歸空間大
  3) 短期跌深 (15%)：5-10 日跌幅 → 短期超跌反彈
  4) 籌碼確認 (15%)：法人逆勢買超 → 確認不是基本面惡化

全盤選股（不限產業），週頻調倉
================================================================================
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Platform.Strategies import Strategy
from Platform.Factors import *


class SteadyStrategy(Strategy):

    name = "均值回歸策略"
    description = "RSI超賣+布林下緣回歸，趨勢濾網保護"
    version = "4.0"
    author = "Investment AI"

    params = {
        "rsi_weight": 0.40,
        "boll_weight": 0.30,
        "drop_weight": 0.15,
        "chip_weight": 0.15,
    }

    def compute(self, db):
        """
        Level 2: Regime Switching + Dynamic Exposure
        - Bull: value + momentum + chip (trend following flavor)
        - Range: mean reversion (reversal + bollinger + chip confirm)
        - Bear: default cash (scores -> 0)
        """

        # =========================
        # 0) 取資料
        # =========================
        close = db.get("close")
        high = db.get("high")
        low = db.get("low")

        pb = db.get("pb")
        daily_return = db.get("daily_return")

        fund_net = db.get("fund_net")
        shares = db.get("shares")

        amount = db.get("amount")
        mktcap = db.get("mktcap")

        tej_opm = db.get("tej_opm")

        industry = load_sector(close, "industry")
        sector = load_sector(close, "sector")

        # =========================
        # 1) 參數
        # =========================
        # factor weights
        vw = self.params.get("value_weight", 0.35)
        gw = self.params.get("growth_weight", 0.45)     # momentum
        cw = self.params.get("chip_weight", 0.20)

        # windows
        ma_n = self.params.get("ma_filter", 60)
        mom_n = self.params.get("mom_periods", 120)

        # regime windows / thresholds
        market_ma = self.params.get("market_ma", 200)
        slope_n = self.params.get("market_slope_periods", 20)
        slope_thr = self.params.get("market_slope_thr", 0.008)  # 0.8% / 20d

        regime_smooth = self.params.get("regime_smooth", 5)     # 平滑天數避免 regime 抖動

        # dynamic exposure by regime
        exp_bull = self.params.get("exposure_bull", 1.00)
        exp_range = self.params.get("exposure_range", 0.70)
        exp_bear = self.params.get("exposure_bear", 0.00)       # 預設空手（你想做小反彈可改 0.2）

        # protection
        crash5_thr = self.params.get("crash5_thr", -0.12)
        crash20_thr = self.params.get("crash20_thr", -0.20)

        # turnover control
        smooth_bull = self.params.get("smooth_bull", 20)
        smooth_range = self.params.get("smooth_range", 20)
        smooth_mix = self.params.get("smooth_mix", 20)

        # optional: if your engine supports "all-zero => cash", this helps
        cash_mode = self.params.get("cash_mode", True)                 # True: bear 時分數壓到 0
        score_floor = self.params.get("score_floor", 0.0)              # <0 => 0
        min_active_exposure = self.params.get("min_active_exposure", 0.05)  # 曝險低於這個就視為空手

        # =========================
        # 2) 小工具：縮尾
        # =========================
        def w(x):
            return winsorize(x, 0.01, 0.99)

        # =========================
        # 3) 市場 proxy（市值加權）
        # =========================
        market = safe_divide((close * mktcap).sum(axis=1), mktcap.sum(axis=1), fill=0)  # Series
        market_maN = market.rolling(market_ma).mean()
        market_slope = market_maN.pct_change(slope_n)  # Series

        # 平滑 slope（避免 regime 抖動）
        market_slope_s = market_slope.rolling(regime_smooth).mean()

        market_above = market > market_maN
        slope_pos = market_slope_s > slope_thr
        slope_flat = abs_val(market_slope_s) <= slope_thr

        # ===== Regime 定義 =====
        is_bull = (market_above & slope_pos).astype(float)   # bull trend
        is_range = (market_above & slope_flat).astype(float) # range / mild up but flat slope
        is_bear = (~market_above).astype(float)              # bear / risk-off

        # 讓三者加總不超過 1（避免極端情況重疊）
        # bull 優先，其次 range，剩下 bear
        is_range = is_range * (1 - is_bull)
        is_bear = 1 - is_bull - is_range

        # 曝險（Series）
        exposure = exp_bull * is_bull + exp_range * is_range + exp_bear * is_bear
        exposure = exposure.clip(0, 1)

        # broadcast to DataFrame
        exposure_df = (close * 0).add(exposure, axis=0)

        # =========================
        # 4) Bull 模型（趨勢/成長）
        # =========================
        # Value: PB低越好（產業內），加上輕量 quality gate
        value = 1 - rank(w(pb), industry)
        quality_gate = tej_opm.isna() | (tej_opm > 0)
        value = if_else(quality_gate, value, value * 0.5)

        # Momentum: N日報酬
        mom = rank(w(ts_pct_change(close, mom_n)), industry)

        # Chip: 投信流（張->股/流通股）
        fund_flow = safe_divide(fund_net * 1000, shares, fill=0)
        chip_raw = rank(w(ts_sum(fund_flow, 10)), industry)
        chip_z = rank(w(ts_zscore(ts_mean(fund_flow, 10), 120)), industry)
        chip = 0.5 * chip_raw + 0.5 * chip_z

        # Trend filter (個股)：跌破 MA_n 降曝險（軟門檻）
        trend_ok = close > ts_mean(close, ma_n)
        trend_mult = 0.5 + 0.5 * trend_ok.astype(float)  # 0.5~1.0

        # 波動折扣（sector 中性）
        vol = w(ts_std(daily_return, 60))
        vol_score = 1 - rank(vol, sector)
        risk_mult = 0.6 + 0.4 * vol_score  # 0.6~1.0

        # 流動性折扣
        liq = rank(w(ts_mean(amount, 20)), industry)
        liq_mult = 0.8 + 0.2 * liq

        bull_core = vw * value + gw * mom + cw * chip
        bull_score = bull_core * trend_mult * risk_mult * liq_mult

        # 急跌保護（個股）
        crash5 = ts_pct_change(close, 5) < crash5_thr
        crash20 = ts_pct_change(close, 20) < crash20_thr
        bull_score = if_else(crash5 | crash20, 0, bull_score)

        # 平滑（降換手）
        bull_score = decay_exp(bull_score, smooth_bull)

        # =========================
        # 5) Range 模型（均值回歸）
        # =========================
        # 反轉：5~10日跌深（跌越多越買）
        rev_5 = 1 - rank(w(ts_pct_change(close, 5)), industry)
        rev_10 = 1 - rank(w(ts_pct_change(close, 10)), industry)
        reversal = 0.6 * rev_5 + 0.4 * rev_10

        # 布林下緣：越靠下緣越買
        boll_pos = bollinger_position(close, 20, 2.0)  # <0 below lower band
        boll_score = 1 - rank(w(boll_pos), industry)
        below_lower = (boll_pos < 0).astype(float) * 0.2
        boll_score = rank(w(boll_score + below_lower), industry)

        # 籌碼確認：用較穩的 chip_z
        chip_confirm = chip_z

        range_score = 0.50 * reversal + 0.30 * boll_score + 0.20 * chip_confirm

        # 盤整策略也避開崩盤
        crash_fast = ts_pct_change(close, 5) < -0.15
        crash_slow = ts_pct_change(close, 20) < -0.30
        range_score = if_else(crash_fast | crash_slow, 0, range_score)

        # 平滑（降換手）
        range_score = decay_exp(range_score, smooth_range)

        # =========================
        # 6) Regime 切換（硬切換 + 動態曝險）
        # =========================
        # broadcast regime mask
        is_bull_df = (close * 0).add(is_bull, axis=0)
        is_range_df = (close * 0).add(is_range, axis=0)
        is_bear_df = (close * 0).add(is_bear, axis=0)

        raw_total = is_bull_df * bull_score + is_range_df * range_score

        # Bear：預設空手（讓分數=0）
        if cash_mode:
            raw_total = if_else(is_bear_df > 0, 0, raw_total)

        # 動態曝險倍率（若你的下單引擎支援空手/部分現金，這會真正生效）
        total = raw_total * exposure_df

        # 再平滑一次（避免 regime 邊界抖動造成換手）
        total = decay_exp(total, smooth_mix)

        # =========================
        # 7) 輸出標準化（0~1）
        # =========================
        # 下限截斷
        total = if_else(total < score_floor, 0, total)

        # 若曝險非常低，直接全 0（空手）
        if cash_mode:
            low_exp = exposure < min_active_exposure  # Series
            low_exp_df = (close * 0).add(low_exp.astype(float), axis=0)
            total = if_else(low_exp_df > 0, 0, total)

        # 截面 rank -> [0,1]
        total = rank(w(total), group=None)

        return total.fillna(0)
    def filter_universe(self, db):
        """
        全盤選股，不限產業。
        只設基本流動性門檻，確保均值回歸訊號可以成交。
        """
        close = db.get('close')
        volume = db.get('volume')
        mktcap = db.get('mktcap')

        daily_amount = close * volume
        min_amount_filter = ts_mean(daily_amount, 20) > 5_000_000
        price_filter = close.iloc[-1] > 10
        mktcap_filter = mktcap.iloc[-1].fillna(0) > 3_000_000_000

        return min_amount_filter & price_filter & mktcap_filter


# ═══════════════════════════════════════════════════════════════════════════════
# 執行區塊
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    from Platform import Backtester, get_allocation

    print("=" * 70)
    print(f"📊 執行策略: {SteadyStrategy.name}")
    print("=" * 70)

    strategy = SteadyStrategy(top_n=15)

    print("\n🔄 執行回測...")

    result = Backtester.run(
        strategy=strategy,
        start_date="2021-03-01",
        end_date=None,
        initial_capital=100_000,
        rebalance_freq="weekly",
        allow_fractional=True,
    )

    print(result.summary())

    result.plot(save_path="performance_steady.png")
    print("📊 績效圖已儲存至 performance_steady.png")

    print("\n📈 當前配置建議:")

    allocation = get_allocation(
        strategy=strategy,
        capital=100_000,
        max_positions=15,
        allow_fractional=True,
    )

    print(allocation)
