"""
交易大廳 - 訂單簿 (Order Book)
負責管理訂單的發布、發現、與狀態追蹤
"""
import uuid
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class ServiceType(str, Enum):
    DATA_ANALYSIS = "data_analysis"
    IMAGE_GEN = "image_gen"
    PREDICTION = "prediction"
    COMPUTE = "compute"
    CODE_GEN = "code_generation"

class OrderStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

class OrderRequest(BaseModel):
    """AI 發出的服務請求"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    buyer_agent_id: str
    service_type: ServiceType
    description: str
    payload: Dict
    max_price: float  # 單位：SOL
    deadline: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: OrderStatus = OrderStatus.OPEN

class Bid(BaseModel):
    """賣方 Agent 的投標"""
    bid_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    seller_agent_id: str
    price: float
    estimated_time: int = 60  # 分鐘，預設 1 小時
    message: str = ""  # 給買方的備註

class OrderBook:
    """內存訂單簿 (後續將同步至鏈上)"""
    def __init__(self):
        self.orders: Dict[str, OrderRequest] = {}
        self.bids: Dict[str, List[Bid]] = {}  # order_id -> bids

    def create_order(self, order: OrderRequest):
        self.orders[order.request_id] = order
        self.bids[order.request_id] = []
        print(f"📢 [OrderBook] 新訂單：{order.request_id} by {order.buyer_agent_id}")

    def place_bid(self, bid: Bid):
        if bid.order_id not in self.orders:
            raise ValueError("Order not found")
        self.bids[bid.order_id].append(bid)
        print(f"💰 [OrderBook] 新投標：{bid.bid_id} for {bid.order_id} by {bid.seller_agent_id} @ {bid.price} SOL")

    def get_orders(self, status: Optional[OrderStatus] = None) -> List[OrderRequest]:
        if status is None:
            return list(self.orders.values())
        return [o for o in self.orders.values() if o.status == status]

    def get_bids(self, order_id: str) -> List[Bid]:
        return self.bids.get(order_id, [])

# 全域實例
order_book = OrderBook()
