#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Factor Operators - 因子運算工具庫
================================================================================

提供量化因子計算所需的各種運算函數。

函數分類:
- 時序運算 (Time-Series): ts_zscore, ts_delta, ts_rank, ts_mean, ts_std, ts_sum, ts_max, ts_min
- 截面運算 (Cross-Section): zscore, rank, demean, neutralize
- 衰減運算 (Decay): decay_linear, decay_exp
- 基礎運算 (Basic): 支援 +, -, *, / 運算

使用方式:
>>> from Platform.Factors.operators import *
>>> from Platform.Core.build_field_database import FieldDB
>>> 
>>> db = FieldDB()
>>> close = db.get('close')
>>> volume = db.get('volume')
>>> 
>>> # 計算 20 日動量
>>> momentum = ts_delta(close, 20) / ts_delay(close, 20)
>>> 
>>> # 計算 Z-score 標準化
>>> vol_zscore = zscore(volume)
>>> 
>>> # 計算線性衰減加權
>>> weighted_ret = decay_linear(ts_delta(close, 1) / ts_delay(close, 1), 20)

Author: Investment AI Platform
Version: 1.0
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Union, Optional, List
import warnings
warnings.filterwarnings('ignore')


# ═══════════════════════════════════════════════════════════════════════════════
# 類型定義
# ═══════════════════════════════════════════════════════════════════════════════

DataType = Union[pd.DataFrame, pd.Series]


# ═══════════════════════════════════════════════════════════════════════════════
# 時序運算 (Time-Series Operators)
# ═══════════════════════════════════════════════════════════════════════════════

def ts_delay(data: DataType, periods: int = 1) -> DataType:
    """
    時序延遲 - 取得 N 期前的值
    
    Args:
        data: DataFrame 或 Series
        periods: 延遲期數 (正數表示過去)
    
    Returns:
        延遲後的資料
    
    Example:
        >>> yesterday_close = ts_delay(close, 1)
    """
    return data.shift(periods)


def ts_delta(data: DataType, periods: int = 1) -> DataType:
    """
    時序差分 - 計算與 N 期前的差值
    
    Args:
        data: DataFrame 或 Series
        periods: 差分期數
    
    Returns:
        差分後的資料 (今日值 - N期前的值)
    
    Example:
        >>> price_change_5d = ts_delta(close, 5)
    """
    return data - data.shift(periods)


def ts_pct_change(data: DataType, periods: int = 1) -> DataType:
    """
    時序百分比變化 - 計算與 N 期前的百分比變化
    
    Args:
        data: DataFrame 或 Series
        periods: 期數
    
    Returns:
        百分比變化 (小數形式)
    
    Example:
        >>> daily_return = ts_pct_change(close, 1)
    """
    return data.pct_change(periods)


def ts_mean(data: DataType, window: int) -> DataType:
    """
    時序移動平均
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        移動平均值
    
    Example:
        >>> ma20 = ts_mean(close, 20)
    """
    return data.rolling(window=window, min_periods=1).mean()


def ts_sum(data: DataType, window: int) -> DataType:
    """
    時序移動加總
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        移動加總值
    
    Example:
        >>> volume_5d = ts_sum(volume, 5)
    """
    return data.rolling(window=window, min_periods=1).sum()


def ts_std(data: DataType, window: int) -> DataType:
    """
    時序移動標準差
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        移動標準差
    
    Example:
        >>> volatility = ts_std(daily_return, 20)
    """
    return data.rolling(window=window, min_periods=2).std()


def ts_max(data: DataType, window: int) -> DataType:
    """
    時序移動最大值
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        移動最大值
    
    Example:
        >>> high_20d = ts_max(high, 20)
    """
    return data.rolling(window=window, min_periods=1).max()


def ts_min(data: DataType, window: int) -> DataType:
    """
    時序移動最小值
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        移動最小值
    
    Example:
        >>> low_20d = ts_min(low, 20)
    """
    return data.rolling(window=window, min_periods=1).min()


def ts_argmax(data: DataType, window: int) -> DataType:
    """
    時序最大值位置 - 最大值出現在幾期前
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        最大值距今期數 (0 表示今天)
    
    Example:
        >>> days_since_high = ts_argmax(close, 20)
    """
    return data.rolling(window=window, min_periods=1).apply(
        lambda x: window - 1 - np.argmax(x), raw=True
    )


def ts_argmin(data: DataType, window: int) -> DataType:
    """
    時序最小值位置 - 最小值出現在幾期前
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        最小值距今期數 (0 表示今天)
    
    Example:
        >>> days_since_low = ts_argmin(close, 20)
    """
    return data.rolling(window=window, min_periods=1).apply(
        lambda x: window - 1 - np.argmin(x), raw=True
    )


def ts_rank(data: DataType, window: int) -> DataType:
    """
    時序排名 - 當前值在過去 N 期中的排名百分位
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        排名百分位 (0~1，1 表示最高)
    
    Example:
        >>> price_rank = ts_rank(close, 20)  # 當前價格在過去20天的排名
    """
    def _rank_pct(x):
        if len(x) < 2:
            return 0.5
        return (np.argsort(np.argsort(x))[-1] + 1) / len(x)
    
    return data.rolling(window=window, min_periods=2).apply(_rank_pct, raw=True)


def ts_zscore(data: DataType, window: int) -> DataType:
    """
    時序 Z-Score 標準化 - 基於過去 N 期的均值和標準差
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        Z-Score 標準化後的值
    
    Example:
        >>> vol_zscore = ts_zscore(volume, 20)
    """
    mean = ts_mean(data, window)
    std = ts_std(data, window)
    return (data - mean) / std.replace(0, np.nan)


def ts_corr(x: DataType, y: DataType, window: int) -> DataType:
    """
    時序滾動相關係數
    
    Args:
        x: 第一個變數
        y: 第二個變數
        window: 窗口期數
    
    Returns:
        滾動相關係數
    
    Example:
        >>> price_vol_corr = ts_corr(close, volume, 20)
    """
    return x.rolling(window=window, min_periods=3).corr(y)


def ts_cov(x: DataType, y: DataType, window: int) -> DataType:
    """
    時序滾動共變異數
    
    Args:
        x: 第一個變數
        y: 第二個變數
        window: 窗口期數
    
    Returns:
        滾動共變異數
    
    Example:
        >>> cov = ts_cov(ret1, ret2, 20)
    """
    return x.rolling(window=window, min_periods=3).cov(y)


def ts_skew(data: DataType, window: int) -> DataType:
    """
    時序滾動偏態
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        滾動偏態值
    
    Example:
        >>> ret_skew = ts_skew(daily_return, 20)
    """
    return data.rolling(window=window, min_periods=3).skew()


def ts_kurt(data: DataType, window: int) -> DataType:
    """
    時序滾動峰態
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        滾動峰態值
    
    Example:
        >>> ret_kurt = ts_kurt(daily_return, 20)
    """
    return data.rolling(window=window, min_periods=4).kurt()


# ═══════════════════════════════════════════════════════════════════════════════
# 截面運算 (Cross-Section Operators)
# ═══════════════════════════════════════════════════════════════════════════════

def rank(data: DataType, group: pd.DataFrame = None) -> DataType:
    """
    截面排名 - 同一時間點所有股票的排名百分位
    
    Args:
        data: DataFrame (rows=日期, cols=股票)
        group: 分組 DataFrame (用於產業分組排名)，如果提供則按組排名
    
    Returns:
        排名百分位 (0~1，1 表示最高)
    
    Example:
        >>> pe_rank = rank(pe)  # PE 在所有股票中的排名
        >>> pe_sector_rank = rank(pe, sector_df)  # 產業內排名
    """
    if isinstance(data, pd.Series):
        return data.rank(pct=True)
    
    if group is None:
        # 整體截面排名
        return data.rank(axis=1, pct=True)
    else:
        # 分組排名 (產業內排名)
        result = data.copy()
        for date in data.index:
            if date not in group.index:
                continue
            row = data.loc[date]
            grp = group.loc[date]
            for g in grp.unique():
                if pd.isna(g):
                    continue
                mask = grp == g
                subset = row[mask]
                if len(subset) > 1:
                    result.loc[date, mask] = subset.rank(pct=True)
        return result


def zscore(data: DataType, group: pd.DataFrame = None) -> DataType:
    """
    截面 Z-Score 標準化 - 同一時間點的標準化
    
    Args:
        data: DataFrame (rows=日期, cols=股票)
        group: 分組 DataFrame (用於產業中性化)，如果提供則按組標準化
    
    Returns:
        Z-Score 標準化後的值
    
    Example:
        >>> pe_zscore = zscore(pe)
        >>> pe_sector_zscore = zscore(pe, sector_df)  # 產業內標準化
    """
    if isinstance(data, pd.Series):
        mean = data.mean()
        std = data.std()
        return (data - mean) / std if std != 0 else data * 0
    
    if group is None:
        # 整體截面標準化
        mean = data.mean(axis=1)
        std = data.std(axis=1)
        return data.sub(mean, axis=0).div(std.replace(0, np.nan), axis=0)
    else:
        # 分組標準化 (產業中性化)
        result = data.copy()
        for date in data.index:
            if date not in group.index:
                continue
            row = data.loc[date]
            grp = group.loc[date]
            for g in grp.unique():
                if pd.isna(g):
                    continue
                mask = grp == g
                subset = row[mask]
                if len(subset) > 1:
                    mean = subset.mean()
                    std = subset.std()
                    if std != 0:
                        result.loc[date, mask] = (subset - mean) / std
        return result


def demean(data: DataType) -> DataType:
    """
    截面去均值 - 減去同一時間點的均值
    
    Args:
        data: DataFrame (rows=日期, cols=股票)
    
    Returns:
        去均值後的值
    
    Example:
        >>> ret_demean = demean(daily_return)
    """
    if isinstance(data, pd.Series):
        return data - data.mean()
    mean = data.mean(axis=1)
    return data.sub(mean, axis=0)


def neutralize(data: DataType, factor: DataType) -> DataType:
    """
    因子中性化 - 移除與指定因子的相關性
    
    使用線性回歸殘差做為中性化後的值
    
    Args:
        data: 要中性化的因子 DataFrame
        factor: 控制因子 DataFrame
    
    Returns:
        中性化後的因子
    
    Example:
        >>> momentum_size_neutral = neutralize(momentum, market_cap)
    """
    result = data.copy()
    
    for date in data.index:
        y = data.loc[date].values
        x = factor.loc[date].values
        
        # 移除 NaN
        valid = ~(np.isnan(y) | np.isnan(x))
        if valid.sum() < 3:
            continue
        
        y_valid = y[valid]
        x_valid = x[valid]
        
        # 線性回歸
        x_mean = x_valid.mean()
        y_mean = y_valid.mean()
        beta = np.sum((x_valid - x_mean) * (y_valid - y_mean)) / np.sum((x_valid - x_mean) ** 2)
        alpha = y_mean - beta * x_mean
        
        # 殘差
        residual = y.copy()
        residual[valid] = y_valid - (alpha + beta * x_valid)
        result.loc[date] = residual
    
    return result


def winsorize(data: DataType, lower: float = 0.01, upper: float = 0.99) -> DataType:
    """
    截面縮尾處理 - 將極端值限制在指定百分位
    
    Args:
        data: DataFrame (rows=日期, cols=股票)
        lower: 下界百分位 (0~1)
        upper: 上界百分位 (0~1)
    
    Returns:
        縮尾處理後的值
    
    Example:
        >>> pe_winsorized = winsorize(pe, 0.01, 0.99)
    """
    if isinstance(data, pd.Series):
        lower_val = data.quantile(lower)
        upper_val = data.quantile(upper)
        return data.clip(lower=lower_val, upper=upper_val)
    
    def _winsorize_row(row):
        lower_val = row.quantile(lower)
        upper_val = row.quantile(upper)
        return row.clip(lower=lower_val, upper=upper_val)
    
    return data.apply(_winsorize_row, axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# 衰減運算 (Decay Operators)
# ═══════════════════════════════════════════════════════════════════════════════

def decay_linear(data: DataType, window: int) -> DataType:
    """
    線性衰減加權 - 近期權重較大，線性遞減
    
    權重: [window, window-1, ..., 2, 1] 正規化
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
    
    Returns:
        線性衰減加權值
    
    Example:
        >>> weighted_ret = decay_linear(daily_return, 20)
    """
    weights = np.arange(1, window + 1, dtype=float)
    weights = weights / weights.sum()
    
    def _weighted_mean(x):
        if len(x) < window:
            w = weights[-len(x):]
            w = w / w.sum()
            return np.sum(x * w)
        return np.sum(x * weights)
    
    return data.rolling(window=window, min_periods=1).apply(_weighted_mean, raw=True)


def decay_exp(data: DataType, window: int, alpha: float = None) -> DataType:
    """
    指數衰減加權 (EMA)
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數 (用於計算 alpha = 2/(window+1))
        alpha: 衰減係數 (0~1)，如不指定則自動計算
    
    Returns:
        指數衰減加權值
    
    Example:
        >>> ema20 = decay_exp(close, 20)
    """
    if alpha is None:
        alpha = 2 / (window + 1)
    return data.ewm(alpha=alpha, min_periods=1).mean()


def decay_power(data: DataType, window: int, power: float = 2) -> DataType:
    """
    冪次衰減加權 - 權重以冪次遞減
    
    權重: [window^p, (window-1)^p, ..., 2^p, 1^p] 正規化
    
    Args:
        data: DataFrame 或 Series
        window: 窗口期數
        power: 冪次 (越大則近期權重越高)
    
    Returns:
        冪次衰減加權值
    
    Example:
        >>> weighted_vol = decay_power(volume, 10, power=2)
    """
    weights = np.arange(1, window + 1, dtype=float) ** power
    weights = weights / weights.sum()
    
    def _weighted_mean(x):
        if len(x) < window:
            w = weights[-len(x):]
            w = w / w.sum()
            return np.sum(x * w)
        return np.sum(x * weights)
    
    return data.rolling(window=window, min_periods=1).apply(_weighted_mean, raw=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 邏輯運算 (Logical Operators)
# ═══════════════════════════════════════════════════════════════════════════════

def if_else(condition: DataType, if_true: DataType, if_false: DataType) -> DataType:
    """
    條件選擇
    
    Args:
        condition: 布林條件
        if_true: 條件為真時的值
        if_false: 條件為假時的值
    
    Returns:
        根據條件選擇的值
    
    Example:
        >>> signal = if_else(close > ma20, 1, -1)
    """
    return pd.DataFrame(
        np.where(condition, if_true, if_false),
        index=condition.index,
        columns=condition.columns if isinstance(condition, pd.DataFrame) else None
    )


def sign(data: DataType) -> DataType:
    """
    取符號 - 正數返回1，負數返回-1，零返回0
    
    Args:
        data: DataFrame 或 Series
    
    Returns:
        符號值
    
    Example:
        >>> direction = sign(ts_delta(close, 1))
    """
    return np.sign(data)


def abs_val(data: DataType) -> DataType:
    """
    取絕對值
    
    Args:
        data: DataFrame 或 Series
    
    Returns:
        絕對值
    
    Example:
        >>> abs_return = abs_val(daily_return)
    """
    return np.abs(data)


def log(data: DataType) -> DataType:
    """
    取自然對數
    
    Args:
        data: DataFrame 或 Series (需為正數)
    
    Returns:
        自然對數
    
    Example:
        >>> log_volume = log(volume)
    """
    return np.log(data.replace(0, np.nan))


def power(data: DataType, exp: float) -> DataType:
    """
    冪次運算
    
    Args:
        data: DataFrame 或 Series
        exp: 指數
    
    Returns:
        冪次結果
    
    Example:
        >>> squared = power(return, 2)
    """
    return np.power(data, exp)


# ═══════════════════════════════════════════════════════════════════════════════
# 基礎運算支援 (自動對齊)
# ═══════════════════════════════════════════════════════════════════════════════

def add(a: DataType, b: DataType) -> DataType:
    """加法 (自動對齊索引)"""
    return a + b


def subtract(a: DataType, b: DataType) -> DataType:
    """減法 (自動對齊索引)"""
    return a - b


def multiply(a: DataType, b: DataType) -> DataType:
    """乘法 (自動對齊索引)"""
    return a * b


def divide(a: DataType, b: DataType) -> DataType:
    """除法 (自動對齊索引，除以零返回 NaN)"""
    return a / b.replace(0, np.nan)


def safe_divide(a: DataType, b: DataType, fill: float = 0) -> DataType:
    """安全除法 (除以零返回指定值)"""
    result = a / b
    result = result.replace([np.inf, -np.inf], np.nan)
    return result.fillna(fill)


# ═══════════════════════════════════════════════════════════════════════════════
# 常用因子計算 (組合函數)
# ═══════════════════════════════════════════════════════════════════════════════

def momentum(data: DataType, periods: int) -> DataType:
    """
    動量因子 - N 期報酬率
    
    Args:
        data: 價格 DataFrame
        periods: 期數
    
    Returns:
        動量 (百分比)
    
    Example:
        >>> mom_20 = momentum(close, 20)
    """
    return ts_pct_change(data, periods)


def volatility(data: DataType, window: int) -> DataType:
    """
    波動率因子 - N 期日報酬標準差
    
    Args:
        data: 價格 DataFrame
        window: 窗口期數
    
    Returns:
        波動率
    
    Example:
        >>> vol_20 = volatility(close, 20)
    """
    returns = ts_pct_change(data, 1)
    return ts_std(returns, window)


def rsi(data: DataType, window: int = 14) -> DataType:
    """
    RSI 相對強弱指標
    
    Args:
        data: 價格 DataFrame
        window: 窗口期數 (預設14)
    
    Returns:
        RSI (0~100)
    
    Example:
        >>> rsi_14 = rsi(close, 14)
    """
    delta = ts_delta(data, 1)
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    
    avg_gain = decay_exp(gain, window)
    avg_loss = decay_exp(loss, window)
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def bollinger_position(data: DataType, window: int = 20, num_std: float = 2) -> DataType:
    """
    布林通道位置 - 當前價格在布林通道中的位置
    
    Args:
        data: 價格 DataFrame
        window: 窗口期數 (預設20)
        num_std: 標準差倍數 (預設2)
    
    Returns:
        位置 (0~1，0.5 為中軌)
    
    Example:
        >>> bb_pos = bollinger_position(close, 20, 2)
    """
    middle = ts_mean(data, window)
    std = ts_std(data, window)
    upper = middle + num_std * std
    lower = middle - num_std * std
    
    return (data - lower) / (upper - lower).replace(0, np.nan)


def macd(data: DataType, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """
    MACD 指標
    
    Args:
        data: 價格 DataFrame
        fast: 快線期數 (預設12)
        slow: 慢線期數 (預設26)
        signal: 信號線期數 (預設9)
    
    Returns:
        (MACD線, 信號線, 柱狀圖)
    
    Example:
        >>> macd_line, signal_line, histogram = macd(close)
    """
    fast_ema = decay_exp(data, fast)
    slow_ema = decay_exp(data, slow)
    macd_line = fast_ema - slow_ema
    signal_line = decay_exp(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


# ═══════════════════════════════════════════════════════════════════════════════
# 產業資料載入
# ═══════════════════════════════════════════════════════════════════════════════

def load_sector(reference_df: pd.DataFrame, field: str = 'sector') -> pd.DataFrame:
    """
    從 Stock_Pool/Database 載入產業資料，對齊到參考 DataFrame
    
    Args:
        reference_df: 參考 DataFrame (用於對齊日期和股票代碼，通常是 close)
        field: 要載入的欄位 ('sector' 或 'industry')
    
    Returns:
        pd.DataFrame: 產業資料 (rows=日期, cols=股票代碼)
    
    Example:
        >>> close = db.get('close')
        >>> sector = load_sector(close)  # 載入產業別
        >>> industry = load_sector(close, 'industry')  # 載入次產業
        >>> 
        >>> # 產業內排名
        >>> pe_sector_rank = rank(pe, sector)
    """
    import json
    from pathlib import Path
    
    # 找到 Database 路徑
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / 'Stock_Pool' / 'Database'
    
    if not db_path.exists():
        raise FileNotFoundError(f"找不到 Database 路徑: {db_path}")
    
    # 讀取所有股票的產業資料
    sector_map = {}
    for json_file in db_path.glob('*_*.json'):
        try:
            ticker = json_file.stem.split('_')[0]  # 取得股票代碼
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if field in data:
                    sector_map[ticker] = data[field]
        except Exception:
            continue
    
    # 建立產業 DataFrame，對齊到參考 DataFrame
    result = pd.DataFrame(
        index=reference_df.index,
        columns=reference_df.columns
    )
    
    for col in reference_df.columns:
        ticker = str(col)
        if ticker in sector_map:
            result[col] = sector_map[ticker]
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 匯出所有函數
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # 時序運算
    'ts_delay', 'ts_delta', 'ts_pct_change',
    'ts_mean', 'ts_sum', 'ts_std', 'ts_max', 'ts_min',
    'ts_argmax', 'ts_argmin', 'ts_rank', 'ts_zscore',
    'ts_corr', 'ts_cov', 'ts_skew', 'ts_kurt',
    
    # 截面運算
    'rank', 'zscore', 'demean', 'neutralize', 'winsorize',
    
    # 衰減運算
    'decay_linear', 'decay_exp', 'decay_power',
    
    # 邏輯運算
    'if_else', 'sign', 'abs_val', 'log', 'power',
    
    # 基礎運算
    'add', 'subtract', 'multiply', 'divide', 'safe_divide',
    
    # 組合因子
    'momentum', 'volatility', 'rsi', 'bollinger_position', 'macd',
    
    # 產業資料
    'load_sector',
]


# ═══════════════════════════════════════════════════════════════════════════════
# 測試
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from Platform.Core.build_field_database import FieldDB
    
    print("=" * 70)
    print("📊 Factor Operators 測試")
    print("=" * 70)
    
    # 載入資料
    db = FieldDB()
    close = db.get('close')
    volume = db.get('volume')
    
    print(f"\n📈 測試資料: close {close.shape}")
    
    # 測試時序運算
    print("\n1️⃣ 時序運算測試:")
    
    delta_5 = ts_delta(close, 5)
    print(f"   ts_delta(close, 5): {delta_5.iloc[-1, :3].values}")
    
    rank_20 = ts_rank(close, 20)
    print(f"   ts_rank(close, 20): {rank_20.iloc[-1, :3].values}")
    
    zscore_20 = ts_zscore(volume, 20)
    print(f"   ts_zscore(volume, 20): {zscore_20.iloc[-1, :3].values}")
    
    # 測試截面運算
    print("\n2️⃣ 截面運算測試:")
    
    cs_rank = rank(close)
    print(f"   rank(close): {cs_rank.iloc[-1, :3].values}")
    
    cs_zscore = zscore(close)
    print(f"   zscore(close): {cs_zscore.iloc[-1, :3].values}")
    
    # 測試衰減運算
    print("\n3️⃣ 衰減運算測試:")
    
    lin_decay = decay_linear(close, 10)
    print(f"   decay_linear(close, 10): {lin_decay.iloc[-1, :3].values}")
    
    exp_decay = decay_exp(close, 10)
    print(f"   decay_exp(close, 10): {exp_decay.iloc[-1, :3].values}")
    
    # 測試組合因子
    print("\n4️⃣ 組合因子測試:")
    
    mom_20 = momentum(close, 20)
    print(f"   momentum(close, 20): {mom_20.iloc[-1, :3].values}")
    
    vol_20 = volatility(close, 20)
    print(f"   volatility(close, 20): {vol_20.iloc[-1, :3].values}")
    
    rsi_14 = rsi(close, 14)
    print(f"   rsi(close, 14): {rsi_14.iloc[-1, :3].values}")
    
    # 測試運算組合
    print("\n5️⃣ 運算組合測試:")
    
    # 價量背離因子: 價格創新高但成交量萎縮
    price_rank = ts_rank(close, 20)
    volume_rank = ts_rank(volume, 20)
    divergence = price_rank - volume_rank
    print(f"   價量背離 = ts_rank(close,20) - ts_rank(volume,20)")
    print(f"   結果: {divergence.iloc[-1, :3].values}")
    
    # 標準化動量
    mom = momentum(close, 20)
    mom_zscore = zscore(mom)
    print(f"   zscore(momentum(close, 20)):")
    print(f"   結果: {mom_zscore.iloc[-1, :3].values}")
    
    print("\n" + "=" * 70)
    print("✅ 所有測試通過！")
    print("=" * 70)
