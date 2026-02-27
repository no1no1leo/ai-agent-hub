"""
純演算法競標策略 (No-LLM Strategies)
基於數學、賽局理論與統計學的自動決策
"""
import random
import math
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class MarketState:
    """市場狀態快照"""
    avg_price: float
    min_price: float
    max_price: float
    total_bids: int
    task_complexity: float  # 0-1

class BiddingStrategy:
    """競標策略基類"""
    name = "Base Strategy"
    
    def calculate_bid(self, cost: float, state: MarketState, max_budget: float) -> float:
        raise NotImplementedError

class AggressiveStrategy(BiddingStrategy):
    """
    激進策略：低價搶單
    邏輯：成本 * 1.05 (僅加價 5%)，優先確保得標
    適用：急需累積信譽的新手 Agent
    """
    name = "Aggressive (Low-ball)"
    
    def calculate_bid(self, cost: float, state: MarketState, max_budget: float) -> float:
        bid = cost * 1.05
        # 確保不超過預算
        return min(bid, max_budget * 0.99)

class ConservativeStrategy(BiddingStrategy):
    """
    保守策略：高利潤導向
    邏輯：成本 * 1.50 (加價 50%)
    適用：對自身品質有信心的 Agent
    """
    name = "Conservative (High-margin)"
    
    def calculate_bid(self, cost: float, state: MarketState, max_budget: float) -> float:
        bid = cost * 1.50
        return min(bid, max_budget * 0.99)

class MarketFollowStrategy(BiddingStrategy):
    """
    跟隨策略：參考市價
    邏輯：市價 * 0.98 (比均價低一點點)
    適用：穩健型 Agent
    """
    name = "Market Follow"
    
    def calculate_bid(self, cost: float, state: MarketState, max_budget: float) -> float:
        # 如果市價低於成本，則放棄或僅微幅加價
        if state.avg_price < cost:
            return cost * 1.10
        return state.avg_price * 0.98

class SniperStrategy(BiddingStrategy):
    """
    狙擊策略：精準計算
    邏輯：觀察市場投標數，若投標少則高價，投標多則低價
    """
    name = "Sniper (Dynamic)"
    
    def calculate_bid(self, cost: float, state: MarketState, max_budget: float) -> float:
        if state.total_bids < 3:
            # 競爭少，高價
            return cost * 1.40
        elif state.total_bids < 10:
            # 中等競爭
            return cost * 1.15
        else:
            # 激烈競爭，壓低利潤
            return cost * 1.02

class RandomWalkStrategy(BiddingStrategy):
    """
    隨機漫步策略：模擬無 intelligence 代理
    邏輯：在成本價附近隨機波動
    """
    name = "Random Walk"
    
    def calculate_bid(self, cost: float, state: MarketState, max_budget: float) -> float:
        variance = random.uniform(0.9, 1.1)
        return cost * variance

# 策略工廠
STRATEGIES = {
    "aggressive": AggressiveStrategy(),
    "conservative": ConservativeStrategy(),
    "market_follow": MarketFollowStrategy(),
    "sniper": SniperStrategy(),
    "random": RandomWalkStrategy()
}

def get_strategy(name: str) -> BiddingStrategy:
    return STRATEGIES.get(name, AggressiveStrategy())
