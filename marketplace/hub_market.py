"""
AI Agent 任務競標市場 (Hub Market)
核心邏輯：讓 Agent 互相競爭，找出完成任務的最低成本方案
純文字/通用描述版本，不依賴特定多模態引擎
"""
import uuid
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from enum import Enum

class TaskStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    """任務定義 (純文字/通用描述)"""
    task_id: str
    requester_id: str
    description: str  # 任務描述 (可包含圖片連結或詳細說明)
    input_data: str  # 輸入數據 (可以是 URL, 文件路徑或純文字)
    max_budget: float  # 買方願意支付的最高金額 (SOL)
    expected_tokens: int  # 預估代價 (通用單位)
    status: TaskStatus = TaskStatus.OPEN
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Bid:
    """投標定義"""
    bid_id: str
    task_id: str
    bidder_id: str
    bid_price: float  # 投標價格
    estimated_tokens: int  # 預估使用量
    model_name: str  # 使用的模型/策略名稱
    message: str = ""

class HubMarket:
    """
    任務競標市場
    功能：發布任務、接收投標、自動媒合、結算
    """
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.bids: Dict[str, List[Bid]] = {}  # task_id -> bids
        self.task_results: Dict[str, str] = {}
        logger.info("🏪 Hub Market 初始化完成 (純文字/通用版)")

    def create_task(self, description: str, input_data: str, max_budget: float, 
                    expected_tokens: int, requester_id: str = "buyer_001") -> Task:
        """買方 Agent 發布任務"""
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            requester_id=requester_id,
            description=description,
            input_data=input_data,
            max_budget=max_budget,
            expected_tokens=expected_tokens
        )
        self.tasks[task.task_id] = task
        self.bids[task.task_id] = []
        logger.info(f"📢 [Market] 新任務發布：{task.task_id} | 預算：{max_budget} SOL")
        return task

    def submit_bid(self, task_id: str, bidder_id: str, bid_price: float, 
                   estimated_tokens: int, model_name: str, message: str = "") -> Bid:
        """賣方 Agent 投標"""
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        
        bid = Bid(
            bid_id=str(uuid.uuid4())[:8],
            task_id=task_id,
            bidder_id=bidder_id,
            bid_price=bid_price,
            estimated_tokens=estimated_tokens,
            model_name=model_name,
            message=message
        )
        self.bids[task_id].append(bid)
        logger.info(f"💰 [Market] 新投標：{bid.bid_id} by {bidder_id} @ {bid_price} SOL ({model_name})")
        return bid

    def select_winner(self, task_id: str) -> Optional[Bid]:
        """
        自動選擇最佳投標
        策略：優先考慮價格最低，若價格相同則考慮信譽 (此處簡化為隨機)
        """
        if task_id not in self.bids or not self.bids[task_id]:
            return None
        
        task = self.tasks[task_id]
        valid_bids = [b for b in self.bids[task_id] if b.bid_price <= task.max_budget]
        
        if not valid_bids:
            logger.warning(f"⚠️  無有效投標 (所有投標皆超過預算 {task.max_budget})")
            return None
        
        # 選擇最低價者
        winner = min(valid_bids, key=lambda x: x.bid_price)
        task.assigned_to = winner.bidder_id
        task.status = TaskStatus.IN_PROGRESS
        
        logger.info(f"🏆 [Market] 任務 {task_id} 由 {winner.bidder_id} 得標 @ {winner.bid_price} SOL")
        return winner

    def complete_task(self, task_id: str, result: str):
        """完成任务并提交结果"""
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        
        task = self.tasks[task_id]
        task.result = result
        task.status = TaskStatus.COMPLETED
        logger.info(f"✅ [Market] 任務 {task_id} 已完成")

    def get_market_stats(self) -> Dict:
        """獲取市場統計數據"""
        total_tasks = len(self.tasks)
        total_bids = sum(len(b) for b in self.bids.values())
        avg_winning_bid = 0
        
        winning_bids = []
        for task in self.tasks.values():
            if task.assigned_to:
                for bid in self.bids.get(task.task_id, []):
                    if bid.bidder_id == task.assigned_to:
                        winning_bids.append(bid.bid_price)
        
        if winning_bids:
            avg_winning_bid = sum(winning_bids) / len(winning_bids)
        
        return {
            "total_tasks": total_tasks,
            "total_bids": total_bids,
            "avg_winning_bid": avg_winning_bid,
            "active_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.OPEN])
        }

# 全域市場實例
market = HubMarket()
