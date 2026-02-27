"""
模擬交易腳本
模擬一個買方 Agent 和一個賣方 Agent 在 Hub 上完成一次交易
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hub.orderbook import order_book, OrderRequest, Bid, ServiceType, OrderStatus
from agents.base_agent import BuyerAgent, SellerAgent
from datetime import datetime, timedelta
import time

def simulate_trade():
    print("=" * 60)
    print("🚀 開始模擬 AI Agent 交易")
    print("=" * 60)

    # 1. 初始化 Agents
    buyer = BuyerAgent("buyer_bot_001")
    seller = SellerAgent("seller_bot_001", ServiceType.DATA_ANALYSIS.value)

    # 2. 買方發布訂單
    order = OrderRequest(
        buyer_agent_id=buyer.agent_id,
        service_type=ServiceType.DATA_ANALYSIS,
        description="分析 Solana 鏈上最近 1 小時的交易數據",
        payload={"chain": "solana", "timeframe": "1h"},
        max_price=0.5,
        deadline=datetime.utcnow() + timedelta(hours=2)
    )
    order_book.create_order(order)

    # 3. 賣方感知訂單並投標
    # 模擬賣方看到訂單
    market_data = {
        "orders": [order.dict()],
        "avg_price": 0.4
    }
    perception = seller.perceive(market_data)
    decision = seller.decide(perception)
    
    print(f"\n🤖 {seller.agent_id} 決策：{decision}")
    
    if decision["action"] == "bid":
        bid = Bid(
            order_id=decision["order_id"],
            seller_agent_id=seller.agent_id,
            price=decision["price"],
            estimated_time=30,  # 預估 30 分鐘完成
            message=decision["message"]
        )
        order_book.place_bid(bid)

        # 4. 買方評估投標
        bids_data = {"bids": [bid.dict()]}
        buyer_perception = buyer.perceive(bids_data)
        buyer_decision = buyer.decide(buyer_perception)
        
        print(f"\n🤖 {buyer.agent_id} 決策：{buyer_decision}")
        
        if buyer_decision["action"] == "accept":
            print("\n✅ 交易達成！準備進入智能合約執行階段...")
            # 此處將觸發智能合約
            # 1. 買方將資金鎖定到 Escrow
            # 2. 賣方開始執行任務
            # 3. 完成後確認並放款
        else:
            print("\n❌ 交易未達成")
    else:
        print("\n❌ 賣方未投標")

    print("\n" + "=" * 60)
    print("模擬結束")
    print("=" * 60)

if __name__ == "__main__":
    simulate_trade()
