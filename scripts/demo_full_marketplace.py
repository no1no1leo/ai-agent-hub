#!/usr/bin/env python3
"""
🏪 AI Agent Marketplace 完整演示
包含：市場競標 + 信譽系統 + Solana 託管 + API 展示
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.hub_market import HubMarket, TaskStatus
from marketplace.reputation import reputation_system
from marketplace.solana_escrow import solana_escrow
from marketplace.solver_agents import create_diverse_solvers

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def demo_full_marketplace():
    print_separator("🏪 AI Agent Marketplace 完整演示")
    
    # 1. 初始化
    print_separator("步驟 1: 系統初始化")
    market = HubMarket()
    print("✅ 市場已啟動")
    print("✅ 信譽系統已啟動")
    print("✅ Solana 託管已啟動")
    
    # 2. 建立任務
    print_separator("步驟 2: 買方發布任務")
    task = market.create_task(
        description="分析 10 萬筆電商數據",
        input_data="s3://data.csv",
        max_budget=3.0,
        expected_tokens=50000,
        requester_id="buyer_001"
    )
    print(f"📝 任務 ID: {task.task_id}")
    print(f"💰 預算：{task.max_budget} SOL")
    
    # 3. Solver Agents 投標
    print_separator("步驟 3: Solver Agents 競標")
    solvers = create_diverse_solvers()
    for solver in solvers:
        solver.scan_and_bid(market)
    
    bids = market.bids.get(task.task_id, [])
    print(f"📊 收到 {len(bids)} 個投標")
    for i, bid in enumerate(bids, 1):
        print(f"   {i}. {bid.bidder_id}: {bid.bid_price} SOL")
    
    # 4. 選擇得標者
    print_separator("步驟 4: 市場媒合")
    winner = market.select_winner(task.task_id)
    
    if winner:
        print(f"🏆 得標者：{winner.bidder_id}")
        print(f"💰 得標價格：{winner.bid_price} SOL")
        
        # 5. 建立 Solana 託管
        print_separator("步驟 5: Solana 智能合約")
        escrow_id = solana_escrow.create_escrow(
            task_id=task.task_id,
            buyer_id=task.requester_id,
            seller_id=winner.bidder_id,
            amount=winner.bid_price
        )
        print(f"⛓️  託管帳戶：{escrow_id}")
        
        # 注資
        solana_escrow.fund_escrow(escrow_id)
        print(f"💰 買方已注資 {winner.bid_price} SOL")
        
        # 6. 模擬任務執行
        print_separator("步驟 6: 任務執行")
        print("⏳ 任務執行中...")
        market.complete_task(task.task_id, "分析報告完成")
        print("✅ 任務完成")
        
        # 7. 更新信譽
        print_separator("步驟 7: 信譽更新")
        reputation_system.update_reputation(winner.bidder_id, completed=True, rating=4.8)
        rep_card = reputation_system.get_agent_card(winner.bidder_id)
        print(rep_card)
        
        # 8. 放款
        print_separator("步驟 8: 智能合約放款")
        solana_escrow.confirm_completion(escrow_id, approved=True)
        print("✅ 資金已釋放給賣方")
        
        # 9. 市場統計
        print_separator("步驟 9: 市場統計")
        stats = solana_escrow.get_market_stats()
        print(f"📊 總託管數：{stats['total_escrows']}")
        print(f"💰 鎖定總價值：{stats['total_value_locked']:.4f} SOL")
        
    else:
        print("❌ 無有效投標")
    
    print_separator("演示完成")
    print("💡 完整流程：")
    print("   1. 買方發布任務")
    print("   2. Solver Agents 競標")
    print("   3. 市場自動媒合")
    print("   4. Solana 託管鎖定資金")
    print("   5. 任務執行")
    print("   6. 更新信譽")
    print("   7. 智能合約放款")

if __name__ == "__main__":
    demo_full_marketplace()
