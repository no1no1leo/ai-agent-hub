#!/usr/bin/env python3
"""
🏪 AI Agent Marketplace 演示
展示買方 Agent 如何透過市場競爭，以低成本完成原本高成本的任務
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.hub_market import HubMarket, TaskStatus
from marketplace.solver_agents import create_diverse_solvers, SolverAgent
from loguru import logger
import time

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def demo_marketplace():
    print_separator("🏪 AI Agent Marketplace - 成本優化演示")
    
    # 1. 初始化市場
    print_separator("步驟 1: 市場初始化")
    market = HubMarket()
    
    # 2. 建立多個 Solver Agents (代表市場上的供應方)
    print_separator("步驟 2: Solver Agents 進場")
    solvers = create_diverse_solvers()
    print(f"✅ 市場上共有 {len(solvers)} 個 Solver Agent 就緒")
    for s in solvers:
        print(f"   - {s.config.agent_id}: {s.config.model_name} "
              f"(成本：{s.config.cost_per_token*1000:.4f} SOL/k tokens)")
    
    # 3. 買方 Agent 發布一個高難度任務
    print_separator("步驟 3: 買方發布高難度任務")
    task_desc = "分析 10 萬筆電商交易數據，找出異常模式並生成報告"
    expected_tokens = 50000  # 預估需要 50k tokens
    direct_cost = 5.0  # 直接使用高階模型的預估成本 (SOL)
    
    task = market.create_task(
        description=task_desc,
        input_data="dataset_url: s3://bucket/data.csv",
        max_budget=direct_cost * 0.6,  # 買方希望比直接呼叫便宜 40%
        expected_tokens=expected_tokens,
        requester_id="buyer_analytics_001"
    )
    
    print(f"📝 任務描述：{task_desc}")
    print(f"🔢 預估 Token 數：{expected_tokens:,}")
    print(f"💰 直接使用高階模型成本：~{direct_cost} SOL")
    print(f"🎯 買方預算上限：{task.max_budget} SOL (節省 40%)")
    
    # 4. Solver Agents 掃描市場並投標
    print_separator("步驟 4: Solver Agents 自動競標")
    for solver in solvers:
        solver.scan_and_bid(market)
    
    # 顯示所有投標
    print(f"\n📊 市場投標情況:")
    bids = market.bids.get(task.task_id, [])
    if not bids:
        print("   ❌ 沒有收到任何投標")
        return
    
    for i, bid in enumerate(bids, 1):
        print(f"   {i}. {bid.bidder_id} ({bid.model_name}): {bid.bid_price} SOL")
    
    # 5. 市場自動選擇最佳投標
    print_separator("步驟 5: 市場自動媒合")
    winner = market.select_winner(task.task_id)
    
    if winner:
        print(f"🏆 得標者：{winner.bidder_id}")
        print(f"💰 得標價格：{winner.bid_price} SOL")
        print(f"📉 節省成本：{direct_cost - winner.bid_price:.2f} SOL "
              f"({(direct_cost - winner.bid_price)/direct_cost*100:.1f}%)")
        print(f"🤖 使用模型：{winner.model_name}")
        
        # 6. 模擬任務執行
        print_separator("步驟 6: 任務執行與結果提交")
        print("⏳ 任務執行中...")
        time.sleep(1)  # 模擬執行時間
        
        market.complete_task(task.task_id, "分析報告：發現 3 個異常模式...")
        print(f"✅ 任務完成！結果已提交")
        
        # 7. 市場統計
        print_separator("步驟 7: 市場統計")
        stats = market.get_market_stats()
        print(f"📊 總任務數：{stats['total_tasks']}")
        print(f"💰 總投標數：{stats['total_bids']}")
        print(f"🏆 平均得標價格：{stats['avg_winning_bid']:.2f} SOL")
        
    else:
        print("❌ 沒有合適的投標，任務失敗")
    
    print_separator("演示總結")
    print("💡 核心價值:")
    print("   1. 買方：以較低成本完成任務")
    print("   2. 賣方：利用閒置算力賺取代幣")
    print("   3. 平台：促進資源有效配置")
    print("\n🎭 演示完成！")

if __name__ == "__main__":
    demo_marketplace()
