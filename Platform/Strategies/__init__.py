"""
Strategies - 策略模組

使用方式:
>>> from Platform.Strategies import Strategy, StrategyManager
>>> 
>>> class MyStrategy(Strategy):
>>>     name = "我的策略"
>>>     def compute(self, db):
>>>         ...
"""

from .base import Strategy
from .manager import StrategyManager

__all__ = ['Strategy', 'StrategyManager']
