#!/usr/bin/env python3
"""
💰 注入流動性：發布賞金任務
模擬人類發布者發布一個帶有真實 Devnet SOL 獎勵的任務，
以此啟動 Agent 經濟飛輪。
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.wallet_manager import WalletManager
from marketplace.solana_escrow_real import escrow_service
from marketplace.hub_market import HubMarket

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def inject_bounty():
    print_separator("💰 啟動 Agent 經濟：注入流動性")
    
    # 1. 初始化人類發布者錢包 (模擬)
    print("1️⃣  初始化人類發布者錢包...")
    # 在真實場景中，這裡應從環境變數加載人類的私鑰
    # 此處為演示，我們臨時生成一個
    human_wallet = WalletManager()
    human_wallet.create_new()
    print(f"   人類錢包：{human_wallet.public_key}")
    print(f"   ⚠️  請記得此錢包需有 Devnet SOL 才能真實支付！")
    
    # 2. 初始化市場
    market = HubMarket()
    
    # 3. 發布賞金任務
    print("\n2️⃣  發布賞金任務...")
    task_desc = "分析比特幣與以太幣的相關性 (真實賞金任務)"
    reward_sol = 0.5  # 0.5 SOL 獎勵
    
    task = market.create_task(
        description=task_desc,
        input_data="https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
        max_budget=reward_sol,
        expected_tokens=5000,
        requester_id="human_bounty_hunter"
    )
    print(f"   📝 任務：{task_desc}")
    print(f"   💰 獎勵：{reward_sol} SOL")
    
    # 4. 建立鏈上託管 (模擬真實注資)
    print("\n3️⃣  建立鏈上託管 (Escrow)...")
    # 此處假設有一個 Solver Agent 已經存在並等待任務
    # 為演示，我們假設 Solver 是 "agent_solver_001"
    # 在真實鏈上，這裡需要 Solver 的公鑰
    # 此處僅做邏輯演示
    print("   ⏳ 等待 Solver Agent 發現任務並投標...")
    print("   (此步驟在真實環境中由 Agent 自動完成)")
    
    # 模擬等待
    time.sleep(2)
    
    print("\n   💡 提示：")
    print("   要讓此任務真正被執行，您需要：")
    print("   1. 運行一個 Solver Agent (scripts/demo_real_wallet_flow.py)")
    print("   2. 或者等待其他開發者的 Agent 接入並投標")
    
    print_separator("🚀 經濟飛輪已啟動")
    print("現在市場上有一個真實獎勵的任務。")
    print("這將吸引 Agent 們進場競爭，從而形成經濟循環。")
    print("\n下一步：運行 'python scripts/demo_real_wallet_flow.py' 模擬一個 Agent 來賺取這筆賞金！")

if __name__ == "__main__":
    inject_bounty()
