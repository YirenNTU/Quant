"""
Factor Engine - 因子運算引擎

使用方式:
>>> from Platform.Factors import *
>>> from Platform.Core.build_field_database import FieldDB
>>> 
>>> db = FieldDB()
>>> close = db.get('close')
>>> volume = db.get('volume')
>>> 
>>> # 計算動量因子
>>> mom_20 = momentum(close, 20)
>>> 
>>> # 計算 Z-score 標準化
>>> mom_zscore = zscore(mom_20)
>>> 
>>> # 計算時序排名
>>> price_rank = ts_rank(close, 20)
"""

from .operators import *
