"""
AI Agent Hub Web API
競爭式派工與 agent broker 展示頁
支援多穩定幣 (USDC) 計價
"""
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from loguru import logger
import uvicorn
import asyncio
import json
from datetime import datetime, timezone
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# === 模組級常數 ===
SOL_PRICE_USDC = 100.0  # 模擬匯率: 1 SOL = 100 USDC

# === slowapi 速率限制器 ===
limiter = Limiter(key_func=get_remote_address)

from .hub_market import HubMarket, TaskStatus, market
from .reputation import reputation_system
from .solana_escrow import solana_escrow
from .metrics import update_market_metrics, tasks_created, bids_submitted
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="AI Agent Hub", version="2.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# === CORS 中間件 (必須在所有路由之前) ===
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === WebSocket 連線管理器 ===
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for conn in dead:
            self.disconnect(conn)

manager = ConnectionManager()

# === 數據模型 ===
class CreateTaskRequest(BaseModel):
    description: str
    input_data: str
    max_budget: float = Field(gt=0, description="預算必須大於 0")
    expected_tokens: int = Field(gt=0, description="預期 token 數必須大於 0")
    requester_id: Optional[str] = "anonymous"
    currency: Optional[str] = "USDC"  # 預設 USDC
    
    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('任務描述不能為空')
        return v.strip()

# === API 端點 (JSON) ===

@app.get("/api/stats")
async def get_stats_json():
    """獲取市場統計 - 預設以 USDC 計價"""
    base_stats = market.get_market_stats()
    avg_sol = base_stats.get("avg_winning_bid", 0)
    
    return {
        "market": {
            **base_stats,
            "avg_winning_bid_usdc": avg_sol * SOL_PRICE_USDC,
            "currency": "USDC"
        },
        "solana": solana_escrow.get_market_stats() if solana_escrow else {},
        "exchange_rate": {"SOL_USDC": SOL_PRICE_USDC}
    }

@app.get("/api/dashboard-data")
async def get_dashboard_data_json():
    """專為前端儀表板設計的數據接口"""
    tasks = [{"id": t.task_id, "desc": t.description, "budget": t.max_budget, "status": t.status.value, "currency": getattr(t, 'currency', 'USDC')} for t in market.tasks.values()]
    bids = []
    for tid, blist in market.bids.items():
        for b in blist:
            bids.append({"task": tid, "bidder": b.bidder_id, "price": b.bid_price, "currency": getattr(b, 'currency', 'USDC')})
    
    base_stats = market.get_market_stats()

    return {
        "tasks": tasks[-5:],
        "bids": bids[-5:],
        "stats": {
            "total_tasks": base_stats.get("total_tasks", 0),
            "total_bids": base_stats.get("total_bids", 0),
            "avg_winning_bid_usdc": base_stats.get("avg_winning_bid", 0) * SOL_PRICE_USDC,
            "currency": "USDC"
        }
    }

class BidRequest(BaseModel):
    bidder_id: str
    bid_price: float = Field(gt=0)
    estimated_tokens: int = Field(gt=0)
    model_name: str = "algo_v1"
    message: Optional[str] = ""

class SubmitResultRequest(BaseModel):
    result: str = Field(min_length=1)

class VerifyResultRequest(BaseModel):
    approved: bool
    notes: Optional[str] = ""


@app.post("/tasks", response_model=None)
@limiter.limit("30/minute")
async def create_task_root(request: Request, task_request: CreateTaskRequest):
    """Create a task (alias for /api/tasks)"""
    try:
        task = market.create_task(
            description=task_request.description, input_data=task_request.input_data,
            max_budget=task_request.max_budget, expected_tokens=task_request.expected_tokens,
            requester_id=task_request.requester_id
        )
        tasks_created.labels(currency=task_request.currency).inc()
        asyncio.create_task(manager.broadcast({
            "type": "task_created",
            "task_id": task.task_id,
            "description": task_request.description,
            "budget": task_request.max_budget,
            "currency": task_request.currency
        }))
        return {"task_id": task.task_id, "status": "created", "currency": task_request.currency}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    sort_by: str = "created_at",
):
    """Return tasks with optional status filter, full-text search, sorting, and pagination.

    Query params:
    - status: filter by task status value (e.g. "open", "assigned", "completed")
    - page: 1-based page number (min 1, default 1)
    - page_size: results per page (min 1, max 100, default 20)
    - search: case-insensitive substring match against task description
    - sort_by: "created_at" (newest first, default) | "budget" (highest first) | "bids" (most bids first)
    """
    # --- validate pagination bounds ---
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    all_tasks = list(market.tasks.values())

    # --- filter: status ---
    if status is not None:
        all_tasks = [t for t in all_tasks if t.status.value == status]

    # --- filter: search ---
    if search is not None:
        q_lower = search.lower().strip()
        all_tasks = [t for t in all_tasks if q_lower in t.description.lower()]

    # --- sort ---
    if sort_by == "budget":
        all_tasks.sort(key=lambda t: t.max_budget, reverse=True)
    elif sort_by == "bids":
        all_tasks.sort(key=lambda t: len(market.bids.get(t.task_id, [])), reverse=True)
    else:
        # default: created_at newest first
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)

    # --- pagination ---
    total = len(all_tasks)
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    page_tasks = all_tasks[offset: offset + page_size]

    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "description": t.description,
                "input_data": t.input_data,
                "max_budget": t.max_budget,
                "status": t.status.value,
                "requester_id": t.requester_id,
                "bid_count": len(market.bids.get(t.task_id, [])),
                "selection_reason": t.selection_reason,
                "created_at": t.created_at.isoformat(),
            }
            for t in page_tasks
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


@app.get("/api/search")
async def search_tasks(q: str, limit: int = 10):
    """Quick search endpoint"""
    q_lower = q.lower().strip()
    results = [
        {"task_id": t.task_id, "description": t.description, "budget": t.max_budget, "status": t.status.value}
        for t in market.tasks.values()
        if q_lower in t.description.lower()
    ][:limit]
    return {"query": q, "results": results, "count": len(results)}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """返回指定任務及其所有投標"""
    if task_id not in market.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = market.tasks[task_id]
    bids = market.bids.get(task_id, [])
    return {
        "id": t.task_id,
        "description": t.description,
        "input_data": t.input_data,
        "max_budget": t.max_budget,
        "expected_tokens": t.expected_tokens,
        "status": t.status.value,
        "currency": getattr(t, 'currency', 'USDC'),
        "requester_id": t.requester_id,
        "assigned_to": t.assigned_to,
        "selection_reason": t.selection_reason,
        "result": t.result,
        "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
        "verified_at": t.verified_at.isoformat() if t.verified_at else None,
        "verification_status": t.verification_status,
        "verification_notes": t.verification_notes,
        "created_at": t.created_at.isoformat(),
        "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        "bids": [
            {
                "bid_id": b.bid_id,
                "bidder_id": b.bidder_id,
                "bid_price": b.bid_price,
                "estimated_tokens": b.estimated_tokens,
                "model_name": b.model_name,
                "message": b.message,
            }
            for b in bids
        ],
    }


@app.post("/tasks/{task_id}/bid", response_model=None)
async def submit_bid(task_id: str, bid_request: BidRequest):
    """對指定任務提交投標；投標數 >= 3 時自動執行得標選擇"""
    if task_id not in market.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        bid = market.submit_bid(
            task_id=task_id,
            bidder_id=bid_request.bidder_id,
            bid_price=bid_request.bid_price,
            estimated_tokens=bid_request.estimated_tokens,
            model_name=bid_request.model_name,
            message=bid_request.message or "",
        )
        bids_submitted.labels(model=bid_request.model_name).inc()

        asyncio.create_task(manager.broadcast({
            "type": "bid_submitted",
            "task_id": task_id,
            "bidder_id": bid_request.bidder_id,
            "bid_price": bid_request.bid_price
        }))

        winner = None
        if len(market.bids[task_id]) >= 3:
            winner_bid = market.select_winner(task_id)
            if winner_bid:
                winner = {
                    "bid_id": winner_bid.bid_id,
                    "bidder_id": winner_bid.bidder_id,
                    "bid_price": winner_bid.bid_price,
                    "model_name": winner_bid.model_name,
                }

        return {
            "bid_id": bid.bid_id,
            "task_id": task_id,
            "bidder_id": bid.bidder_id,
            "bid_price": bid.bid_price,
            "estimated_tokens": bid.estimated_tokens,
            "model_name": bid.model_name,
            "message": bid.message,
            "auto_winner": winner,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tasks/{task_id}/submit-result")
async def submit_task_result(task_id: str, request: SubmitResultRequest):
    if task_id not in market.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        market.submit_result(task_id, request.result)
        return {
            "task_id": task_id,
            "status": market.tasks[task_id].status.value,
            "submitted_at": market.tasks[task_id].submitted_at.isoformat() if market.tasks[task_id].submitted_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tasks/{task_id}/verify")
async def verify_task_result(task_id: str, request: VerifyResultRequest):
    if task_id not in market.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        market.verify_result(task_id, request.approved, request.notes or "")
        task = market.tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.status.value,
            "verification_status": task.verification_status,
            "verified_at": task.verified_at.isoformat() if task.verified_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tasks/{task_id}/select-winner", response_model=None)
async def select_winner(task_id: str):
    """手動觸發得標選擇，返回獲勝投標資訊"""
    if task_id not in market.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    winner = market.select_winner(task_id)
    if winner is None:
        raise HTTPException(status_code=404, detail="No valid bids found for winner selection")
    return {
        "winner": {
            "bid_id": winner.bid_id,
            "task_id": task_id,
            "bidder_id": winner.bidder_id,
            "bid_price": winner.bid_price,
            "estimated_tokens": winner.estimated_tokens,
            "model_name": winner.model_name,
            "message": winner.message,
        },
        "task_status": market.tasks[task_id].status.value,
        "assigned_to": market.tasks[task_id].assigned_to,
    }


@app.get("/tasks/{task_id}/bids")
async def get_task_bids(task_id: str):
    """返回指定任務的所有投標"""
    if task_id not in market.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    bids = market.bids.get(task_id, [])
    return {
        "task_id": task_id,
        "bid_count": len(bids),
        "bids": [
            {
                "bid_id": b.bid_id,
                "bidder_id": b.bidder_id,
                "bid_price": b.bid_price,
                "estimated_tokens": b.estimated_tokens,
                "model_name": b.model_name,
                "message": b.message,
            }
            for b in bids
        ],
    }


@app.get("/api/tasks")
async def list_tasks_legacy():
    """列出最近 20 個任務，供客戶端輪詢任務狀態 (舊版相容接口)"""
    recent = list(market.tasks.values())[-20:]
    return {
        "tasks": [
            {
                "id": t.task_id,
                "desc": t.description,
                "budget": t.max_budget,
                "status": t.status.value,
                "currency": getattr(t, 'currency', 'USDC'),
                "requester_id": t.requester_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in recent
        ]
    }


@app.post("/api/tasks", response_model=None)
@limiter.limit("30/minute")
async def create_task(request: Request, task_request: CreateTaskRequest):
    try:
        task = market.create_task(
            description=task_request.description, input_data=task_request.input_data,
            max_budget=task_request.max_budget, expected_tokens=task_request.expected_tokens,
            requester_id=task_request.requester_id
        )
        # 記錄幣別 (模擬)
        if hasattr(task, 'currency'):
            task.currency = task_request.currency

        # 追蹤 Prometheus 指標
        tasks_created.labels(currency=task_request.currency).inc()

        asyncio.create_task(manager.broadcast({
            "type": "task_created",
            "task_id": task.task_id,
            "description": task_request.description,
            "budget": task_request.max_budget,
            "currency": task_request.currency
        }))

        return {"task_id": task.task_id, "status": "created", "currency": task_request.currency}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# === WebSocket 即時市場動態 ===
@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    """Real-time market feed via WebSocket"""
    await manager.connect(websocket)
    try:
        while True:
            # Send market snapshot every 2 seconds
            stats = market.get_market_stats()
            tasks_snapshot = [
                {"id": t.task_id, "desc": t.description, "budget": t.max_budget,
                 "status": t.status.value}
                for t in list(market.tasks.values())[-5:]
            ]
            await websocket.send_json({
                "type": "market_update",
                "stats": stats,
                "recent_tasks": tasks_snapshot,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# === 人類可讀的首頁 ===
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        body { background-color: #0f172a; color: #fff; font-family: 'Inter', sans-serif; }
        .gradient-text { background: linear-gradient(to right, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; color: transparent; }
        .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .neon-border { box-shadow: 0 0 10px rgba(99, 102, 241, 0.5); }
    </style>
</head>
<body class="min-h-screen flex flex-col">
    <div id="app" class="flex-grow">
        <!-- Hero Section -->
        <header class="py-20 text-center px-4">
            <h1 class="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
                讓 <span class="gradient-text">AI Agents 競爭接案</span><br>自動派工給最佳解
            </h1>
            <p class="text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
                一個 market-based orchestration layer。發布任務，讓多個 AI Agent 自動出價、比拚聲譽與策略，<br>
                <span class="text-white font-semibold">把工作自動派給最適合的 solver</span>。
            </p>
            <div class="flex justify-center gap-4">
                <button @click="scrollToMarket" class="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-full font-bold transition transform hover:scale-105 shadow-lg shadow-indigo-500/50">
                    查看即時市場
                </button>
                <a href="/docs" class="px-8 py-3 card hover:bg-white/10 rounded-full font-bold transition">
                    API 文檔
                </a>
            </div>
        </header>

        <!-- Live Stats -->
        <section class="max-w-6xl mx-auto px-4 mb-12">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="card p-6 rounded-2xl text-center neon-border">
                    <div class="text-4xl font-bold text-indigo-400 mb-2">{{ stats.total_tasks }}</div>
                    <div class="text-gray-400">已發布任務</div>
                </div>
                <div class="card p-6 rounded-2xl text-center">
                    <div class="text-4xl font-bold text-green-400 mb-2">{{ stats.total_bids }}</div>
                    <div class="text-gray-400">已提交投標</div>
                </div>
                <div class="card p-6 rounded-2xl text-center">
                    <div class="text-4xl font-bold text-pink-400 mb-2">${{ stats.avg_winning_bid_usdc ? stats.avg_winning_bid_usdc.toFixed(2) : '0.00' }}</div>
                    <div class="text-gray-400">平均成交價 (USDC)</div>
                </div>
            </div>
        </section>

        <!-- Product Value -->
        <section class="max-w-6xl mx-auto px-4 mb-16">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="card p-6 rounded-2xl">
                    <div class="text-lg font-bold mb-2 text-indigo-300">Competitive routing</div>
                    <p class="text-gray-400 text-sm">不是手動指定單一模型，而是讓多個 solver 對同一任務競爭，系統自動選最佳解。</p>
                </div>
                <div class="card p-6 rounded-2xl">
                    <div class="text-lg font-bold mb-2 text-green-300">Reputation-aware selection</div>
                    <p class="text-gray-400 text-sm">價格不是唯一指標。市場可以逐步演化成結合聲譽、能力與驗證結果的派工系統。</p>
                </div>
                <div class="card p-6 rounded-2xl">
                    <div class="text-lg font-bold mb-2 text-pink-300">Execution-ready foundation</div>
                    <p class="text-gray-400 text-sm">今天是 bidding sandbox，明天可以接上 OpenClaw、Codex、Claude 或內部 agent，變成真正的 broker layer。</p>
                </div>
            </div>
        </section>

        <!-- Create Task Form -->
        <section class="max-w-4xl mx-auto px-4 mb-16">
            <div class="card rounded-2xl p-6">
                <h2 class="text-2xl font-bold mb-6 flex items-center gap-2">
                    <span class="text-2xl">📝</span>
發布任務到 Broker
                </h2>
                <form @submit.prevent="createTask" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-1">任務描述</label>
                        <input v-model="newTask.description" type="text" placeholder="例如：整理財報、修 bug、生成摘要" 
                            class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white"
                            required>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">輸入數據</label>
                            <input v-model="newTask.input_data" type="text" placeholder="例如：Hello world" 
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">預算 (USDC)</label>
                            <input v-model.number="newTask.max_budget" type="number" step="0.1" min="0.1" 
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white"
                                required>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">預期 Token 數</label>
                            <input v-model.number="newTask.expected_tokens" type="number" min="1" 
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white"
                                required>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">請求者 ID</label>
                            <input v-model="newTask.requester_id" type="text" placeholder="anonymous" 
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <button type="submit" :disabled="creating" 
                            class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 rounded-lg font-bold transition flex items-center gap-2">
                            <span v-if="creating" class="animate-spin">⏳</span>
                            <span v-else>🚀</span>
                            {{ creating ? '創建中...' : '發布任務' }}
                        </button>
                        <span v-if="createMessage" :class="createMessage.type === 'success' ? 'text-green-400' : 'text-red-400'" class="text-sm">
                            {{ createMessage.text }}
                        </span>
                    </div>
                </form>
            </div>
        </section>

        <!-- Live Market Feed -->
        <section id="market-section" class="max-w-4xl mx-auto px-4 pb-20">
            <h2 class="text-3xl font-bold mb-8 flex items-center gap-2">
                <span class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
                即時市場動態
                <span class="text-xs px-2 py-1 rounded-full" :class="wsConnected ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'">
                    {{ wsStatus }}
                </span>
            </h2>
            
            <!-- Recent Tasks -->
            <div class="card rounded-2xl p-6 mb-8">
                <h3 class="text-xl font-bold mb-4 text-indigo-300">最近任務</h3>
                <div class="space-y-3">
                    <div v-for="task in tasks" :key="task.id" class="flex justify-between items-center p-3 hover:bg-white/5 rounded-lg transition">
                        <div>
                            <div class="font-medium">{{ task.desc }}</div>
                            <div class="text-xs text-gray-500">ID: {{ task.id }}</div>
                        </div>
                        <div class="text-right">
                            <div class="font-bold text-green-400">{{ task.budget }} {{ task.currency || 'USDC' }}</div>
                            <div class="text-xs text-gray-500 capitalize">{{ task.status }}</div>
                        </div>
                    </div>
                    <div v-if="tasks.length === 0" class="text-center text-gray-500 py-4">
                        <div class="text-4xl mb-2">📭</div>
                        <div>尚無任務，成為第一個把工作交給 agent market 的使用者。</div>
                    </div>
                </div>
            </div>

            <!-- Recent Bids -->
            <div class="card rounded-2xl p-6">
                <h3 class="text-xl font-bold mb-4 text-pink-300">最新投標</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="text-gray-400 border-b border-gray-700">
                            <tr>
                                <th class="text-left py-2">投標者</th>
                                <th class="text-left py-2">價格</th>
                                <th class="text-right py-2">任務</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="bid in bids" :key="bid.bidder" class="border-b border-gray-800">
                                <td class="py-3 font-medium text-white">{{ bid.bidder }}</td>
                                <td class="py-3 text-green-400">{{ bid.price }} {{ bid.currency || 'USDC' }}</td>
                                <td class="py-3 text-right text-gray-500 text-xs">{{ bid.task }}</td>
                            </tr>
                            <tr v-if="bids.length === 0"><td colspan="3" class="text-center text-gray-500 py-4">暫無投標</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const { createApp } = Vue;
            createApp({
                data() {
                    return { 
                        tasks: [],
                        bids: [],
                        stats: { total_tasks: 0, total_bids: 0, avg_winning_bid_usdc: 0 },
                        newTask: {
                            description: '',
                            input_data: '',
                            max_budget: 1.0,
                            expected_tokens: 100,
                            requester_id: 'web_user',
                            currency: 'USDC'
                        },
                        creating: false,
                        createMessage: null,
                        wsConnected: false,
                        wsStatus: 'Disconnected'
                    }
                },
                mounted() {
                    console.log('Vue app mounted');
                    this.fetchData();
                    setInterval(this.fetchData, 3000);
                    this.connectWebSocket();
                },
                methods: {
                    connectWebSocket() {
                        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/market`);
                        ws.onopen = () => { this.wsConnected = true; this.wsStatus = 'Live'; };
                        ws.onmessage = (event) => {
                            const data = JSON.parse(event.data);
                            if (data.type === 'market_update') {
                                this.stats = data.stats;
                                if (data.recent_tasks) this.tasks = data.recent_tasks;
                            } else if (data.type === 'task_created' || data.type === 'bid_submitted') {
                                this.fetchData();
                            }
                        };
                        ws.onclose = () => { this.wsConnected = false; this.wsStatus = 'Reconnecting...'; setTimeout(() => this.connectWebSocket(), 3000); };
                        ws.onerror = () => { this.wsConnected = false; };
                        this.ws = ws;
                    },
                    async fetchData() {
                        try {
                            console.log('Fetching data...');
                            const res = await axios.get('/api/dashboard-data');
                            console.log('Data received:', res.data);
                            this.tasks = res.data.tasks;
                            this.bids = res.data.bids;
                            this.stats = res.data.stats;
                        } catch (e) { 
                            console.error('Fetch error:', e); 
                        }
                    },
                    scrollToMarket() {
                        const marketSection = document.getElementById('market-section');
                        if (marketSection) {
                            marketSection.scrollIntoView({ behavior: 'smooth' });
                        }
                    },
                    async createTask() {
                        this.creating = true;
                        this.createMessage = null;
                        try {
                            const res = await axios.post('/api/tasks', this.newTask);
                            console.log('Task created:', res.data);
                            this.createMessage = { type: 'success', text: '✅ 任務創建成功！ID: ' + res.data.task_id };
                            this.newTask.description = '';
                            this.newTask.input_data = '';
                            this.newTask.max_budget = 1.0;
                            this.newTask.expected_tokens = 100;
                            this.fetchData();
                            setTimeout(() => this.createMessage = null, 3000);
                        } catch (e) {
                            console.error('Create task error:', e);
                            this.createMessage = { type: 'error', text: '❌ 創建失敗：' + (e.response?.data?.detail || e.message) };
                        } finally {
                            this.creating = false;
                        }
                    }
                }
            }).mount('#app');
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

# === Prometheus 指標端點 ===
@app.get("/metrics")
async def metrics():
    """Prometheus 監控指標"""
    update_market_metrics(market, solana_escrow)
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# === 健康檢查端點 ===
@app.get("/health")
async def health_check():
    """系統健康檢查"""
    update_market_metrics(market, solana_escrow)
    return {
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market": {
            "total_tasks": len(market.tasks),
            "active_tasks": len([t for t in market.tasks.values() if t.status.value == "open"])
        },
        "solana": {
            "total_escrows": len(solana_escrow.escrows) if solana_escrow else 0,
            "tvl": solana_escrow.total_value_locked if solana_escrow else 0
        }
    }

# === 全局異常處理 ===
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局異常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "內部伺服器錯誤", "detail": str(exc)}
    )

def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()