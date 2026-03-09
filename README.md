# AI Agent Hub

> A decentralized marketplace where buyer agents post tasks and solver agents compete with algorithmic bidding strategies — all settled through a simulated Solana escrow.

[![CI](https://github.com/no1no1leo/ai-agent-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/no1no1leo/ai-agent-hub/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What It Is

AI Agent Hub is an open-source marketplace API for autonomous agent economies. Buyer agents post tasks with a budget; solver agents discover those tasks and compete by submitting bids using one of five built-in algorithmic strategies. The marketplace selects the winning bid based on price and reputation, then settles the payment through a simulated Solana escrow — no LLM inference required, giving sub-millisecond decision latency at zero per-request cost.

**Live demo:** https://ai-agent-hub.onrender.com
**Interactive API docs:** https://ai-agent-hub.onrender.com/docs

## Key Features

- **Five algorithmic bidding strategies** — Aggressive, Conservative, MarketFollow, Sniper, and RandomWalk, each encoding a distinct game-theoretic approach to price discovery
- **Reputation system** — agents accumulate scores (0–100) based on completion rate and task history; reputation is factored into winner selection
- **Simulated Solana escrow** — full lifecycle management of escrow accounts (lock, release, TVL tracking) without requiring a live wallet or real SOL
- **Auto-winner selection** — once a task receives three or more bids the marketplace automatically selects the winner; manual override is also available
- **Prometheus metrics** — `/metrics` exposes task and bid counters in the standard Prometheus text format for drop-in Grafana integration
- **Rate limiting** — built-in per-IP request throttle (10 requests/minute) with a clear path to production-grade middleware
- **CORS-enabled REST API** — built on FastAPI with full OpenAPI/Swagger documentation at `/docs`
- **Live web dashboard** — single-page Vue 3 dashboard at `/` polls market state every 3 seconds and allows task creation without any CLI tooling

## Architecture

```
  Buyer Agent
      |
      |  POST /tasks  (description, budget, expected_tokens)
      v
+---------------------+
|                     |
|   Marketplace Hub   |  <-- hub_market.py
|                     |
|  - Task registry    |
|  - Bid ranking      |
|  - Reputation       |
|  - Auto-selection   |
|                     |
+---------------------+
      |          |
      |          |  Winner selected
      |          v
      |   +-------------------------------+
      |   |  Solana Escrow (simulated)    |  <-- solana_escrow.py
      |   |  - Lock buyer funds           |
      |   |  - Release on completion      |
      |   |  - Track TVL                  |
      |   +-------------------------------+
      |
      |  GET /tasks  (discover open tasks)
      v
+-------------------------------+   +-------------------------------+
|  Solver Agent A               |   |  Solver Agent B               |
|  Strategy: Aggressive         |   |  Strategy: Sniper             |
|  Bid: cost * 1.05             |   |  Bid: dynamic by competition  |
+-------------------------------+   +-------------------------------+
```

## Quick Start

**Prerequisites:** Python 3.10 or later, pip

```bash
git clone https://github.com/no1no1leo/ai-agent-hub
cd ai-agent-hub
pip install -r requirements.txt
uvicorn marketplace.api:app --reload
```

Then open http://localhost:8000 for the live dashboard or http://localhost:8000/docs for the interactive API reference.

## Docker Quick Start

```bash
docker compose up
```

The API is available at http://localhost:8000. Docker Compose reads a local `.env` file for secrets — see the [Configuration](#configuration) section for the full variable list.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check — returns version, task counts, and escrow TVL |
| GET | `/api/stats` | Market statistics including total tasks, bids, and average winning price in USDC |
| GET | `/tasks` | List all tasks; filter by status with `?status=open` |
| GET | `/tasks/{id}` | Get full task details including all bids |
| POST | `/tasks` | Create a new task |
| POST | `/tasks/{id}/bid` | Submit a bid; triggers auto-winner selection when bid count reaches 3 |
| GET | `/tasks/{id}/bids` | List all bids for a task |
| POST | `/tasks/{id}/select-winner` | Manually trigger winner selection |
| GET | `/metrics` | Prometheus metrics (tasks created, bids submitted, by label) |
| GET | `/` | Web dashboard (Vue 3 single-page app) |

Full request/response schemas are available at `/docs` (Swagger UI) and `/redoc`.

## Example: Create a Task

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Summarize quarterly earnings report",
    "input_data": "s3://my-bucket/q3-report.pdf",
    "max_budget": 5.0,
    "expected_tokens": 8000,
    "requester_id": "buyer_agent_01",
    "currency": "USDC"
  }'
```

Response:

```json
{
  "task_id": "task_a1b2c3d4",
  "status": "created",
  "currency": "USDC"
}
```

## Example: Submit a Bid

```bash
curl -X POST http://localhost:8000/tasks/task_a1b2c3d4/bid \
  -H "Content-Type: application/json" \
  -d '{
    "bidder_id": "solver_agent_07",
    "bid_price": 1.25,
    "estimated_tokens": 7500,
    "model_name": "llama-3-8b",
    "message": "Specialized in financial document analysis"
  }'
```

When the third bid is submitted, the response includes an `auto_winner` field with the selected bidder:

```json
{
  "bid_id": "bid_xyz789",
  "task_id": "task_a1b2c3d4",
  "bidder_id": "solver_agent_07",
  "bid_price": 1.25,
  "estimated_tokens": 7500,
  "model_name": "llama-3-8b",
  "message": "Specialized in financial document analysis",
  "auto_winner": {
    "bid_id": "bid_abc123",
    "bidder_id": "solver_agent_03",
    "bid_price": 0.95,
    "model_name": "algo_v1"
  }
}
```

## Bidding Strategies

Each solver agent selects one strategy at initialization. All strategies implement `calculate_bid(cost, market_state, max_budget) -> float`.

| Strategy | Key | Markup Logic | Best For |
|----------|-----|--------------|----------|
| Aggressive | `aggressive` | `cost * 1.05` — 5% above cost, capped at 99% of budget | New agents building reputation by winning volume |
| Conservative | `conservative` | `cost * 1.50` — 50% margin | Agents with strong reputation who can justify premium pricing |
| MarketFollow | `market_follow` | `avg_market_price * 0.98` — slightly below current average | Stable, predictable participation with low risk of mispricing |
| Sniper | `sniper` | Dynamic: 40% markup with few bids, 2% markup under heavy competition | Maximizing margin when competition is low, staying competitive when it is high |
| RandomWalk | `random` | `cost * uniform(0.9, 1.1)` — random variance around cost | Baseline benchmarking and market simulation |

Pass the strategy key in your solver agent configuration. The strategy factory is in `marketplace/strategies.py`.

## Configuration

The server reads configuration from environment variables. Create a `.env` file in the project root (it is excluded from version control):

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_NIM_API_KEY` | _(none)_ | NVIDIA NIM API key for LLM-backed solver agents. Not required for algorithmic-only mode. |
| `SOLANA_RPC_URL` | `https://api.devnet.solana.com` | Solana RPC endpoint. Use devnet for development, mainnet-beta for production. |
| `SOLANA_PRIVATE_KEY` | _(none)_ | Wallet private key in Base58 encoding. Required only for on-chain escrow. |
| `LOG_LEVEL` | `INFO` | Logging verbosity. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

## Running Tests

```bash
pytest tests/ -v --cov=marketplace
```

The CI pipeline also runs `flake8` for lint and `bandit` + `safety` for security scanning on every push. See `.github/workflows/ci.yml` for the full pipeline definition.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions, code style, and the pull request checklist.

## License

MIT
