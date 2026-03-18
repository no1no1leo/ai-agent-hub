"""
AI Agent 任務競標市場 (Hub Market)
核心邏輯：純算法规則，無外部依賴
功能：發布任務、接收投標、自動媒合、結算
"""
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from loguru import logger
from enum import Enum

class TaskStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
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
    routing_mode: str = "internal"
    required_domain: Optional[str] = None
    status: TaskStatus = TaskStatus.OPEN
    assigned_to: Optional[str] = None
    selection_reason: Optional[str] = None
    result: Optional[str] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verification_status: Optional[str] = None
    verification_notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = field(default=None)

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
    domains: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    trust_level: str = "standard"

class HubMarket:
    """任務競標市場"""
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.bids: Dict[str, List[Bid]] = {}
        logger.info("🏪 Hub Market 初始化完成 (純算法规則)")

    def create_task(self, description: str, input_data: str, max_budget: float,
                    expected_tokens: int, requester_id: str = "buyer_001",
                    expires_in_hours: int = 24, routing_mode: str = "internal",
                    required_domain: Optional[str] = None) -> Task:
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")
        if max_budget <= 0:
            raise ValueError("Budget must be positive")
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            requester_id=requester_id,
            description=description,
            input_data=input_data,
            max_budget=max_budget,
            expected_tokens=expected_tokens,
            routing_mode=routing_mode,
            required_domain=required_domain,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        )
        self.tasks[task.task_id] = task
        self.bids[task.task_id] = []
        logger.info(f"📢 [Broker] 新任務：{task.task_id} | 預算上限：{max_budget} units | 過期：{expires_in_hours}h")
        return task

    def submit_bid(self, task_id: str, bidder_id: str, bid_price: float,
                   estimated_tokens: int, model_name: str, message: str = "",
                   domains: Optional[List[str]] = None, tools: Optional[List[str]] = None,
                   trust_level: str = "standard") -> Bid:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        bid = Bid(
            bid_id=str(uuid.uuid4())[:8],
            task_id=task_id,
            bidder_id=bidder_id,
            bid_price=bid_price,
            estimated_tokens=estimated_tokens,
            model_name=model_name,
            message=message,
            domains=domains or [],
            tools=tools or [],
            trust_level=trust_level,
        )
        self.bids[task_id].append(bid)
        logger.info(f"🧮 [Broker] 新提案：{bid.bid_id} by {bidder_id} @ {bid_price} cost units")
        return bid

    def _score_bid(self, task: Task, bid: Bid) -> tuple[float, str]:
        trust_bonus = {"simulated": 0.0, "standard": 0.1, "external": 0.05, "verified": 0.2}.get(bid.trust_level, 0.0)
        domain_bonus = 0.0
        reason_bits = []
        if task.required_domain and task.required_domain in (bid.domains or []):
            domain_bonus = 0.25
            reason_bits.append(f"matched required domain '{task.required_domain}'")
        if bid.trust_level:
            reason_bits.append(f"trust={bid.trust_level}")
        score = bid.bid_price - domain_bonus - trust_bonus
        if not reason_bits:
            reason_bits.append("cost-first selection")
        return score, ", ".join(reason_bits)

    def select_winner(self, task_id: str) -> Optional[Bid]:
        if task_id not in self.bids or not self.bids[task_id]:
            return None
        task = self.tasks[task_id]
        valid_bids = [b for b in self.bids[task_id] if b.bid_price <= task.max_budget]
        if not valid_bids:
            logger.warning(f"⚠️ 無有效提案 (預算上限：{task.max_budget})")
            return None
        scored_bids = [(b, *self._score_bid(task, b)) for b in valid_bids]
        winner, winner_score, winner_reason = min(scored_bids, key=lambda item: item[1])
        task.assigned_to = winner.bidder_id
        task.status = TaskStatus.IN_PROGRESS
        task.selection_reason = (
            f"Selected {winner.bidder_id} with estimated cost {winner.bid_price}; "
            f"decision factors: {winner_reason}; final score={winner_score:.3f}"
        )
        logger.info(f"🏆 [Broker] 任務 {task_id} 指派給 {winner.bidder_id} @ estimated cost {winner.bid_price}")
        return winner

    def submit_result(self, task_id: str, result: str):
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        task.result = result
        task.status = TaskStatus.SUBMITTED
        task.submitted_at = datetime.now(timezone.utc)
        logger.info(f"📨 [Market] 任務 {task_id} 已提交結果")

    def verify_result(self, task_id: str, approved: bool, notes: str = ""):
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        task.verified_at = datetime.now(timezone.utc)
        task.verification_notes = notes
        if approved:
            task.verification_status = "approved"
            task.status = TaskStatus.COMPLETED
            logger.info(f"✅ [Market] 任務 {task_id} 驗證通過")
        else:
            task.verification_status = "rejected"
            task.status = TaskStatus.FAILED
            logger.info(f"❌ [Market] 任務 {task_id} 驗證失敗")

        if task.assigned_to:
            from .reputation import reputation_system

            reputation_system.update_from_verification(
                agent_id=task.assigned_to,
                approved=approved,
                rating=5.0 if approved else 2.0,
                latency_score=1.0,
                budget_score=1.0,
            )

    def complete_task(self, task_id: str, result: str):
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        task.result = result
        task.status = TaskStatus.COMPLETED
        logger.info(f"✅ [Market] 任務 {task_id} 已完成")

    def expire_old_tasks(self):
        """自動過期超時任務"""
        now = datetime.now(timezone.utc)
        expired_count = 0
        for task in self.tasks.values():
            if task.status == TaskStatus.OPEN and task.expires_at and now > task.expires_at:
                task.status = TaskStatus.FAILED
                expired_count += 1
        if expired_count > 0:
            logger.info(f"🧹 [Market] 已過期 {expired_count} 個任務")
        return expired_count

    def get_task(self, task_id: str) -> Optional[Task]:
        """Return a single task by ID, or None if not found."""
        return self.tasks.get(task_id)

    def get_bids_for_task(self, task_id: str) -> List[Bid]:
        """Return all bids submitted for a given task."""
        return self.bids.get(task_id, [])

    def get_market_stats(self) -> Dict:
        total_tasks = len(self.tasks)
        total_bids = sum(len(b) for b in self.bids.values())
        winning_bids = [b.bid_price for t in self.tasks.values() if t.assigned_to for b in self.bids.get(t.task_id, []) if b.bidder_id == t.assigned_to]
        avg_winning_bid = sum(winning_bids) / len(winning_bids) if winning_bids else 0

        return {
            "total_tasks": total_tasks,
            "total_bids": total_bids,
            "avg_winning_bid": avg_winning_bid,
            "active_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.OPEN]),
            "expired_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
        }

market = HubMarket()
