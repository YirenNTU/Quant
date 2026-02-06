"""
價值策略 - Value Strategy

買入低估值 (低 PE, 低 PB, 高殖利率) 的股票
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Platform.Strategies import Strategy
from Platform.Factors import *


class ValueStrategy(Strategy):
    """價值策略"""
    
    name = "價值策略"
    description = "買入低PE、低PB、高殖利率的股票"
    version = "1.0"
    author = "Platform"
    
    params = {
        "pe_weight": 0.4,      # PE 權重
        "pb_weight": 0.3,      # PB 權重
        "yield_weight": 0.3,   # 殖利率權重
        "top_n": 10,
    }
    
    def compute(self, db):
        pe = db.get('pe')
        pb = db.get('pb')
        div_yield = db.get('div_yield')
        
        # 填充缺值
        pe = pe.ffill()
        pb = pb.ffill()
        div_yield = div_yield.ffill()
        
        # 計算各因子 (PE, PB 越低越好，殖利率越高越好)
        pe_score = zscore(-pe)
        pb_score = zscore(-pb)
        yield_score = zscore(div_yield)
        
        # 組合分數
        score = (self.params["pe_weight"] * pe_score +
                 self.params["pb_weight"] * pb_score +
                 self.params["yield_weight"] * yield_score)
        
        return score


if __name__ == '__main__':
    from Platform import quick_test
    quick_test(ValueStrategy)
