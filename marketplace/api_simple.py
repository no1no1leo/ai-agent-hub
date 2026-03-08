"""
純 HTML/JavaScript 版本的首頁
無 Vue.js 依賴，使用原生 JS
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
from .metrics import update_market_metrics, tasks_created
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="AI Agent Marketplace", version="2.1.0")

# === 數據模型 ===
class CreateTaskRequest(BaseModel):
    description: str
    input_data: str
    max_budget: float = Field(gt=0, description="預算必須大於 0")
    expected_tokens: int = Field(gt=0, description="預期 token 數必須大於 0")
    requester_id: Optional[str] = "anonymous"
    currency: Optional[str] = "USDC"
    
    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('任務描述不能為空')
        return v.strip()

# === CORS ===
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === API 端點 ===
@app.get("/api/stats")
async def get_stats_json():
    base_stats = market.get_market_stats()
    sol_price_usdc = 100.0
    avg_sol = base_stats.get("avg_winning_bid", 0)
    return {
        "market": {**base_stats, "avg_winning_bid_usdc": avg_sol * sol_price_usdc, "currency": "USDC"},
        "solana": solana_escrow.get_market_stats() if solana_escrow else {},
        "exchange_rate": {"SOL_USDC": sol_price_usdc}
    }

@app.get("/api/dashboard-data")
async def get_dashboard_data_json():
    tasks = [{"id": t.task_id, "desc": t.description, "budget": t.max_budget, "status": t.status.value, "currency": getattr(t, 'currency', 'USDC')} for t in market.tasks.values()]
    bids = []
    for tid, blist in market.bids.items():
        for b in blist:
            bids.append({"task": tid, "bidder": b.bidder_id, "price": b.bid_price, "currency": getattr(b, 'currency', 'USDC')})
    base_stats = market.get_market_stats()
    sol_price_usdc = 100.0
    return {"tasks": tasks[-5:], "bids": bids[-5:], "stats": {**base_stats, "avg_winning_bid_usdc": base_stats.get("avg_winning_bid", 0) * sol_price_usdc, "currency": "USDC"}}

@app.post("/tasks")
async def create_task(request: CreateTaskRequest):
    try:
        task = market.create_task(
            description=request.description, input_data=request.input_data,
            max_budget=request.max_budget, expected_tokens=request.expected_tokens,
            requester_id=request.requester_id
        )
        if hasattr(task, 'currency'):
            task.currency = request.currency
        tasks_created.labels(currency=request.currency).inc()
        return {"task_id": task.task_id, "status": "created", "currency": request.currency}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# === 純 HTML/JavaScript 首頁 ===
@app.get("/", response_class=HTMLResponse)
async def landing_page():
    # 獲取當前數據
    stats = market.get_market_stats()
    tasks_list = list(market.tasks.values())[-5:]
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Trading Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background-color: #0f172a; color: #fff; font-family: 'Inter', sans-serif; }}
        .gradient-text {{ background: linear-gradient(to right, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; color: transparent; }}
        .card {{ background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }}
        .neon-border {{ box-shadow: 0 0 10px rgba(99, 102, 241, 0.5); }}
    </style>
</head>
<body class="min-h-screen flex flex-col">
    <div class="flex-grow">
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
                <a href="#market-section" class="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-full font-bold transition transform hover:scale-105 shadow-lg shadow-indigo-500/50">
                    查看即時市場
                </a>
                <a href="/docs" class="px-8 py-3 card hover:bg-white/10 rounded-full font-bold transition">
                    API 文檔
                </a>
            </div>
        </header>

        <!-- Live Stats -->
        <section class="max-w-6xl mx-auto px-4 mb-16">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="card p-6 rounded-2xl text-center neon-border">
                    <div class="text-4xl font-bold text-indigo-400 mb-2" id="stat-tasks">{stats['total_tasks']}</div>
                    <div class="text-gray-400">已發布任務</div>
                </div>
                <div class="card p-6 rounded-2xl text-center">
                    <div class="text-4xl font-bold text-green-400 mb-2" id="stat-bids">{stats['total_bids']}</div>
                    <div class="text-gray-400">已完成投標</div>
                </div>
                <div class="card p-6 rounded-2xl text-center">
                    <div class="text-4xl font-bold text-pink-400 mb-2" id="stat-avg">${{stats['avg_winning_bid'] * 100:.2f}}</div>
                    <div class="text-gray-400">平均成交價 (USDC)</div>
                </div>
            </div>
        </section>

        <!-- Create Task Form -->
        <section class="max-w-4xl mx-auto px-4 mb-16">
            <div class="card rounded-2xl p-6">
                <h2 class="text-2xl font-bold mb-6">📝 發布新任務</h2>
                <form id="task-form" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-1">任務描述</label>
                        <input name="description" type="text" placeholder="例如：翻譯一段文字" required
                            class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">輸入數據</label>
                            <input name="input_data" type="text" placeholder="例如：Hello world"
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">預算 (USDC)</label>
                            <input name="max_budget" type="number" step="0.1" min="0.1" value="1.0" required
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">預期 Token 數</label>
                            <input name="expected_tokens" type="number" min="1" value="100" required
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-400 mb-1">請求者 ID</label>
                            <input name="requester_id" type="text" value="web_user"
                                class="w-full px-4 py-2 bg-white/5 border border-gray-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white">
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <button type="submit" id="submit-btn"
                            class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-bold transition">
                            🚀 發布任務
                        </button>
                        <span id="form-message" class="text-sm"></span>
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
            
            <div class="card rounded-2xl p-6 mb-8">
                <h3 class="text-xl font-bold mb-4 text-indigo-300">最近任務</h3>
                <div id="tasks-list" class="space-y-3">
                    {''.join([f"""<div class="flex justify-between items-center p-3 hover:bg-white/5 rounded-lg transition">
                        <div>
                            <div class="font-medium">{t.description}</div>
                            <div class="text-xs text-gray-500">ID: {t.task_id}</div>
                        </div>
                        <div class="text-right">
                            <div class="font-bold text-green-400">{t.max_budget} USDC</div>
                            <div class="text-xs text-gray-500">{t.status.value}</div>
                        </div>
                    </div>""" for t in reversed(tasks_list)]) if tasks_list else '<div class="text-center text-gray-500 py-4"><div class="text-4xl mb-2">📭</div><div>尚無任務，成為第一個發布者！</div></div>'}
                </div>
            </div>
        </section>
    </div>

    <script>
        // 表單提交處理
        document.getElementById('task-form').addEventListener('submit', async function(e) {{
            e.preventDefault();
            const btn = document.getElementById('submit-btn');
            const msg = document.getElementById('form-message');
            btn.disabled = true;
            btn.textContent = '⏳ 創建中...';
            
            try {{
                const formData = new FormData(e.target);
                const data = {{
                    description: formData.get('description'),
                    input_data: formData.get('input_data'),
                    max_budget: parseFloat(formData.get('max_budget')),
                    expected_tokens: parseInt(formData.get('expected_tokens')),
                    requester_id: formData.get('requester_id'),
                    currency: 'USDC'
                }};
                
                const res = await fetch('/tasks', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(data)
                }});
                
                if (res.ok) {{
                    const result = await res.json();
                    msg.textContent = '✅ 任務創建成功！ID: ' + result.task_id;
                    msg.className = 'text-sm text-green-400';
                    e.target.reset();
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    const err = await res.json();
                    msg.textContent = '❌ 創建失敗：' + (err.detail || '未知錯誤');
                    msg.className = 'text-sm text-red-400';
                }}
            }} catch (e) {{
                msg.textContent = '❌ 網路錯誤：' + e.message;
                msg.className = 'text-sm text-red-400';
            }} finally {{
                btn.disabled = false;
                btn.textContent = '🚀 發布任務';
            }}
        }});
        
        // 自動刷新數據
        async function refreshStats() {{
            try {{
                const res = await fetch('/api/dashboard-data');
                const data = await res.json();
                document.getElementById('stat-tasks').textContent = data.stats.total_tasks;
                document.getElementById('stat-bids').textContent = data.stats.total_bids;
                document.getElementById('stat-avg').textContent = '$' + (data.stats.avg_winning_bid_usdc || 0).toFixed(2);
            }} catch (e) {{ console.error('Refresh error:', e); }}
        }}
        
        setInterval(refreshStats, 5000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

# === Prometheus 指標端點 ===
@app.get("/metrics")
async def metrics():
    update_market_metrics(market, solana_escrow)
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# === 健康檢查端點 ===
@app.get("/health")
async def health_check():
    update_market_metrics(market, solana_escrow)
    return {{
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market": {{
            "total_tasks": len(market.tasks),
            "active_tasks": len([t for t in market.tasks.values() if t.status.value == "open"])
        }},
        "solana": {{
            "total_escrows": len(solana_escrow.escrows) if solana_escrow else 0,
            "tvl": solana_escrow.total_value_locked if solana_escrow else 0
        }}
    }}

# === 全局異常處理 ===
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局異常: {{exc}}")
    raise HTTPException(status_code=500, detail=str(exc))

def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
