"""
多幣種錢包管理器 (Multi-Currency Wallet)
支援 SOL 與多種 SPL 穩定幣 (USDC, USDT, DAI)
"""
import os
from typing import Dict, Optional, List
from loguru import logger
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed

# 常見穩定幣在 Solana Devnet/Mainnet 的 Mint Address
STABLECOIN_MINTS = {
    "devnet": {
        "USDC": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU", # 範例地址 (Devnet 需自行鑄幣或映射)
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", # 範例
    },
    "mainnet-beta": {
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "DAI": "EjmyN6qEC1Tf1JxiG1ae7UTJhUxSwk1TCWNWqxWV4J6o"
    }
}

class MultiCurrencyWallet:
    def __init__(self, private_key: Optional[str] = None, network: str = "devnet"):
        self.network = network
        self.rpc_url = f"https://api.{network}.solana.com"
        self.client = Client(self.rpc_url)
        self.keypair: Optional[Keypair] = None
        self.public_key: Optional[Pubkey] = None
        
        if private_key:
            self.load(private_key)
        else:
            logger.warning("⚠️  未提供私鑰，錢包處於未激活狀態。")

    def load(self, secret: str):
        """加載錢包 (支持 Base58 或 JSON)"""
        try:
            if os.path.isfile(secret):
                import json
                with open(secret, 'r') as f:
                    key_data = json.load(f)
                    if isinstance(key_data, list):
                        self.keypair = Keypair.from_bytes(bytes(key_data))
            else:
                self.keypair = Keypair.from_base58_string(secret)
            
            self.public_key = self.keypair.pubkey()
            logger.info(f"✅ 多幣種錢包已加載：{self.public_key}")
        except Exception as e:
            logger.error(f"❌ 錢包加載失敗：{e}")
            raise

    def get_balance_sol(self) -> float:
        """獲取 SOL 餘額"""
        if not self.public_key: return 0.0
        try:
            balance = self.client.get_balance(self.public_key)
            return balance.value / 1e9
        except: return 0.0

    def get_token_balance(self, mint_symbol: str) -> float:
        """
        獲取特定代幣 (如 USDC) 餘額
        邏輯：找到該代幣對應的 Token Account (ATA)
        """
        if not self.public_key or not self.keypair: return 0.0
        
        mint_str = STABLECOIN_MINTS.get(self.network, {}).get(mint_symbol)
        if not mint_str:
            logger.warning(f"⚠️  未找到 {mint_symbol} 在 {self.network} 的合約地址")
            return 0.0

        try:
            mint_pubkey = Pubkey.from_string(mint_str)
            # 獲取或計算關聯代幣賬戶 (ATA)
            # 注意：真實環境需調用 get_token_accounts_by_owner 或使用 derive_ata
            # 此處為簡化邏輯，實際需使用 spl-token 庫或手計算 ATA
            # 這裡模擬返回 0，實際需實作 ATA 查找邏輯
            accounts = self.client.get_token_accounts_by_owner(
                self.public_key, 
                {"mint": mint_pubkey}
            )
            if accounts.value:
                # 取第一個 ATA
                token_account = accounts.value[0].pubkey
                balance_info = self.client.get_token_account_balance(token_account)
                return float(balance_info.value.ui_amount) if balance_info.value.ui_amount else 0.0
            return 0.0
        except Exception as e:
            # logger.error(f"查詢 {mint_symbol} 餘額失敗：{e}")
            return 0.0

    def get_all_balances(self) -> Dict[str, float]:
        """一次獲取所有餘額"""
        balances = {"SOL": self.get_balance_sol()}
        for symbol in STABLECOIN_MINTS.get(self.network, {}).keys():
            balances[symbol] = self.get_token_balance(symbol)
        return balances

# 全域實例範例
# wallet = MultiCurrencyWallet(os.getenv("SOLANA_PRIVATE_KEY"), "devnet")
