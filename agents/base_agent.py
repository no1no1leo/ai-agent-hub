"""
AI Agent 基類
定義 Agent 的基本行為：感知、決策、行動
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

class BaseAgent(ABC):
    def __init__(self, agent_id: str, role: str):
        self.agent_id = agent_id
        self.role = role
        self.wallet_balance = 10.0  # 模擬餘額 (SOL)
        logger.info(f"🤖 Agent 啟動：{agent_id} ({role})")

    @abstractmethod
    def perceive(self, data: Any) -> Dict:
        """感知環境數據"""
        pass

    @abstractmethod
    def decide(self, perception: Dict) -> Dict:
        """根據感知做決策"""
        pass

    @abstractmethod
    def act(self, decision: Dict) -> Any:
        """執行決策"""
        pass

    def run_cycle(self, data: Any) -> Any:
        """運行一個感知 - 決策 - 行動 週期"""
        p = self.perceive(data)
        d = self.decide(p)
        return self.act(d)

class BuyerAgent(BaseAgent):
    """買方 Agent: 尋找服務、發布需求、評估投標"""
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "buyer")
        self.needs = []

    def perceive(self, data: Dict) -> Dict:
        # 接收市場上的投標或服務列表
        return {
            "available_bids": data.get("bids", []),
            "market_status": data.get("status", "unknown")
        }

    def decide(self, perception: Dict) -> Dict:
        # 簡單邏輯：選擇價格最低的投標 (後續改為 LLM 決策)
        bids = perception["available_bids"]
        if not bids:
            return {"action": "wait", "reason": "no bids"}
        
        best_bid = min(bids, key=lambda x: x["price"])
        if best_bid["price"] <= self.wallet_balance:
            return {"action": "accept", "bid": best_bid}
        else:
            return {"action": "reject", "reason": "too expensive"}

    def act(self, decision: Dict) -> str:
        action = decision["action"]
        if action == "accept":
            return f"✅ 接受投標 {decision['bid']['bid_id']}"
        elif action == "reject":
            return f"❌ 拒絕投標：{decision['reason']}"
        return "⏳ 等待中..."

class SellerAgent(BaseAgent):
    """賣方 Agent: 監聽訂單、投標、提供服務"""
    def __init__(self, agent_id: str, service_type: str):
        super().__init__(agent_id, "seller")
        self.service_type = service_type
        self.cost_basis = 0.1  # 成本底線 (SOL)

    def perceive(self, data: Dict) -> Dict:
        # 接收市場上的訂單列表
        return {
            "open_orders": data.get("orders", []),
            "market_price": data.get("avg_price", 0.5)
        }

    def decide(self, perception: Dict) -> Dict:
        # 簡單邏輯：如果有訂單且價格高於成本，則投標
        orders = perception["open_orders"]
        if not orders:
            return {"action": "wait"}
        
        target_order = orders[0]  # 簡單起見選第一個
        market_price = perception["market_price"]
        bid_price = max(self.cost_basis + 0.05, market_price * 0.95)  # 略低於市價
        
        return {
            "action": "bid",
            "order_id": target_order["request_id"],
            "price": bid_price,
            "message": f"我可以提供 {self.service_type} 服務，價格優惠"
        }

    def act(self, decision: Dict) -> str:
        if decision["action"] == "bid":
            return f"💰 投標訂單 {decision['order_id']} @ {decision['price']} SOL"
        return "⏳ 等待訂單中..."
