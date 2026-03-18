# RESEARCH_SOLVER_SCHEMA

## Purpose
This schema defines the minimum metadata and execution expectations for research-capable solvers.

---

## Capability example

```json
{
  "agent_id": "research_worker_01",
  "model_name": "browser-research-worker",
  "domains": ["research", "market-intel", "technical-analysis"],
  "modalities": ["text", "web", "documents"],
  "tools": ["web", "browser", "citations", "memory"],
  "latency_class": "balanced",
  "cost_class": "medium",
  "max_context_tokens": 128000,
  "trust_level": "verified"
}
```

---

## Recommended fields
### Required
- `agent_id`
- `model_name`
- `domains`
- `tools`
- `trust_level`

### Important optional
- `modalities`
- `latency_class`
- `cost_class`
- `max_context_tokens`

---

## Research-specific domains
Suggested normalized values:
- `research`
- `market-intel`
- `competitor-analysis`
- `technical-analysis`
- `literature-review`
- `fact-synthesis`

---

## Research-specific tools
Suggested normalized values:
- `web`
- `browser`
- `citations`
- `memory`
- `documents`
- `scraping`

---

## Research execution output
A research solver should ideally return:
- `summary`
- `key_findings`
- `sources`
- `confidence`
- `notes`

Example:

```json
{
  "status": "completed",
  "summary": "NVIDIA emphasized agentic AI, AI factories, and robotics.",
  "key_findings": [
    "Open models were highlighted in multiple sessions.",
    "Research workflows are becoming more tool-augmented."
  ],
  "sources": [
    "https://www.nvidia.com/gtc/"
  ],
  "confidence": 0.82,
  "notes": "Based on public web sources."
}
```
