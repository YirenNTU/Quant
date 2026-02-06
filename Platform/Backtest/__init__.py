"""
Backtest Engine - 回測引擎

使用方式:
>>> from Platform.Backtest import Backtester
>>> from Platform.Strategies.base import Strategy
>>> 
>>> result = Backtester.run(strategy=my_strategy)
>>> print(result.summary())
"""

from .engine import Backtester, BacktestResult

__all__ = ['Backtester', 'BacktestResult']
