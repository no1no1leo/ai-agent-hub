"""
傳統演算法 Agent
不使用 LLM，僅靠數學規則與賽局理論進行決策
特點：極速、穩定、可預測
"""
import random
from typing import Dict, Any, List
from loguru import logger
from .base_agent import BuyerAgent, SellerAgent

class TraditionalBuyerAgent(BuyerAgent):
    """
    傳統買方：
    1. 過濾：只考慮價格低於預算的投標
    2. 排序：優先選擇價格最低者
    3. 打破平手：若價格相同，隨機選擇或選擇 ID 較小者
    """
    def __init__(self, agent_id: str):
        # 注意：這裡我們不初始化 LLM，避免資源浪費
        super(BuyerAgent, self).__init__(agent_id, "buyer") 
        self.wallet_balance = 10.0
        logger.info(f"🤖 [傳統] 買方 Agent 啟動：{agent_id} (無 LLM)")

    def decide(self, perception: Dict) -> Dict:
        bids = perception.get("available_bids", [])
        if not bids:
            return {"action": "wait", "reason": "no bids"}

        # 過濾：只留買得起的
        affordable_bids = [b for b in bids if b["price"] <= self.wallet_balance]
        
        if not affordable_bids:
            return {"action": "reject", "reason": "all too expensive"}

        # 策略：選擇最低價 (若同價則隨機)
        best_bid = min(affordable_bids, key=lambda x: x["price"])
        
        return {
            "action": "accept",
            "bid": best_bid,
            "reasoning": f"最低價投標：{best_bid['price']} SOL"
        }

    def act(self, decision: Dict) -> str:
        if decision["action"] == "accept":
            return f"✅ [傳統] 接受投標 {decision['bid']['bid_id']} @ {decision['bid']['price']} SOL"
        return f"❌ [傳統] 拒絕：{decision['reason']}"


class TraditionalSellerAgent(SellerAgent):
    """
    傳統賣方：
    1. 計算：成本 + 預期利潤
    2. 觀察：參考市場均價
    3. 策略：
       - 激進：市價 * 0.95 (搶單)
       - 保守：成本 * 1.5 (高利潤)
       - 跟隨：市價 (跟隨市場)
    """
    def __init__(self, agent_id: str, service_type: str, strategy: str = "aggressive"):
        super(SellerAgent, self).__init__(agent_id, "seller")
        self.service_type = service_type
        self.cost_basis = 0.1
        self.strategy = strategy
        logger.info(f"🤖 [傳統] 賣方 Agent 啟動：{agent_id} (策略:{strategy})")

    def decide(self, perception: Dict) -> Dict:
        orders = perception.get("open_orders", [])
        if not orders:
            return {"action": "wait"}

        market_price = perception.get("market_price", 0.5)
        target_order = orders[0]

        # 根據策略定價
        if self.strategy == "aggressive":
            # 激進：比市價低 5% 搶單
            bid_price = market_price * 0.95
        elif self.strategy == "conservative":
            # 保守：成本 + 50% 利潤
            bid_price = self.cost_basis * 1.5
        else:
            # 跟隨：市價
            bid_price = market_price

        # 確保不虧本
        bid_price = max(bid_price, self.cost_basis + 0.01)

        return {
            "action": "bid",
            "order_id": target_order["request_id"],
            "price": round(bid_price, 4),
            "message": f"[傳統] {self.service_type} 服務投標",
            "reasoning": f"{self.strategy} 策略：市價{market_price} -> 投標{bid_price}"
        }

    def act(self, decision: Dict) -> str:
        if decision["action"] == "bid":
            return f"💰 [傳統] 投標 {decision['order_id']} @ {decision['price']} SOL ({decision.get('reasoning', '')})"
        return "⏳ [傳統] 等待訂單中..."


def compare_strategies():
    """比較傳統演算法與 LLM 的差異"""
    print("\n--- ⚡ 速度與效能比較 ---")
    print("LLM 模式:")
    print("  - 延遲：500ms ~ 3000ms (取決於網路與模型大小)")
    print("  - 成本：每千 token 約 $0.00X ~ $0.XXX")
    print("  - 優點：靈活、可處理複雜語意、可談判")
    print("  - 缺點：慢、貴、不穩定")
    
    print("\n傳統演算法模式:")
    print("  - 延遲：< 1ms (微秒級)")
    print("  - 成本：$0 (僅需 CPU 運算)")
    print("  - 優點：極速、免費、穩定、可預測")
    print("  - 缺點：僵硬、無法處理非結構化數據")

if __name__ == "__main__":
    compare_strategies()
