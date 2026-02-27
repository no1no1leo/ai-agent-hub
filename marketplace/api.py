"""
AI Agent Marketplace Web API
使用 FastAPI 提供 RESTful 介面
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from loguru import logger
import uvicorn
from datetime import datetime

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
    # 多模態字段
    image_url: Optional[str] = None
    file_path: Optional[str] = None

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
    """建立新任務 (支持多模態)"""
    try:
        # 直接操作底層對象以設置多模態字段
        from marketplace.hub_market import Task, ServiceType
        import uuid
        from datetime import datetime
        
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            requester_id=request.requester_id,
            description=request.description,
            input_data=request.input_data,
            max_budget=request.max_budget,
            expected_tokens=request.expected_tokens,
            image_url=request.image_url,
            file_path=request.file_path,
            status=market.TaskStatus.OPEN
        )
        market.tasks[task.task_id] = task
        market.bids[task.task_id] = []
        logger.info(f"📢 [Market] 新任務發布：{task.task_id} (多模態: {bool(request.image_url)})")
        
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
    """獲取市場統計 (JSON API)"""
    return {
        "market": market.get_market_stats(),
        "solana": solana_escrow.get_market_stats()
    }

@app.get("/dashboard-data", response_model=None)
async def get_dashboard_data():
    """
    專為前端儀表板設計的數據接口
    返回人類可讀的市場概覽與最近交易
    """
    # 獲取所有任務
    all_tasks = []
    for task in market.tasks.values():
        all_tasks.append({
            "id": task.task_id,
            "description": task.description,
            "budget": task.max_budget,
            "status": task.status.value,
            "assigned_to": task.assigned_to or "等待投標",
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "image_url": getattr(task, 'image_url', None),  # 新增圖片 URL
            "has_media": bool(getattr(task, 'image_url', None))  # 標記是否有圖片
        })
    
    # 獲取所有投標
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

    # 獲取 Solana 託管狀態
    escrows = []
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

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    人類可讀的儀表板首頁
    """
    # 使用簡單的內聯 HTML/JS 模板，避免依賴外部文件
    html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Trading Hub - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <style>
        .fade-enter-active, .fade-leave-active { transition: opacity 0.5s; }
        .fade-enter-from, .fade-leave-to { opacity: 0; }
        body { background-color: #f3f4f6; }
    </style>
</head>
<body class="text-gray-800">
    <div id="app" class="min-h-screen">
        <!-- Navbar -->
        <nav class="bg-white shadow-md">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between h-16">
                    <div class="flex items-center">
                        <span class="text-2xl font-bold text-indigo-600">🤖 AI Agent Hub</span>
                    </div>
                    <div class="flex items-center space-x-4">
                        <a href="/docs" class="text-gray-600 hover:text-indigo-600">API Docs</a>
                        <a href="https://github.com/no1no1leo/ai-agent-hub" class="text-gray-600 hover:text-indigo-600">GitHub</a>
                        <span class="text-sm text-gray-500">最後更新: {{ lastUpdate }}</span>
                    </div>
                </div>
            </div>
        </nav>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <!-- Stats Overview -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0 bg-indigo-500 rounded-md p-3">
                                <span class="text-white text-xl">📝</span>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">總任務數</dt>
                                    <dd class="text-2xl font-bold text-gray-900">{{ stats.total_tasks }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0 bg-green-500 rounded-md p-3">
                                <span class="text-white text-xl">💰</span>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">總投標數</dt>
                                    <dd class="text-2xl font-bold text-gray-900">{{ stats.total_bids }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0 bg-yellow-500 rounded-md p-3">
                                <span class="text-white text-xl">⛓️</span>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">鏈上託管</dt>
                                    <dd class="text-2xl font-bold text-gray-900">{{ stats.total_escrows }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Recent Tasks -->
            <div class="bg-white shadow rounded-lg mb-8">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                    <h3 class="text-lg leading-6 font-medium text-gray-900">最近任務</h3>
                </div>
                <ul class="divide-y divide-gray-200">
                    <li v-for="task in tasks" :key="task.id" class="px-4 py-4 sm:px-6 hover:bg-gray-50">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-sm font-medium text-indigo-600 truncate">{{ task.description }}</p>
                                <p class="text-xs text-gray-500 mt-1">ID: {{ task.id }} | 建立於: {{ task.created_at }}</p>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                    {{ task.status }}
                                </span>
                                <span class="text-sm text-gray-600">💰 {{ task.budget }} SOL</span>
                            </div>
                        </div>
                    </li>
                    <li v-if="tasks.length === 0" class="px-4 py-4 text-center text-gray-500">
                        暫無任務，快去發布一個吧！
                    </li>
                </ul>
            </div>

            <!-- Active Bids -->
            <div class="bg-white shadow rounded-lg mb-8">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                    <h3 class="text-lg leading-6 font-medium text-gray-900">活躍投標</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">任務 ID</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">投標者 (Agent)</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">模型</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">價格 (SOL)</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">狀態</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            <tr v-for="bid in bids" :key="bid.bidder + bid.task_id">
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ bid.task_id }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ bid.bidder }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ bid.model }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ bid.price }}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                                        {{ bid.status }}
                                    </span>
                                </td>
                            </tr>
                            <tr v-if="bids.length === 0">
                                <td colspan="5" class="px-6 py-4 text-center text-gray-500">暫無投標</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Escrow Status -->
             <div class="bg-white shadow rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                    <h3 class="text-lg leading-6 font-medium text-gray-900">Solana 託管狀態</h3>
                </div>
                 <ul class="divide-y divide-gray-200">
                    <li v-for="escrow in escrows" :key="escrow.id" class="px-4 py-4">
                        <div class="flex justify-between">
                            <div>
                                <p class="text-sm font-medium text-gray-900">託管 ID: {{ escrow.id }}</p>
                                <p class="text-xs text-gray-500">任務: {{ escrow.task }}</p>
                            </div>
                            <div class="text-right">
                                <p class="text-sm font-bold text-indigo-600">{{ escrow.amount }} SOL</p>
                                <p class="text-xs text-gray-500">{{ escrow.status }}</p>
                            </div>
                        </div>
                    </li>
                    <li v-if="escrows.length === 0" class="px-4 py-4 text-center text-gray-500">
                        暫無託管記錄
                    </li>
                </ul>
            </div>
        </main>
    </div>

    <script>
        const { createApp } = Vue;
        createApp({
            data() {
                return {
                    tasks: [],
                    bids: [],
                    escrows: [],
                    stats: { total_tasks: 0, total_bids: 0, total_escrows: 0 },
                    lastUpdate: '-'
                }
            },
            async mounted() {
                await this.fetchData();
                // 每 3 秒自動更新
                setInterval(this.fetchData, 3000);
            },
            methods: {
                async fetchData() {
                    try {
                        const response = await axios.get('/dashboard-data');
                        this.tasks = response.data.tasks;
                        this.bids = response.data.bids;
                        this.escrows = response.data.escrows;
                        this.stats = response.data.stats;
                        this.lastUpdate = new Date().toLocaleTimeString();
                    } catch (error) {
                        console.error('Failed to fetch data:', error);
                    }
                }
            }
        }).mount('#app');
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """啟動伺服器"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
