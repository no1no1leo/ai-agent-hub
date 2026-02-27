"""
AI Agent 基類
定義 Agent 的基本行為：感知、決策、行動
整合 LLM 進行自然語言議價
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from loguru import logger
from .llm_engine import LLMEngine

load_dotenv()


class BaseAgent(ABC):
    def __init__(self, agent_id: str, role: str):
        self.agent_id = agent_id
        self.role = role
        self.wallet_balance = 10.0  # 模擬餘額 (SOL)
        self.llm = LLMEngine()  # 初始化 LLM 引擎
        logger.info(f"🤖 Agent 啟動：{agent_id} ({role})")

    @abstractmethod
    def perceive(self, data: Any) -> Dict:
        """感知環境數據"""
        pass

    @abstractmethod
    def decide(self, perception: Dict) -> Dict:
        """根據感知做決策 (使用 LLM)"""
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
        # 使用 LLM 進行議價決策
        bids = perception["available_bids"]
        if not bids:
            return {"action": "wait", "reason": "no bids"}

        # 構建 LLM 提示詞
        system_prompt = f"""你是一個 AI 買方 Agent (ID: {self.agent_id})，負責評估賣方投標。
當前市場上有 {len(bids)} 個投標，請選擇最合適的一個。"""

        user_prompt = f"投標列表：{bids}\n你的預算：{self.wallet_balance} SOL\n請決定：接受哪個投標？為什麼？"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        llm_response = self.llm.chat(messages)

        # 解析 LLM 回應 (簡單起見，選擇價格最低的合理投標)
        best_bid = min(bids, key=lambda x: x["price"])
        if best_bid["price"] <= self.wallet_balance:
            return {"action": "accept", "bid": best_bid, "llm_reasoning": llm_response}
        else:
            return {"action": "reject", "reason": "too expensive", "llm_reasoning": llm_response}

    def act(self, decision: Dict) -> str:
        action = decision["action"]
        if action == "accept":
            return f"✅ 接受投標 {decision['bid']['bid_id']} (LLM: {decision.get('llm_reasoning', 'N/A')[:50]}...)"
        elif action == "reject":
            return f"❌ 拒絕投標：{decision['reason']} (LLM: {decision.get('llm_reasoning', 'N/A')[:50]}...)"
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
        # 使用 LLM 進行投標決策
        orders = perception["open_orders"]
        if not orders:
            return {"action": "wait"}

        # 構建 LLM 提示詞
        system_prompt = f"""你是一個 AI 賣方 Agent (ID: {self.agent_id})，專門提供 {self.service_type} 服務。
請根據市場情況決定投標價格。"""

        market_price = perception["market_price"]
        user_prompt = f"市場均價：{market_price} SOL\n你的成本：{self.cost_basis} SOL\n請決定：是否投標？價格多少？"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        llm_response = self.llm.chat(messages)

        # 簡單投標邏輯
        target_order = orders[0]
        bid_price = max(self.cost_basis + 0.05, market_price * 0.95)

        return {
            "action": "bid",
            "order_id": target_order["request_id"],
            "price": bid_price,
            "message": f"我可以提供 {self.service_type} 服務，價格優惠",
            "llm_reasoning": llm_response
        }

    def act(self, decision: Dict) -> str:
        if decision["action"] == "bid":
            return f"💰 投標訂單 {decision['order_id']} @ {decision['price']} SOL (LLM: {decision.get('llm_reasoning', 'N/A')[:50]}...)"
        return "⏳ 等待訂單中..."
