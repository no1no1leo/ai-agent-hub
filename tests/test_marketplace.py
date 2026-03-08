"""
AI Agent Hub 測試套件
運行: python -m pytest tests/ -v
"""
import pytest
import sys
import os

# 添加專案路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.hub_market import HubMarket, TaskStatus, Task, Bid
from marketplace.reputation import ReputationSystem, AgentReputation
from marketplace.solana_escrow import SolanaEscrowSimulator, EscrowStatus
from marketplace.strategies import (
    AggressiveStrategy, ConservativeStrategy, MarketFollowStrategy,
    SniperStrategy, RandomWalkStrategy, MarketState
)


class TestHubMarket:
    """測試市場核心功能"""
    
    def setup_method(self):
        """每個測試前重置市場"""
        self.market = HubMarket()
    
    def test_create_task(self):
        """測試創建任務"""
        task = self.market.create_task(
            description="測試任務",
            input_data="test.csv",
            max_budget=1.0,
            expected_tokens=1000,
            requester_id="buyer_01"
        )
        
        assert task.task_id in self.market.tasks
        assert task.status == TaskStatus.OPEN
        assert task.max_budget == 1.0
        assert task.requester_id == "buyer_01"
    
    def test_submit_bid(self):
        """測試提交投標"""
        task = self.market.create_task("測試", "data", 1.0, 1000)
        
        bid = self.market.submit_bid(
            task_id=task.task_id,
            bidder_id="agent_01",
            bid_price=0.5,
            estimated_tokens=1000,
            model_name="test_model"
        )
        
        assert bid.task_id == task.task_id
        assert bid.bid_price == 0.5
        assert len(self.market.bids[task.task_id]) == 1
    
    def test_select_winner(self):
        """測試選擇得標者"""
        task = self.market.create_task("測試", "data", 1.0, 1000)
        
        # 提交多個投標
        self.market.submit_bid(task.task_id, "agent_01", 0.8, 1000, "model")
        self.market.submit_bid(task.task_id, "agent_02", 0.5, 1000, "model")
        self.market.submit_bid(task.task_id, "agent_03", 0.9, 1000, "model")
        
        winner = self.market.select_winner(task.task_id)
        
        assert winner is not None
        assert winner.bidder_id == "agent_02"  # 最低價應該得標
        assert winner.bid_price == 0.5
        assert self.market.tasks[task.task_id].status == TaskStatus.IN_PROGRESS
    
    def test_select_winner_no_valid_bids(self):
        """測試無有效投標的情況"""
        task = self.market.create_task("測試", "data", 1.0, 1000)
        
        # 提交超過預算的投標
        self.market.submit_bid(task.task_id, "agent_01", 2.0, 1000, "model")
        
        winner = self.market.select_winner(task.task_id)
        
        assert winner is None
    
    def test_complete_task(self):
        """測試完成任務"""
        task = self.market.create_task("測試", "data", 1.0, 1000)
        self.market.submit_bid(task.task_id, "agent_01", 0.5, 1000, "model")
        self.market.select_winner(task.task_id)
        
        self.market.complete_task(task.task_id, "任務完成結果")
        
        assert self.market.tasks[task.task_id].status == TaskStatus.COMPLETED
        assert self.market.tasks[task.task_id].result == "任務完成結果"
    
    def test_get_market_stats(self):
        """測試市場統計"""
        # 創建一些任務和投標
        task1 = self.market.create_task("測試1", "data1", 1.0, 1000)
        task2 = self.market.create_task("測試2", "data2", 2.0, 2000)
        
        self.market.submit_bid(task1.task_id, "agent_01", 0.5, 1000, "model")
        self.market.submit_bid(task1.task_id, "agent_02", 0.8, 1000, "model")
        self.market.submit_bid(task2.task_id, "agent_01", 1.5, 2000, "model")
        
        stats = self.market.get_market_stats()
        
        assert stats["total_tasks"] == 2
        assert stats["total_bids"] == 3
        assert stats["active_tasks"] == 2


class TestReputationSystem:
    """測試信譽系統"""
    
    def setup_method(self):
        self.rep_system = ReputationSystem()
    
    def test_create_reputation(self):
        """測試創建信譽記錄"""
        rep = self.rep_system.get_or_create("agent_01")
        
        assert rep.agent_id == "agent_01"
        assert rep.total_tasks == 0
        assert rep.reputation_score > 80  # 初始分數（基於預設 4.0 評分）
    
    def test_update_reputation(self):
        """測試更新信譽"""
        self.rep_system.update_reputation("agent_01", completed=True, rating=5.0)
        self.rep_system.update_reputation("agent_01", completed=True, rating=4.0)
        
        rep = self.rep_system.get_or_create("agent_01")
        
        assert rep.total_tasks == 2
        assert rep.completed_tasks == 2
        assert rep.success_rate == 1.0
        assert 4.0 <= rep.avg_rating <= 4.5  # 考慮預設 4.0 評分的影響
    
    def test_reputation_score_calculation(self):
        """測試信譽分數計算"""
        # 完成多個任務
        for _ in range(10):
            self.rep_system.update_reputation("agent_01", completed=True, rating=5.0)
        
        rep = self.rep_system.get_or_create("agent_01")
        
        # 成功率 50 + 評分 40 + 經驗 1 = 91
        assert rep.reputation_score > 90
    
    def test_get_trusted_agents(self):
        """測試獲取可信賴 Agent"""
        # agent_01: 高分
        for _ in range(5):
            self.rep_system.update_reputation("agent_01", completed=True, rating=5.0)
        
        # agent_02: 低分
        self.rep_system.update_reputation("agent_02", completed=False)
        
        trusted = self.rep_system.get_trusted_agents(min_score=60.0)
        
        assert "agent_01" in trusted
        assert "agent_02" not in trusted


class TestSolanaEscrow:
    """測試 Solana 託管"""
    
    def setup_method(self):
        self.escrow = SolanaEscrowSimulator()
    
    def test_create_escrow(self):
        """測試創建託管"""
        escrow_id = self.escrow.create_escrow(
            task_id="task_01",
            buyer_id="buyer_01",
            seller_id="seller_01",
            amount=1.5
        )
        
        assert escrow_id in self.escrow.escrows
        assert self.escrow.escrows[escrow_id].amount == 1.5
        assert self.escrow.escrows[escrow_id].status == EscrowStatus.CREATED
    
    def test_fund_escrow(self):
        """測試託管注資"""
        escrow_id = self.escrow.create_escrow("task_01", "buyer_01", "seller_01", 1.5)
        
        result = self.escrow.fund_escrow(escrow_id)
        
        assert result is True
        assert self.escrow.escrows[escrow_id].status == EscrowStatus.FUNDED
        assert self.escrow.total_value_locked == 1.5
    
    def test_confirm_completion(self):
        """測試確認完成"""
        escrow_id = self.escrow.create_escrow("task_01", "buyer_01", "seller_01", 1.5)
        self.escrow.fund_escrow(escrow_id)
        
        result = self.escrow.confirm_completion(escrow_id, approved=True)
        
        assert result is True
        assert self.escrow.escrows[escrow_id].status == EscrowStatus.COMPLETED
        assert self.escrow.total_value_locked == 0.0
    
    def test_cancel_escrow(self):
        """測試取消託管"""
        escrow_id = self.escrow.create_escrow("task_01", "buyer_01", "seller_01", 1.5)
        self.escrow.fund_escrow(escrow_id)
        
        result = self.escrow.confirm_completion(escrow_id, approved=False)
        
        assert result is True
        assert self.escrow.escrows[escrow_id].status == EscrowStatus.CANCELLED


class TestBiddingStrategies:
    """測試競標策略"""
    
    def setup_method(self):
        self.market_state = MarketState(
            avg_price=0.8,
            min_price=0.5,
            max_price=1.2,
            total_bids=5,
            task_complexity=0.5
        )
        self.cost = 0.5
        self.max_budget = 1.0
    
    def test_aggressive_strategy(self):
        """測試激進策略"""
        strategy = AggressiveStrategy()
        bid = strategy.calculate_bid(self.cost, self.market_state, self.max_budget)
        
        # 激進策略: cost * 1.05
        expected = self.cost * 1.05
        assert bid == pytest.approx(expected, 0.01)
    
    def test_conservative_strategy(self):
        """測試保守策略"""
        strategy = ConservativeStrategy()
        bid = strategy.calculate_bid(self.cost, self.market_state, self.max_budget)
        
        # 保守策略: cost * 1.50
        expected = self.cost * 1.50
        assert bid == pytest.approx(expected, 0.01)
    
    def test_market_follow_strategy(self):
        """測試跟隨策略"""
        strategy = MarketFollowStrategy()
        bid = strategy.calculate_bid(self.cost, self.market_state, self.max_budget)
        
        # 跟隨策略: avg_price * 0.98
        expected = self.market_state.avg_price * 0.98
        assert bid == pytest.approx(expected, 0.01)
    
    def test_sniper_strategy_low_competition(self):
        """測試狙擊策略（低競爭）"""
        strategy = SniperStrategy()
        low_competition_state = MarketState(0.8, 0.5, 1.2, 2, 0.5)  # 只有 2 個投標
        
        bid = strategy.calculate_bid(self.cost, low_competition_state, self.max_budget)
        
        # 低競爭: cost * 1.40
        expected = self.cost * 1.40
        assert bid == pytest.approx(expected, 0.01)
    
    def test_sniper_strategy_high_competition(self):
        """測試狙擊策略（高競爭）"""
        strategy = SniperStrategy()
        high_competition_state = MarketState(0.8, 0.5, 1.2, 15, 0.5)  # 15 個投標
        
        bid = strategy.calculate_bid(self.cost, high_competition_state, self.max_budget)
        
        # 高競爭: cost * 1.02
        expected = self.cost * 1.02
        assert bid == pytest.approx(expected, 0.01)


class TestEdgeCases:
    """測試邊界情況"""
    
    def test_task_not_found(self):
        """測試任務不存在"""
        market = HubMarket()
        
        with pytest.raises(ValueError, match="Task not found"):
            market.submit_bid("non_existent_task", "agent_01", 0.5, 1000, "model")
    
    def test_escrow_not_found(self):
        """測試託管不存在"""
        escrow = SolanaEscrowSimulator()
        
        with pytest.raises(ValueError, match="Escrow not found"):
            escrow.fund_escrow("non_existent_escrow")
    
    def test_empty_market_stats(self):
        """測試空市場統計"""
        market = HubMarket()
        stats = market.get_market_stats()
        
        assert stats["total_tasks"] == 0
        assert stats["total_bids"] == 0
        assert stats["avg_winning_bid"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
