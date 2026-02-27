"""
任務解決者 Agent (Solver Agents)
這些 Agent 專門接收市場上的任務，評估自身能力後進行投標
"""
import random
from typing import Dict, List, Optional
from loguru import logger
from dataclasses import dataclass
from .hub_market import Task, Bid, market, TaskStatus

@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_id: str
    model_name: str
    cost_per_token: float  # 每 Token 成本 (SOL)
    success_rate: float  # 成功率 (0-1)
    specialization: List[str]  # 擅長領域

class SolverAgent:
    """
    任務解決者 Agent
    策略：監控市場 -> 評估任務 -> 計算成本 -> 自動投標
    """
    def __init__(self, config: AgentConfig):
        self.config = config
        self.wallet_balance = 10.0  # 初始資金
        self.completed_tasks = 0
        logger.info(f"🤖 [Solver] Agent 啟動：{config.agent_id} "
                    f"(模型：{config.model_name}, 成本：{config.cost_per_token:.4f} SOL/token)")

    def evaluate_task(self, task: Task) -> bool:
        """
        評估是否接手此任務
        條件：
        1. 任務在擅長領域內
        2. 預期利潤為正
        """
        # 簡單起見，假設所有任務都能做
        can_do = True
        
        # 計算預期成本
        expected_cost = task.expected_tokens * self.config.cost_per_token
        
        # 如果預期成本超過買方預算，則不做
        if expected_cost > task.max_budget:
            can_do = False
        
        return can_do

    def calculate_bid(self, task: Task) -> Optional[float]:
        """
        計算投標價格
        策略：成本 + 預期利潤
        """
        expected_cost = task.expected_tokens * self.config.cost_per_token
        
        # 加價策略：根據成功率和市場競爭調整
        profit_margin = 0.3  # 30% 利潤
        bid_price = expected_cost * (1 + profit_margin)
        
        # 確保不超過買方預算
        if bid_price > task.max_budget:
            return None  # 無法在預算內完成
        
        return round(bid_price, 4)

    def scan_and_bid(self, market_instance) -> List[Bid]:
        """
        掃描市場並對合適的任務投標
        """
        submitted_bids = []
        
        for task_id, task in market_instance.tasks.items():
            if task.status != TaskStatus.OPEN:  # 只投標進行中的任務
                continue
            
            if self.evaluate_task(task):
                bid_price = self.calculate_bid(task)
                
                if bid_price:
                    bid = market_instance.submit_bid(
                        task_id=task_id,
                        bidder_id=self.config.agent_id,
                        bid_price=bid_price,
                        estimated_tokens=task.expected_tokens,
                        model_name=self.config.model_name,
                        message=f"我可以使用 {self.config.model_name} 高效完成此任務"
                    )
                    submitted_bids.append(bid)
                    logger.info(f"🎯 {self.config.agent_id} 投標任務 {task_id} "
                                f"@ {bid_price} SOL (成本：{task.expected_tokens * self.config.cost_per_token:.4f})")
        
        return submitted_bids

def create_diverse_solvers():
    """建立多樣的 Solver Agents 模擬真實市場"""
    configs = [
        # 低成本、低質量 Agent (使用小型模型)
        # 假設 1000 tokens 成本 0.0001 SOL
        AgentConfig("solver_qwen_tiny", "Qwen-1.5B", 0.0000001, 0.7, ["general"]),
        
        # 中等成本、中等質量
        AgentConfig("solver_llama_mid", "Llama-3-8B", 0.0000005, 0.85, ["general", "code"]),
        
        # 高成本、高質量 (使用大型模型)
        AgentConfig("solver_qwen_large", "Qwen-32B", 0.000001, 0.95, ["complex", "analysis"]),
        
        # 專家級 (使用頂級模型，但成本高)
        AgentConfig("solver_expert", "Mixtral-8x22B", 0.000002, 0.98, ["expert", "research"]),
    ]
    
    return [SolverAgent(cfg) for cfg in configs]
