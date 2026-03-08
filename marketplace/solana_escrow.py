"""
Solana 智能合約整合 (模擬層)
模擬與 Solana Escrow 合約的互動
"""
import uuid
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from loguru import logger
from enum import Enum

class EscrowStatus(Enum):
    CREATED = "created"
    FUNDED = "funded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

@dataclass
class EscrowAccount:
    """託管帳戶"""
    escrow_id: str
    task_id: str
    buyer_id: str
    seller_id: str
    amount: float  # SOL
    status: EscrowStatus = EscrowStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class SolanaEscrowSimulator:
    """
    Solana Escrow 模擬器
    模擬與真實 Solana 合約的互動
    """
    def __init__(self):
        self.escrows: Dict[str, EscrowAccount] = {}
        self.total_value_locked = 0.0
        logger.info("⛓️ Solana Escrow 模擬器已啟動")
    
    def create_escrow(self, task_id: str, buyer_id: str, seller_id: str, amount: float) -> str:
        """
        建立託管帳戶
        模擬：呼叫 Solana 合約的 initialize_escrow
        """
        escrow_id = str(uuid.uuid4())[:8]
        escrow = EscrowAccount(
            escrow_id=escrow_id,
            task_id=task_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=amount
        )
        self.escrows[escrow_id] = escrow
        logger.info(f"⛓️ [Solana] 建立託管：{escrow_id} | 金額：{amount} SOL")
        return escrow_id
    
    def fund_escrow(self, escrow_id: str) -> bool:
        """
        買方注入資金
        模擬：呼叫 token::transfer 從買方轉帳到託管
        """
        if escrow_id not in self.escrows:
            raise ValueError("Escrow not found")
        
        escrow = self.escrows[escrow_id]
        escrow.status = EscrowStatus.FUNDED
        self.total_value_locked += escrow.amount
        
        logger.info(f"💰 [Solana] 託管 {escrow_id} 已注資 {escrow.amount} SOL")
        return True
    
    def confirm_completion(self, escrow_id: str, approved: bool) -> bool:
        """
        確認任務完成並放款
        模擬：呼叫 Solana 合約的 confirm_delivery 或 cancel_escrow
        """
        if escrow_id not in self.escrows:
            raise ValueError("Escrow not found")
        
        escrow = self.escrows[escrow_id]
        
        if approved:
            escrow.status = EscrowStatus.COMPLETED
            escrow.completed_at = datetime.now(timezone.utc)
            self.total_value_locked -= escrow.amount
            logger.info(f"✅ [Solana] 任務完成！{escrow.amount} SOL 已釋放給 {escrow.seller_id}")
        else:
            escrow.status = EscrowStatus.CANCELLED
            self.total_value_locked -= escrow.amount
            logger.info(f"❌ [Solana] 任務取消！{escrow.amount} SOL 已退回給 {escrow.buyer_id}")
        
        return True
    
    def get_escrow_status(self, escrow_id: str) -> Optional[Dict]:
        """查詢託管狀態"""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        return {
            "escrow_id": escrow.escrow_id,
            "task_id": escrow.task_id,
            "buyer_id": escrow.buyer_id,
            "seller_id": escrow.seller_id,
            "amount": escrow.amount,
            "status": escrow.status.value,
            "created_at": escrow.created_at.isoformat(),
            "completed_at": escrow.completed_at.isoformat() if escrow.completed_at else None
        }
    
    def get_market_stats(self) -> Dict:
        """獲取市場統計"""
        return {
            "total_escrows": len(self.escrows),
            "total_value_locked": self.total_value_locked,
            "active_escrows": len([e for e in self.escrows.values() if e.status in [EscrowStatus.FUNDED, EscrowStatus.IN_PROGRESS]])
        }

# 全域實例
solana_escrow = SolanaEscrowSimulator()
