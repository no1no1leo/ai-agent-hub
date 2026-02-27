"""
Solana 錢包管理器
負責生成、載入和管理 Agent 的 Solana 錢包
"""
import os
import json
from typing import Optional
from loguru import logger
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore

class WalletManager:
    """
    錢包管理器
    支持從環境變數、文件或內存中加載密鑰
    """
    def __init__(self, private_key: Optional[str] = None):
        """
        初始化錢包管理器
        :param private_key: Base58 格式的私鑰字符串，或 JSON 格式的密鑰文件路徑
        """
        self.keypair: Optional[Keypair] = None
        self.public_key: Optional[Pubkey] = None
        
        if private_key:
            self.load(private_key)
        else:
            logger.warning("⚠️  未提供私鑰，錢包處於未激活狀態。")

    def load(self, secret: str):
        """
        加載錢包
        :param secret: Base58 私鑰字符串，或 JSON 文件路徑
        """
        try:
            # 嘗試作為 JSON 文件路徑加載
            if os.path.isfile(secret):
                with open(secret, 'r') as f:
                    key_data = json.load(f)
                    # Solana CLI 生成的 JSON 通常是數字數組
                    if isinstance(key_data, list):
                        self.keypair = Keypair.from_bytes(bytes(key_data))
                    elif isinstance(key_data, dict) and 'secret_key' in key_data:
                         # 處理其他格式
                        self.keypair = Keypair.from_bytes(bytes(key_data['secret_key']))
            else:
                # 嘗試作為 Base58 字符串或 JSON 字符串加載
                try:
                    # 嘗試直接從 Base58 解析 (solders 支持)
                    self.keypair = Keypair.from_base58_string(secret)
                except:
                    # 嘗試作為 JSON 數組字符串解析
                    key_data = json.loads(secret)
                    self.keypair = Keypair.from_bytes(bytes(key_data))
            
            self.public_key = self.keypair.pubkey()
            logger.info(f"✅ 錢包加載成功：{self.public_key}")
            
        except Exception as e:
            logger.error(f"❌ 錢包加載失敗：{e}")
            raise

    def create_new(self) -> Keypair:
        """
        創建新錢包
        :return: 新生成的 Keypair
        """
        self.keypair = Keypair()
        self.public_key = self.keypair.pubkey()
        logger.info(f"🆕 新錢包已創建：{self.public_key}")
        return self.keypair

    def sign_transaction(self, transaction) -> bytes:
        """
        簽署交易
        :param transaction: 待簽署的交易對象
        :return: 簽名後的交易字節
        """
        if not self.keypair:
            raise ValueError("錢包未加載，無法簽署交易")
        return self.keypair.sign(transaction)

    def get_balance(self, rpc_client) -> float:
        """
        查詢餘額
        :param rpc_client: Solana RPC 客戶端
        :return: SOL 餘額
        """
        if not self.public_key:
            return 0.0
        try:
            balance = rpc_client.get_balance(self.public_key)
            return balance.value / 1e9  # 轉換為 SOL
        except Exception as e:
            logger.error(f"查詢餘額失敗：{e}")
            return 0.0

    def export_keypair(self, as_json: bool = False) -> str:
        """
        導出密鑰
        :param as_json: 是否以 JSON 格式導出
        :return: Base58 私鑰字符串或 JSON 字符串
        """
        if not self.keypair:
            raise ValueError("錢包未加載")
        
        if as_json:
            return json.dumps(list(self.keypair.to_bytes_array()))
        else:
            return self.keypair.__str__() # 這會返回 Base58 字符串 (取決於 solders 版本，可能需要調整)

# 全域實例 (可選)
# wallet = WalletManager(os.getenv("SOLANA_PRIVATE_KEY"))
