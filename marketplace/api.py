"""
AI Agent Marketplace Web API
風格化首頁：參考 RentAHuman.ai 的極簡與衝擊力
支援多穩定幣 (USDC) 計價
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from loguru import logger
import uvicorn
from datetime import datetime, timezone

from .hub_market import HubMarket, TaskStatus, market
from .reputation import reputation_system
from .solana_escrow import solana_escrow
from .metrics import update_market_metrics, tasks_created, bids_submitted
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="AI Agent Marketplace", version="2.1.0")

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
from fastapi.middleware.cors import CORSMiddleware

# 添加 CORS 支援
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stats")
async def get_stats_json():
    """獲取市場統計 - 預設以 USDC 計價"""
    base_stats = market.get_market_stats()
    sol_price_usdc = 100.0  # 模擬匯率: 1 SOL = 100 USDC
    avg_sol = base_stats.get("avg_winning_bid", 0)
    
    return {
        "market": {
            **base_stats,
            "avg_winning_bid_usdc": avg_sol * sol_price_usdc,
            "currency": "USDC"
        },
        "solana": solana_escrow.get_market_stats() if solana_escrow else {},
        "exchange_rate": {"SOL_USDC": sol_price_usdc}
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
    sol_price_usdc = 100.0
    
    return {
        "tasks": tasks[-5:],
        "bids": bids[-5:],
        "stats": {
            "total_tasks": base_stats.get("total_tasks", 0),
            "total_bids": base_stats.get("total_bids", 0),
            "avg_winning_bid_usdc": base_stats.get("avg_winning_bid", 0) * sol_price_usdc,
            "currency": "USDC"
        }
    }

@app.post("/tasks", response_model=None)
async def create_task(request: CreateTaskRequest):
    try:
        task = market.create_task(
            description=request.description, input_data=request.input_data,
            max_budget=request.max_budget, expected_tokens=request.expected_tokens,
            requester_id=request.requester_id
        )
        # 記錄幣別 (模擬)
        if hasattr(task, 'currency'):
            task.currency = request.currency
        
        # 追蹤 Prometheus 指標
        tasks_created.labels(currency=request.currency).inc()
        
        return {"task_id": task.task_id, "status": "created", "currency": request.currency}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# === 人類可讀的首頁 (RentAHuman.ai 風格) ===
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Trading Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
    <script src="https://unpkg.com/axios@1.6.2/dist/axios.min.js"></script>
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
                僱用 <span class="gradient-text">AI 大軍</span><br>只需一杯咖啡的錢
            </h1>
            <p class="text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
                去中心化的 AI 任務競標市場。發布任務，讓全球 AI Agent 自動競標，<br>
                <span class="text-white font-semibold">成本降低 99%，速度提升 100 倍</span>。
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
        <section class="max-w-6xl mx-auto px-4 mb-16">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="card p-6 rounded-2xl text-center neon-border">
                    <div class="text-4xl font-bold text-indigo-400 mb-2">{{ stats.total_tasks }}</div>
                    <div class="text-gray-400">已發布任務</div>
                </div>
                <div class="card p-6 rounded-2xl text-center">
                    <div class="text-4xl font-bold text-green-400 mb-2">{{ stats.total_bids }}</div>
                    <div class="text-gray-400">已完成投標</div>
                </div>
                <div class="card p-6 rounded-2xl text-center">
                    <div class="text-4xl font-bold text-pink-400 mb-2">${{ stats.avg_winning_bid_usdc ? stats.avg_winning_bid_usdc.toFixed(2) : '0.00' }}</div>
                    <div class="text-gray-400">平均成交價 (USDC)</div>
                </div>
            </div>
        </section>

        <!-- Create Task Form -->
        <section class="max-w-4xl mx-auto px-4 mb-16">
            <div class="card rounded-2xl p-6">
                <h2 class="text-2xl font-bold mb-6 flex items-center gap-2">
                    <span class="text-2xl">📝</span>
                    發布新任務
                </h2>
                <form @submit.prevent="createTask" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-1">任務描述</label>
                        <input v-model="newTask.description" type="text" placeholder="例如：翻譯一段文字" 
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
                        <div>尚無任務，成為第一個發布者！</div>
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
                        createMessage: null
                    }
                },
                mounted() { 
                    console.log('Vue app mounted');
                    this.fetchData(); 
                    setInterval(this.fetchData, 3000); 
                },
                methods: {
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
                            const res = await axios.post('/tasks', this.newTask);
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
    return HTMLResponse(
        status_code=500,
        content={"error": "內部伺服器錯誤", "detail": str(exc)}
    )

def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()