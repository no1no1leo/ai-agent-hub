#!/usr/bin/env python3
"""
🎭 AI Agent 交易演示
展示完整的 LLM 自然語言議價過程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BuyerAgent, SellerAgent
from hub.orderbook import OrderBook, OrderRequest, ServiceType, Bid
from datetime import datetime, timedelta

def print_separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def demo_trading_cycle():
    """演示完整的交易週期"""
    print_separator("🎭 AI Agent 交易演示 - LLM 自然語言議價")
    
    # 1. 建立訂單簿
    print_separator("步驟 1: 建立訂單簿")
    orderbook = OrderBook()
    
    # 2. 買方發布需求
    print_separator("步驟 2: 買方發布需求")
    buyer = BuyerAgent("buyer_pro_001")
    
    order = OrderRequest(
        buyer_agent_id=buyer.agent_id,
        service_type=ServiceType.DATA_ANALYSIS,
        description="分析電商銷售數據，找出趨勢與異常",
        payload={"dataset_size": "10GB", "deadline": "7 days"},
        max_price=1.0,
        deadline=datetime.utcnow() + timedelta(days=7)
    )
    orderbook.create_order(order)
    print(f"📝 訂單內容：{order.description}")
    print(f"💰 預算上限：{order.max_price} SOL")
    
    # 3. 賣方 1 號投標
    print_separator("步驟 3: 賣方 1 號 (低價策略) 進行 LLM 議價")
    seller1 = SellerAgent("seller_budget_001", "data_analysis")
    seller1.cost_basis = 0.2  # 成本較低
    
    perception1 = {
        "open_orders": [{"request_id": order.request_id}],
        "market_price": 0.8
    }
    decision1 = seller1.decide(perception1)
    print(f"🤖 賣方 1 號 LLM 想法：{decision1.get('llm_reasoning', 'N/A')}")
    
    # 送出投標
    bid1 = Bid(
        order_id=order.request_id,
        seller_agent_id=seller1.agent_id,
        price=decision1["price"],
        message=decision1["message"]
    )
    orderbook.place_bid(bid1)
    print(f"💰 賣方 1 號投標價格：{bid1.price} SOL")
    
    # 4. 賣方 2 號投標 (高品質策略)
    print_separator("步驟 4: 賣方 2 號 (高品質策略) 進行 LLM 議價")
    seller2 = SellerAgent("seller_premium_001", "data_analysis")
    seller2.cost_basis = 0.4  # 成本較高，但品質好
    
    perception2 = {
        "open_orders": [{"request_id": order.request_id}],
        "market_price": 0.8
    }
    decision2 = seller2.decide(perception2)
    print(f"🤖 賣方 2 號 LLM 想法：{decision2.get('llm_reasoning', 'N/A')}")
    
    # 送出投標
    bid2 = Bid(
        order_id=order.request_id,
        seller_agent_id=seller2.agent_id,
        price=decision2["price"],
        message=decision2["message"]
    )
    orderbook.place_bid(bid2)
    print(f"💰 賣方 2 號投標價格：{bid2.price} SOL")
    
    # 5. 買方評估所有投標
    print_separator("步驟 5: 買方 Agent 使用 LLM 評估所有投標")
    all_bids = orderbook.get_bids(order.request_id)
    print(f"📊 市場上共有 {len(all_bids)} 個投標")
    
    buyer_perception = {
        "available_bids": [
            {"bid_id": b.bid_id, "price": b.price, "seller_id": b.seller_agent_id}
            for b in all_bids
        ],
        "status": "active"
    }
    
    buyer_decision = buyer.decide(buyer_perception)
    print(f"🤖 買方 LLM 評估：{buyer_decision.get('llm_reasoning', 'N/A')}")
    
    result = buyer.act(buyer_decision)
    print(f"\n🎯 最終決策：{result}")
    
    # 6. 總結
    print_separator("📊 演示總結")
    print(f"✅ 買方最終選擇：{buyer_decision['action']}")
    if buyer_decision['action'] == 'accept':
        print(f"🏆 得標賣方：{buyer_decision['bid']['seller_id']}")
        print(f"💰 成交價格：{buyer_decision['bid']['price']} SOL")
    print(f"💡 LLM 在整個過程中提供了自然語言的議價推理")
    print("\n🎭 演示完成！")

if __name__ == "__main__":
    demo_trading_cycle()
