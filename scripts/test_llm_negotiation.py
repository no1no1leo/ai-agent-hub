#!/usr/bin/env python3
"""
測試 LLM 議價功能
驗證 Agent 是否能使用 NVIDIA NIM API 進行自然語言決策
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BuyerAgent, SellerAgent
from hub.orderbook import OrderBook, OrderRequest, ServiceType

def test_llm_buyer():
    """測試買方 Agent 的 LLM 議價"""
    print("\n=== 測試買方 Agent (LLM 議價) ===")
    buyer = BuyerAgent("buyer_llm_001")
    
    # 模擬市場投標 (符合 base_agent.py 預期的格式)
    mock_bids = [
        {"bid_id": "bid_1", "price": 0.5, "seller_id": "seller_1"},
        {"bid_id": "bid_2", "price": 0.3, "seller_id": "seller_2"},
        {"bid_id": "bid_3", "price": 0.7, "seller_id": "seller_3"},
    ]
    
    # 修正：使用 "available_bids" 而非 "bids"
    perception = {"available_bids": mock_bids, "status": "active"}
    decision = buyer.decide(perception)
    action_result = buyer.act(decision)
    
    print(f"決策結果：{decision}")
    print(f"執行動作：{action_result}")
    return True

def test_llm_seller():
    """測試賣方 Agent 的 LLM 投標"""
    print("\n=== 測試賣方 Agent (LLM 投標) ===")
    seller = SellerAgent("seller_llm_001", "data_analysis")
    
    # 模擬市場訂單 (符合 base_agent.py 預期的格式)
    mock_orders = [
        {"request_id": "order_1", "service_type": "data_analysis", "max_price": 1.0},
    ]
    
    # 修正：使用 "open_orders" 和 "market_price"
    perception = {"open_orders": mock_orders, "market_price": 0.5}
    decision = seller.decide(perception)
    action_result = seller.act(decision)
    
    print(f"決策結果：{decision}")
    print(f"執行動作：{action_result}")
    return True

if __name__ == "__main__":
    print("🧪 開始測試 LLM 議價功能...")
    print(f"NVIDIA NIM API 狀態：{'✅ 已啟用' if 'NVIDIA_NIM_API_KEY' in __import__('os').environ else '⚠️  未啟用 (使用模擬模式)'}")
    
    test_llm_buyer()
    test_llm_seller()
    
    print("\n✅ 測試完成！")
