"""
AI Agent 任務競標市場 (Hub Market)
核心邏輯：純算法规則，無外部依賴
功能：發布任務、接收投標、自動媒合、結算
"""
import uuid
from typing import Dict, List, Optional
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
    """任務定義 (純文字/通用)"""
    task_id: str
    requester_id: str
    description: str  # 任務描述 (可由 Agent 將圖片轉譯後填入)
    input_data: str  # 輸入數據 (URL, 路徑或文字)
    max_budget: float
    expected_tokens: int
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
    bid_price: float
    estimated_tokens: int
    model_name: str  # 策略或模型名稱 (由 Agent 自行聲明)
    message: str = ""

class HubMarket:
    """任務競標市場"""
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.bids: Dict[str, List[Bid]] = {}
        logger.info("🏪 Hub Market 初始化完成 (純算法规則)")

    def create_task(self, description: str, input_data: str, max_budget: float, 
                    expected_tokens: int, requester_id: str = "buyer_001") -> Task:
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
        logger.info(f"📢 [Market] 新任務：{task.task_id} | 預算：{max_budget} SOL")
        return task

    def submit_bid(self, task_id: str, bidder_id: str, bid_price: float, 
                   estimated_tokens: int, model_name: str, message: str = "") -> Bid:
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
        logger.info(f"💰 [Market] 新投標：{bid.bid_id} by {bidder_id} @ {bid_price} SOL")
        return bid

    def select_winner(self, task_id: str) -> Optional[Bid]:
        if task_id not in self.bids or not self.bids[task_id]:
            return None
        task = self.tasks[task_id]
        valid_bids = [b for b in self.bids[task_id] if b.bid_price <= task.max_budget]
        if not valid_bids:
            logger.warning(f"⚠️ 無有效投標 (預算：{task.max_budget})")
            return None
        winner = min(valid_bids, key=lambda x: x.bid_price)
        task.assigned_to = winner.bidder_id
        task.status = TaskStatus.IN_PROGRESS
        logger.info(f"🏆 [Market] 任務 {task_id} 由 {winner.bidder_id} 得標 @ {winner.bid_price} SOL")
        return winner

    def complete_task(self, task_id: str, result: str):
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        task.result = result
        task.status = TaskStatus.COMPLETED
        logger.info(f"✅ [Market] 任務 {task_id} 已完成")

    def get_market_stats(self) -> Dict:
        total_tasks = len(self.tasks)
        total_bids = sum(len(b) for b in self.bids.values())
        winning_bids = [b.bid_price for t in self.tasks.values() if t.assigned_to for b in self.bids.get(t.task_id, []) if b.bidder_id == t.assigned_to]
        avg_winning_bid = sum(winning_bids) / len(winning_bids) if winning_bids else 0
        return {
            "total_tasks": total_tasks,
            "total_bids": total_bids,
            "avg_winning_bid": avg_winning_bid,
            "active_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.OPEN])
        }

market = HubMarket()
