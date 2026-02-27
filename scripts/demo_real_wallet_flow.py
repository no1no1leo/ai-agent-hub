#!/usr/bin/env python3
"""
真實錢包流程演示
展示一個完整的使用者旅程：生成錢包 -> 領取空投 -> 發布任務 -> 鏈上託管
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.wallet_manager import WalletManager
from marketplace.solana_escrow_real import escrow_service, client as solana_client

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def demo_flow():
    print_separator("🔗 真實 Solana 錢包流程演示")
    
    # 1. 買方生成錢包
    print_separator("步驟 1: 買方生成錢包")
    buyer_wallet = WalletManager()
    buyer_wallet.create_new()
    print(f"✅ 買方錢包已生成：{buyer_wallet.public_key}")
    
    # 2. 賣方生成錢包
    print_separator("步驟 2: 賣方生成錢包")
    seller_wallet = WalletManager()
    seller_wallet.create_new()
    print(f"✅ 賣方錢包已生成：{seller_wallet.public_key}")
    
    # 3. 模擬領取空投 (Devnet)
    print_separator("步驟 3: 領取測試 SOL (模擬)")
    print(f"🪂 正在為 {buyer_wallet.public_key} 請求 Devnet 空投...")
    # 真實場景需呼叫 faucet API，此處跳過
    print("✅ 模擬空投成功！餘額：1.0 SOL")
    
    # 4. 買方發布任務並建立託管
    print_separator("步驟 4: 建立鏈上託管")
    task_id = "task_demo_001"
    amount_lamports = int(0.5 * 1e9) # 0.5 SOL
    
    escrow_id = escrow_service.create_escrow_account(
        buyer_pubkey=buyer_wallet.public_key,
        seller_pubkey=seller_wallet.public_key,
        amount_lamports=amount_lamports,
        task_id=task_id
    )
    
    # 5. 買方注資
    print_separator("步驟 5: 買方注資到託管")
    try:
        escrow_service.fund_escrow(escrow_id, buyer_wallet.keypair)
        print("✅ 資金已鎖定在智能合約中")
    except Exception as e:
        print(f"❌ 注資失敗：{e}")
        return

    # 6. 模擬任務執行
    print_separator("步驟 6: 任務執行")
    print("⏳ 賣方正在執行任務...")
    import time
    time.sleep(1)
    print("✅ 任務完成！結果已提交")
    
    # 7. 確認完成並放款
    print_separator("步驟 7: 智能合約自動放款")
    try:
        escrow_service.complete_escrow(escrow_id, buyer_wallet.keypair)
        print(f"✅ 資金已釋放給賣方 {seller_wallet.public_key}")
    except Exception as e:
        print(f"❌ 放款失敗：{e}")
        return
    
    # 8. 總結
    print_separator("📊 流程總結")
    print(f"✅ 任務 ID: {task_id}")
    print(f"✅ 託管 ID: {escrow_id}")
    print(f"✅ 交易金額：{amount_lamports/1e9} SOL")
    print(f"✅ 狀態：已完成")
    print("\n💡 這就是去中心化交易的魅力：無需信任第三方，代碼即法律！")

if __name__ == "__main__":
    demo_flow()
