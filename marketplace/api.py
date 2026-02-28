"""
AI Agent Marketplace Web API
純文字/通用版本，無外部 LLM 依賴
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from loguru import logger
import uvicorn
from datetime import datetime

# 引入市場模組
from .hub_market import HubMarket, TaskStatus, market
from .reputation import ReputationSystem, reputation_system
from .solana_escrow import solana_escrow

# 初始化 FastAPI
app = FastAPI(
    title="AI Agent Marketplace",
    description="去中心化 AI 任務競標平台 (純文字/通用版)",
    version="1.1.0"
)

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

# === API 端點 (JSON) ===
@app.get("/api/stats")
async def get_stats_json():
    """獲取市場統計 (純 JSON API)"""
    return {
        "message": "AI Agent Marketplace Stats",
        "market": market.get_market_stats(),
        "solana": solana_escrow.get_market_stats() if solana_escrow else {}
    }

@app.get("/api/dashboard-data")
async def get_dashboard_data_json():
    """專為前端儀表板設計的數據接口 (JSON)"""
    all_tasks = []
    for task in market.tasks.values():
        all_tasks.append({
            "id": task.task_id,
            "description": task.description,
            "budget": task.max_budget,
            "status": task.status.value,
            "assigned_to": task.assigned_to or "等待投標",
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    all_bids = []
    for task_id, bids in market.bids.items():
        for bid in bids:
            all_bids.append({
                "task_id": task_id,
                "bidder": bid.bidder_id,
                "price": bid.bid_price,
                "model": bid.model_name,
                "status": "active"
            })

    escrows = []
    if solana_escrow:
        for eid, escrow in solana_escrow.escrows.items():
            escrows.append({
                "id": eid,
                "task": escrow.task_id,
                "buyer": escrow.buyer_id,
                "seller": escrow.seller_id,
                "amount": escrow.amount,
                "status": escrow.status.value
            })

    return {
        "tasks": all_tasks,
        "bids": all_bids,
        "escrows": escrows,
        "stats": {
            "total_tasks": len(all_tasks),
            "total_bids": len(all_bids),
            "total_escrows": len(escrows)
        }
    }

# === 業務邏輯端點 ===
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
            estimated_tokens=0,
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
        escrow_id = "simulated_escrow"
        if solana_escrow:
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

# === 人類可讀的首頁 (HTML) ===
@app.get("/", response_class=HTMLResponse)
async def dashboard_html(request: Request):
    """人類可讀的儀表板首頁 (強制返回 HTML)"""
    # 這裡直接返回一個簡單的 HTML 字符串，避免依賴外部文件
    # 為了節省 Token，此處精簡了 HTML 內容，但保留了核心功能
    html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Hub - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
</head>
<body class="bg-gray-100 text-gray-800">
    <div id="app" class="min-h-screen">
        <nav class="bg-white shadow-md">
            <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
                <h1 class="text-2xl font-bold text-indigo-600">🤖 AI Agent Hub</h1>
                <div class="space-x-4">
                    <a href="/docs" class="text-gray-600 hover:text-indigo-600">API Docs</a>
                    <a href="https://github.com/no1no1leo/ai-agent-hub" class="text-gray-600 hover:text-indigo-600">GitHub</a>
                </div>
            </div>
        </nav>
        <main class="max-w-7xl mx-auto px-4 py-8">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-white p-6 rounded-lg shadow">
                    <h3 class="text-gray-500 text-sm">總任務數</h3>
                    <p class="text-3xl font-bold">{{ stats.total_tasks }}</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow">
                    <h3 class="text-gray-500 text-sm">總投標數</h3>
                    <p class="text-3xl font-bold">{{ stats.total_bids }}</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow">
                    <h3 class="text-gray-500 text-sm">鏈上託管</h3>
                    <p class="text-3xl font-bold">{{ stats.total_escrows }}</p>
                </div>
            </div>
            <div class="bg-white rounded-lg shadow mb-8">
                <div class="p-4 border-b"><h3 class="font-bold">最近任務</h3></div>
                <ul class="divide-y">
                    <li v-for="task in tasks" :key="task.id" class="p-4 hover:bg-gray-50 flex justify-between">
                        <div>
                            <p class="font-medium text-indigo-600">{{ task.description }}</p>
                            <p class="text-xs text-gray-500">{{ task.created_at }}</p>
                        </div>
                        <div class="text-right">
                            <span class="px-2 py-1 text-xs rounded bg-green-100 text-green-800">{{ task.status }}</span>
                            <p class="font-bold mt-1">{{ task.budget }} SOL</p>
                        </div>
                    </li>
                    <li v-if="tasks.length === 0" class="p-4 text-center text-gray-500">暫無任務</li>
                </ul>
            </div>
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b"><h3 class="font-bold">活躍投標</h3></div>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="p-3 text-left">任務 ID</th>
                                <th class="p-3 text-left">投標者</th>
                                <th class="p-3 text-left">模型</th>
                                <th class="p-3 text-left">價格 (SOL)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="bid in bids" :key="bid.bidder" class="border-t">
                                <td class="p-3">{{ bid.task_id }}</td>
                                <td class="p-3 font-medium">{{ bid.bidder }}</td>
                                <td class="p-3">{{ bid.model }}</td>
                                <td class="p-3">{{ bid.price }}</td>
                            </tr>
                            <tr v-if="bids.length === 0"><td colspan="4" class="p-4 text-center text-gray-500">暫無投標</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>
    <script>
        const { createApp } = Vue;
        createApp({
            data() {
                return { tasks: [], bids: [], escrows: [], stats: { total_tasks: 0, total_bids: 0, total_escrows: 0 } }
            },
            async mounted() { await this.fetchData(); setInterval(this.fetchData, 3000); },
            methods: {
                async fetchData() {
                    try {
                        const res = await axios.get('/api/dashboard-data');
                        this.tasks = res.data.tasks;
                        this.bids = res.data.bids;
                        this.escrows = res.data.escrows;
                        this.stats = res.data.stats;
                    } catch (e) { console.error(e); }
                }
            }
        }).mount('#app');
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

# === 啟動器 ===
def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()