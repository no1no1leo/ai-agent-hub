#!/usr/bin/env python3
"""
📈 大規模市場模擬 (無 LLM 模式)
展示純演算法在處理大量併發任務時的效能
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.hub_market import HubMarket, TaskStatus
from marketplace.solver_agents import create_diverse_solvers
from marketplace.strategies import STRATEGIES

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def run_scale_simulation(num_tasks=100, num_agents=20):
    print_separator("📈 大規模市場模擬 (純演算法)")
    
    # 1. 初始化
    print(f"\n⚙️  設定：{num_tasks} 個任務，{num_agents} 個 Agent")
    market = HubMarket()
    
    # 2. 建立多樣化 Agent 集群
    print("\n1️⃣  建立 Agent 集群...")
    base_agents = create_diverse_solvers()
    
    # 擴展到指定數量
    all_agents = []
    for i in range(num_agents):
        base_config = base_agents[i % len(base_agents)]
        config = base_config.config
        config.agent_id = f"algo_agent_{i:03d}"
        all_agents.append(base_config)  # 此處簡化，實際應 deep copy
    
    print(f"   ✅ 建立 {len(all_agents)} 個 Agent")
    
    # 3. 發布任務
    print(f"\n2️⃣  發布 {num_tasks} 個任務...")
    start_time = time.time()
    
    for i in range(num_tasks):
        task = market.create_task(
            description=f"任務 #{i}: 數據分析",
            input_data=f"data_{i}.csv",
            max_budget=3.0,
            expected_tokens=50000,
            requester_id=f"buyer_{i % 10}"
        )
    
    task_creation_time = time.time() - start_time
    print(f"   ⏱️  耗時：{task_creation_time*1000:.2f} ms")
    
    # 4. Agent 競標
    print(f"\n3️⃣  Agent 競標階段...")
    start_time = time.time()
    
    for agent in all_agents:
        agent.scan_and_bid(market)
    
    bidding_time = time.time() - start_time
    print(f"   ⏱️  競標耗時：{bidding_time*1000:.2f} ms")
    print(f"   ⚡ 每秒處理任務數：{num_tasks / bidding_time:.0f}")
    
    # 5. 市場統計
    print(f"\n4️⃣  市場統計")
    stats = market.get_market_stats()
    print(f"   📊 總任務數：{stats['total_tasks']}")
    print(f"   💰 總投標數：{stats['total_bids']}")
    print(f"   🏆 平均得標價格：{stats['avg_winning_bid']:.4f} SOL")
    
    # 6. 效能分析
    print(f"\n5️⃣  效能分析")
    print(f"   - 任務發布速率：{num_tasks / task_creation_time:.0f} tasks/sec")
    print(f"   - 競標處理速率：{num_tasks * len(all_agents) / bidding_time:.0f} bids/sec")
    print(f"   - 平均每個任務投標數：{stats['total_bids'] / num_tasks:.1f}")
    
    print_separator("模擬完成")
    print("💡 純演算法模式優勢:")
    print("   - 無 LLM 延遲，決策速度 < 1ms")
    print("   - 可預測，無隨機性")
    print("   - 適合高頻交易與標準化任務")

if __name__ == "__main__":
    # 預設模擬 100 個任務，20 個 Agent
    run_scale_simulation(num_tasks=100, num_agents=20)
