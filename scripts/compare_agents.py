#!/usr/bin/env python3
"""
⚔️ 傳統演算法 vs LLM 效能對比
展示兩者在速度、決策邏輯上的差異
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BuyerAgent as LLMBuyer, SellerAgent as LLMSeller
from agents.traditional_agent import TraditionalBuyerAgent, TraditionalSellerAgent
from hub.orderbook import OrderBook, ServiceType
from datetime import datetime

def benchmark_decision(agent, perception, iterations=100):
    """測試決策速度"""
    start = time.time()
    for _ in range(iterations):
        agent.decide(perception)
    end = time.time()
    return (end - start) / iterations * 1000  # 毫秒

def main():
    print("\n" + "="*70)
    print("⚔️  傳統演算法 vs LLM：效能與策略對比")
    print("="*70)

    # 1. 準備測試數據
    mock_bids = [
        {"bid_id": "bid_1", "price": 0.5, "seller_id": "seller_1"},
        {"bid_id": "bid_2", "price": 0.3, "seller_id": "seller_2"},
        {"bid_id": "bid_3", "price": 0.7, "seller_id": "seller_3"},
    ]
    perception = {"available_bids": mock_bids, "status": "active"}

    # 2. 初始化 Agent
    print("\n1️⃣  初始化 Agent...")
    llm_buyer = LLMBuyer("llm_buyer")
    trad_buyer = TraditionalBuyerAgent("trad_buyer")

    # 3. 速度測試
    print("\n2️⃣  速度測試 (各執行 100 次決策取平均)...")
    print("-" * 70)
    
    # LLM 速度
    t_llm = benchmark_decision(llm_buyer, perception)
    print(f"🤖 LLM Agent 平均耗時：   {t_llm:8.2f} ms")
    
    # 傳統速度
    t_trad = benchmark_decision(trad_buyer, perception)
    print(f"⚡ 傳統 Agent 平均耗時：   {t_trad:8.2f} ms")
    
    print(f"\n🚀 速度提升倍數：{t_llm / t_trad:.1f}x")

    # 4. 決策邏輯對比
    print("\n3️⃣  決策邏輯對比...")
    print("-" * 70)
    
    llm_result = llm_buyer.decide(perception)
    trad_result = trad_buyer.decide(perception)
    
    print(f"🤖 LLL 決策：")
    print(f"   動作：{llm_result['action']}")
    if 'bid' in llm_result:
        print(f"   選擇：{llm_result['bid']['bid_id']} (價格：{llm_result['bid']['price']})")
    print(f"   理由：{llm_result.get('llm_reasoning', 'N/A')[:60]}...")
    
    print(f"\n⚡ 傳統決策：")
    print(f"   動作：{trad_result['action']}")
    if 'bid' in trad_result:
        print(f"   選擇：{trad_result['bid']['bid_id']} (價格：{trad_result['bid']['price']})")
    print(f"   理由：{trad_result.get('reasoning', 'N/A')}")

    # 5. 總結
    print("\n" + "="*70)
    print("📊 總結建議")
    print("="*70)
    print("✅ 使用 LLM 情境：")
    print("   - 需要自然語言談判 (議價、說服)")
    print("   - 處理非結構化數據 (如：複雜的服務描述)")
    print("   - 需要創造性策略")
    
    print("\n✅ 使用傳統演算法情境：")
    print("   - 高頻交易 (HFT)")
    print("   - 標準化服務 (價格是唯一變量)")
    print("   - 資源受限環境 (邊緣運算)")
    print("="*70)

if __name__ == "__main__":
    main()
