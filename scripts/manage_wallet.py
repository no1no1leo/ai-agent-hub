#!/usr/bin/env python3
"""
錢包管理工具
功能：生成新錢包、查看餘額、導出密鑰
"""
import sys
import os
import json
import argparse

# 添加上層目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.wallet_manager import WalletManager
from solana.rpc.api import Client
from solders.pubkey import Pubkey  # type: ignore

def create_wallet():
    """創建新錢包"""
    print("🆕 正在生成新的 Solana 錢包...")
    wm = WalletManager()
    wm.create_new()
    
    print(f"\n✅ 錢包生成成功！")
    print(f"公鑰 (Public Key): {wm.public_key}")
    print(f"⚠️  請務必安全保存以下私鑰，遺遺後果自負：")
    print(f"私鑰 (Base58): {wm.keypair}") # 這裡可能需要調整以獲取正確的 Base58 字符串
    
    # 建議保存到環境變數
    print(f"\n💡 建議操作:")
    print(f'將私鑰設置為環境變數：export SOLANA_PRIVATE_KEY="{wm.keypair}"')

def check_balance(public_key: str, rpc_url: str = "https://api.devnet.solana.com"):
    """檢查餘額"""
    print(f"🔍 正在查詢 {public_key} 在 {rpc_url} 的餘額...")
    try:
        client = Client(rpc_url)
        pubkey = Pubkey.from_string(public_key)
        balance = client.get_balance(pubkey)
        print(f"💰 餘額：{balance.value / 1e9} SOL")
    except Exception as e:
        print(f"❌ 查詢失敗：{e}")

def main():
    parser = argparse.ArgumentParser(description="AI Agent Hub 錢包管理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令類型")

    # create 命令
    parser_create = subparsers.add_parser("create", help="生成新錢包")
    
    # balance 命令
    parser_balance = subparsers.add_parser("balance", help="查詢餘額")
    parser_balance.add_argument("public_key", type=str, help="公鑰地址")
    parser_balance.add_argument("--rpc", type=str, default="https://api.devnet.solana.com", help="RPC 節點")

    args = parser.parse_args()

    if args.command == "create":
        create_wallet()
    elif args.command == "balance":
        check_balance(args.public_key, args.rpc)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
