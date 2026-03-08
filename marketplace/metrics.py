"""
Prometheus 監控指標
用於追蹤市場效能和健康狀態
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time

# 市場指標
tasks_created = Counter(
    'market_tasks_created_total',
    'Total number of tasks created',
    ['currency']
)

tasks_completed = Counter(
    'market_tasks_completed_total',
    'Total number of tasks completed',
    ['status']
)

bids_submitted = Counter(
    'market_bids_submitted_total',
    'Total number of bids submitted'
)

active_tasks = Gauge(
    'market_active_tasks',
    'Number of currently active tasks'
)

avg_bid_price = Gauge(
    'market_avg_bid_price',
    'Average bid price in SOL'
)

# 效能指標
bid_processing_duration = Histogram(
    'market_bid_processing_duration_seconds',
    'Time spent processing bids',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

task_creation_duration = Histogram(
    'market_task_creation_duration_seconds',
    'Time spent creating tasks',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Solana 指標
escrows_created = Counter(
    'solana_escrows_created_total',
    'Total number of escrows created'
)

escrows_completed = Counter(
    'solana_escrows_completed_total',
    'Total number of escrows completed'
)

total_value_locked = Gauge(
    'solana_total_value_locked_sol',
    'Total value locked in escrows (SOL)'
)

# 系統資訊
app_info = Info(
    'market_app',
    'Application information'
)

def track_timing(metric):
    """追蹤函數執行時間的裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                metric.observe(time.time() - start)
        return wrapper
    return decorator

def update_market_metrics(market, solana_escrow):
    """更新市場指標"""
    from .hub_market import TaskStatus
    
    # 更新活躍任務數
    active_count = len([t for t in market.tasks.values() if t.status == TaskStatus.OPEN])
    active_tasks.set(active_count)
    
    # 更新平均投標價格
    winning_bids = [
        b.bid_price 
        for t in market.tasks.values() 
        if t.assigned_to 
        for b in market.bids.get(t.task_id, []) 
        if b.bidder_id == t.assigned_to
    ]
    if winning_bids:
        avg_bid_price.set(sum(winning_bids) / len(winning_bids))
    
    # 更新 TVL
    if solana_escrow:
        total_value_locked.set(solana_escrow.total_value_locked)

# 初始化應用資訊
app_info.info({'version': '2.1.0', 'environment': 'production'})
