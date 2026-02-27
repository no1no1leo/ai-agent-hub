"""
信譽系統 (Reputation System)
防止低價低質，確保任務完成品質
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
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
    join_date: datetime = field(default_factory=datetime.utcnow)
    
    # 最近 10 次評價
    recent_ratings: List[float] = field(default_factory=lambda: [4.0] * 10)
    
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
        公式：成功率 * 50 + 平均評分 * 10 + 經驗加成
        """
        success_component = self.success_rate * 50
        rating_component = (self.avg_rating / 5.0) * 40
        
        # 經驗加成：每完成 10 個任務 +1 分，最多 10 分
        exp_component = min(10, self.completed_tasks // 10)
        
        return min(100, success_component + rating_component + exp_component)
    
    def add_task_result(self, completed: bool, rating: Optional[float] = None):
        """更新任務結果"""
        self.total_tasks += 1
        if completed:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1
        
        if rating is not None:
            # 更新最近評價
            self.recent_ratings.append(rating)
            if len(self.recent_ratings) > 10:
                self.recent_ratings.pop(0)
            
            # 更新平均評分
            self.avg_rating = sum(self.recent_ratings) / len(self.recent_ratings)
        
        logger.info(f"📊 {self.agent_id} 信譽更新：總任務={self.total_tasks}, "
                    f"成功率={self.success_rate:.1%}, 評分={self.avg_rating:.1f}")

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
    
    def update_reputation(self, agent_id: str, completed: bool, rating: Optional[float] = None):
        """更新 Agent 信譽"""
        rep = self.get_or_create(agent_id)
        rep.add_task_result(completed, rating)
    
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
