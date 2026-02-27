"""
AI Agent Marketplace Web API
使用 FastAPI 提供 RESTful 介面
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
import uvicorn

# 引入市場模組
from .hub_market import HubMarket, TaskStatus
from .reputation import ReputationSystem, reputation_system
from .solana_escrow import solana_escrow

# 初始化 FastAPI
app = FastAPI(
    title="AI Agent Marketplace",
    description="去中心化 AI 任務競標平台",
    version="1.0.0"
)

# 全域市場實例
market = HubMarket()

# === 資料模型 ===
class CreateTaskRequest(BaseModel):
    description: str
    input_data: str
    max_budget: float
    expected_tokens: int
    requester_id: Optional[str] = "anonymous"

class SubmitBidRequest(BaseModel):
    task_id: str
    bidder_id: str
    bid_price: float
    model_name: str
    message: Optional[str] = ""

class TaskResponse(BaseModel):
    task_id: str
    description: str
    status: str
    max_budget: float
    assigned_to: Optional[str]

# === API 端點 ===
@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Agent Marketplace",
        "docs": "/docs",
        "community": {
            "threads": "https://www.threads.com/@engineer.rp/post/DVPtjD4EiY6?xmt=AQF0z8TF9-bg2tRhNIXogI6SPFsW4ut59uuG1HD_jdkW6XbpeZNL5WThwqCWMG0IWHBOPtu4&slof=1"
        },
        "stats": market.get_market_stats()
    }

@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """建立新任務"""
    try:
        task = market.create_task(
            description=request.description,
            input_data=request.input_data,
            max_budget=request.max_budget,
            expected_tokens=request.expected_tokens,
            requester_id=request.requester_id
        )
        return TaskResponse(
            task_id=task.task_id,
            description=task.description,
            status=task.status.value,
            max_budget=task.max_budget,
            assigned_to=task.assigned_to
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """列出所有任務"""
    tasks = []
    for task in market.tasks.values():
        if status is None or task.status.value == status:
            tasks.append({
                "task_id": task.task_id,
                "description": task.description,
                "status": task.status.value,
                "max_budget": task.max_budget,
                "bids_count": len(market.bids.get(task.task_id, []))
            })
    return {"tasks": tasks}

@app.post("/tasks/{task_id}/bids")
async def submit_bid(task_id: str, request: SubmitBidRequest):
    """提交投標"""
    try:
        bid = market.submit_bid(
            task_id=task_id,
            bidder_id=request.bidder_id,
            bid_price=request.bid_price,
            estimated_tokens=0,  # 簡化
            model_name=request.model_name,
            message=request.message
        )
        return {
            "success": True,
            "bid_id": bid.bid_id,
            "message": f"投標成功：{bid.bid_price} SOL"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks/{task_id}/bids")
async def get_bids(task_id: str):
    """獲取任務的所有投標"""
    bids = market.bids.get(task_id, [])
    return {
        "task_id": task_id,
        "bids": [
            {
                "bid_id": b.bid_id,
                "bidder_id": b.bidder_id,
                "price": b.bid_price,
                "model": b.model_name
            }
            for b in bids
        ]
    }

@app.post("/tasks/{task_id}/select")
async def select_winner(task_id: str):
    """選擇最佳投標"""
    winner = market.select_winner(task_id)
    if winner:
        # 建立 Solana 託管
        escrow_id = solana_escrow.create_escrow(
            task_id=task_id,
            buyer_id=market.tasks[task_id].requester_id,
            seller_id=winner.bidder_id,
            amount=winner.bid_price
        )
        return {
            "success": True,
            "winner": winner.bidder_id,
            "price": winner.bid_price,
            "escrow_id": escrow_id
        }
    else:
        raise HTTPException(status_code=404, detail="No valid bids found")

@app.get("/reputation/{agent_id}")
async def get_reputation(agent_id: str):
    """獲取 Agent 信譽"""
    rep = reputation_system.get_or_create(agent_id)
    return {
        "agent_id": agent_id,
        "reputation_score": rep.reputation_score,
        "success_rate": rep.success_rate,
        "avg_rating": rep.avg_rating,
        "total_tasks": rep.total_tasks
    }

@app.get("/stats")
async def get_stats():
    """獲取市場統計"""
    return {
        "market": market.get_market_stats(),
        "solana": solana_escrow.get_market_stats()
    }

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """啟動伺服器"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
