"""
信譽系統 (Reputation System)
防止低價低質，確保任務完成品質
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
from loguru import logger

@dataclass
class AgentReputation:
    """Agent 信譽記錄"""
    agent_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_rating: float = 4.0  # 初始 4.0 分 (滿分 5 分)
    total_earnings: float = 0.0
    avg_latency_score: float = 1.0
    avg_budget_score: float = 1.0
    verification_passes: int = 0
    verification_failures: int = 0
    join_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # 最近 10 次評價
    recent_ratings: List[float] = field(default_factory=lambda: [4.0] * 10)
    recent_latency_scores: List[float] = field(default_factory=lambda: [1.0] * 5)
    recent_budget_scores: List[float] = field(default_factory=lambda: [1.0] * 5)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 1.0
        return self.completed_tasks / self.total_tasks
    
    @property
    def reputation_score(self) -> float:
        """
        信譽評分 (0-100)
        綜合：成功率 + 平均評分 + 驗證品質 + 經驗
        """
        success_component = self.success_rate * 40
        rating_component = (self.avg_rating / 5.0) * 25
        verification_rate = (
            self.verification_passes / (self.verification_passes + self.verification_failures)
            if (self.verification_passes + self.verification_failures) > 0 else 1.0
        )
        verification_component = verification_rate * 15
        latency_component = self.avg_latency_score * 5
        budget_component = self.avg_budget_score * 5

        # 經驗加成：每完成 10 個任務 +1 分，最多 10 分
        exp_component = min(10, self.completed_tasks // 10)

        return min(100, success_component + rating_component + verification_component + latency_component + budget_component + exp_component)
    
    def add_task_result(
        self,
        completed: bool,
        rating: Optional[float] = None,
        latency_score: Optional[float] = None,
        budget_score: Optional[float] = None,
        verified: Optional[bool] = None,
    ):
        """更新任務結果"""
        self.total_tasks += 1
        if completed:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1

        if verified is True:
            self.verification_passes += 1
        elif verified is False:
            self.verification_failures += 1

        if rating is not None:
            self.recent_ratings.append(rating)
            if len(self.recent_ratings) > 10:
                self.recent_ratings.pop(0)
            self.avg_rating = sum(self.recent_ratings) / len(self.recent_ratings)

        if latency_score is not None:
            self.recent_latency_scores.append(latency_score)
            if len(self.recent_latency_scores) > 5:
                self.recent_latency_scores.pop(0)
            self.avg_latency_score = sum(self.recent_latency_scores) / len(self.recent_latency_scores)

        if budget_score is not None:
            self.recent_budget_scores.append(budget_score)
            if len(self.recent_budget_scores) > 5:
                self.recent_budget_scores.pop(0)
            self.avg_budget_score = sum(self.recent_budget_scores) / len(self.recent_budget_scores)

        logger.info(
            f"📊 {self.agent_id} 信譽更新：總任務={self.total_tasks}, "
            f"成功率={self.success_rate:.1%}, 評分={self.avg_rating:.1f}, "
            f"驗證通過={self.verification_passes}, 驗證失敗={self.verification_failures}"
        )

class ReputationSystem:
    """全域信譽系統"""
    def __init__(self):
        self.reputations: Dict[str, AgentReputation] = {}
        logger.info("🏛️ 信譽系統初始化完成")
    
    def get_or_create(self, agent_id: str) -> AgentReputation:
        """獲取或建立信譽記錄"""
        if agent_id not in self.reputations:
            self.reputations[agent_id] = AgentReputation(agent_id=agent_id)
            logger.info(f"🆕 為 {agent_id} 建立信譽記錄")
        return self.reputations[agent_id]
    
    def update_reputation(
        self,
        agent_id: str,
        completed: bool,
        rating: Optional[float] = None,
        latency_score: Optional[float] = None,
        budget_score: Optional[float] = None,
        verified: Optional[bool] = None,
    ):
        """更新 Agent 信譽"""
        rep = self.get_or_create(agent_id)
        rep.add_task_result(completed, rating, latency_score, budget_score, verified)

    def update_from_verification(
        self,
        agent_id: str,
        approved: bool,
        rating: Optional[float] = None,
        latency_score: float = 1.0,
        budget_score: float = 1.0,
    ):
        """根據驗證結果更新信譽"""
        self.update_reputation(
            agent_id=agent_id,
            completed=approved,
            rating=rating if rating is not None else (5.0 if approved else 2.5),
            latency_score=latency_score,
            budget_score=budget_score,
            verified=approved,
        )
    
    def get_trusted_agents(self, min_score: float = 60.0) -> List[str]:
        """獲取信譽良好的 Agent 列表"""
        trusted = []
        for agent_id, rep in self.reputations.items():
            if rep.reputation_score >= min_score:
                trusted.append(agent_id)
        return trusted
    
    def get_agent_card(self, agent_id: str) -> str:
        """生成 Agent 信譽卡片"""
        rep = self.get_or_create(agent_id)
        return f"""
📊 Agent 信譽卡片: {agent_id}
├─ 信譽評分：{rep.reputation_score:.1f}/100
├─ 成功率：{rep.success_rate:.1%}
├─ 平均評分：{rep.avg_rating:.1f}/5.0
├─ 總任務數：{rep.total_tasks}
├─ 總收益：{rep.total_earnings:.4f} SOL
└─ 狀態：{'✅ 值得信賴' if rep.reputation_score >= 60 else '⚠️ 新用戶/風險較高'}
"""

# 全域實例
reputation_system = ReputationSystem()
