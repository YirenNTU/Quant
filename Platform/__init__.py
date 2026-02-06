"""
================================================================================
📊 Investment AI Platform - 量化交易平台
================================================================================

一個讓朋友們可以輕鬆使用的量化交易平台。

🚀 快速開始:

1. 載入資料庫:
>>> from Platform import FieldDB
>>> db = FieldDB()
>>> close = db.get('close')

2. 使用運算工具:
>>> from Platform.Factors import *
>>> momentum = ts_pct_change(close, 20)
>>> momentum_zscore = zscore(momentum)

3. 建立策略:
>>> from Platform import Strategy
>>> 
>>> class MyStrategy(Strategy):
>>>     name = "我的策略"
>>>     
>>>     def compute(self, db):
>>>         close = db.get('close')
>>>         return zscore(ts_pct_change(close, 20))

4. 執行回測:
>>> from Platform import Backtester
>>> result = Backtester.run(MyStrategy())
>>> print(result.summary())

5. 取得配置:
>>> from Platform import get_allocation
>>> allocation = get_allocation(MyStrategy(), capital=1_000_000)
>>> print(allocation)

================================================================================
"""

# 版本資訊
__version__ = "1.0.0"
__author__ = "Investment AI"

# 核心模組
from .Core.build_field_database import FieldDB

# 策略模組
from .Strategies.base import Strategy
from .Strategies.manager import StrategyManager

# 回測模組
from .Backtest.engine import Backtester, BacktestResult

# 配置模組
from .Allocator.allocator import Allocator, AllocationResult, get_allocation

# 因子運算 (重新匯出)
from .Factors import operators

# 匯出列表
__all__ = [
    # 資料庫
    'FieldDB',
    
    # 策略
    'Strategy',
    'StrategyManager',
    
    # 回測
    'Backtester',
    'BacktestResult',
    
    # 配置
    'Allocator',
    'AllocationResult',
    'get_allocation',
    
    # 運算工具
    'operators',
]


# ═══════════════════════════════════════════════════════════════════════════════
# 便利函數
# ═══════════════════════════════════════════════════════════════════════════════

def run_strategy(strategy, start_date=None, end_date=None, db=None):
    """
    執行策略並取得權重
    
    Args:
        strategy: 策略實例
        start_date: 開始日期
        end_date: 結束日期
        db: FieldDB 實例
    
    Returns:
        pd.DataFrame: 權重矩陣
    """
    if db is None:
        db = FieldDB()
    return strategy.run(db, start_date, end_date)


def backtest(strategy, **kwargs):
    """
    執行回測
    
    Args:
        strategy: 策略實例
        **kwargs: 回測參數
    
    Returns:
        BacktestResult
    """
    return Backtester.run(strategy, **kwargs)


def quick_test(strategy_class, capital=1_000_000, show_allocation=True):
    """
    快速測試策略
    
    Args:
        strategy_class: 策略類別
        capital: 測試資金
        show_allocation: 是否顯示配置
    
    Example:
        >>> quick_test(MyStrategy)
    """
    print("=" * 70)
    print(f"🚀 快速測試: {strategy_class.name}")
    print("=" * 70)
    
    # 實例化
    strategy = strategy_class()
    
    # 回測
    print("\n📊 回測中...")
    result = Backtester.run(strategy, start_date="2024-06-01")
    print(result.summary())
    
    # 配置
    if show_allocation:
        print("📈 當前配置建議:")
        allocation = get_allocation(strategy, capital=capital)
        print(allocation)
    
    return result


# 打印歡迎訊息 (只在直接執行時)
if __name__ == '__main__':
    print(__doc__)
