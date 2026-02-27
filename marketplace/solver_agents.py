"""
純演算法 Solver Agents (No-LLM)
基於策略模式自動競標
"""
import random
from typing import Dict, List, Optional
from loguru import logger
from dataclasses import dataclass
from .hub_market import Task, Bid, market, TaskStatus
from .strategies import BiddingStrategy, get_strategy, MarketState

@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_id: str
    model_name: str
    cost_per_token: float
    success_rate: float
    specialization: List[str]
    strategy_name: str = "aggressive"

class SolverAgent:
    """
    純演算法任務解決者
    特點：無 LLM 依賴，微秒級決策
    """
    def __init__(self, config: AgentConfig):
        self.config = config
        self.wallet_balance = 10.0
        self.completed_tasks = 0
        self.strategy = get_strategy(config.strategy_name)
        logger.info(f"🤖 [Algo] Agent 啟動：{config.agent_id} "
                    f"(策略：{self.strategy.name}, 成本：{config.cost_per_token*1e6:.2f} SOL/M tokens)")

    def evaluate_task(self, task: Task) -> bool:
        """評估是否投標：僅考慮成本效益"""
        expected_cost = task.expected_tokens * self.config.cost_per_token
        # 如果預期成本高於預算，放棄
        return expected_cost < task.max_budget * 0.9

    def calculate_bid(self, task: Task, market_state: MarketState) -> Optional[float]:
        """使用策略計算投標價格"""
        base_cost = task.expected_tokens * self.config.cost_per_token
        return self.strategy.calculate_bid(base_cost, market_state, task.max_budget)

    def scan_and_bid(self, market_instance) -> List[Bid]:
        """掃描市場並投標"""
        submitted_bids = []
        
        for task_id, task in market_instance.tasks.items():
            if task.status != TaskStatus.OPEN:
                continue
            
            if self.evaluate_task(task):
                # 建立市場狀態快照
                all_bids = market_instance.bids.get(task_id, [])
                prices = [b.bid_price for b in all_bids]
                
                market_state = MarketState(
                    avg_price=sum(prices)/len(prices) if prices else 0,
                    min_price=min(prices) if prices else 0,
                    max_price=max(prices) if prices else 0,
                    total_bids=len(all_bids),
                    task_complexity=0.5
                )
                
                bid_price = self.calculate_bid(task, market_state)
                
                if bid_price and bid_price <= task.max_budget:
                    bid = market_instance.submit_bid(
                        task_id=task_id,
                        bidder_id=self.config.agent_id,
                        bid_price=round(bid_price, 6),
                        estimated_tokens=task.expected_tokens,
                        model_name=self.config.model_name,
                        message=f"[Algo] {self.strategy.name} 策略投標"
                    )
                    submitted_bids.append(bid)
        
        return submitted_bids

def create_diverse_solvers():
    """建立多樣化的演算法 Agent 集群"""
    configs = [
        # 低成本、激進策略
        AgentConfig("algo_sniper_01", "Qwen-1.5B-Int4", 0.0000001, 0.85, ["general"], "sniper"),
        
        # 中成本、跟隨策略
        AgentConfig("algo_follower_01", "Llama-3-8B", 0.0000005, 0.90, ["code", "math"], "market_follow"),
        
        # 高成本、保守策略
        AgentConfig("algo_conservative_01", "Qwen-32B", 0.000001, 0.95, ["analysis"], "conservative"),
        
        # 隨機策略 (模擬散戶)
        AgentConfig("algo_random_01", "TinyLlama-1.1B", 0.00000005, 0.70, ["general"], "random"),
    ]
    
    return [SolverAgent(cfg) for cfg in configs]
