# ROADMAP

## Phase 1 — Clarify the product
Goal: make the repo and landing page communicate a startup-ready story.

### Deliverables
- Rewrite README
- Rewrite landing page hero copy
- Add positioning docs
- Reframe escrow as optional settlement, not core identity
- Update architecture docs around broker / solver / verifier flow

---

## Phase 2 — Add execution lifecycle
Goal: move beyond bidding simulation.

### Deliverables
- task states: posted -> bidding -> assigned -> in_progress -> submitted -> verified -> paid
- result submission flow
- execution adapter interface
- completion records

---

## Phase 3 — Real solver adapters
Goal: allow real agents to participate.

### Deliverables
- OpenClaw adapter
- Codex / Claude / generic HTTP worker adapter
- capability metadata for solver agents
- routing rules based on fit + cost + reputation

---

## Phase 4 — Verification and reputation quality
Goal: make reputation reflect actual outcomes.

### Deliverables
- verifier hooks
- outcome scoring
- latency / budget / quality dimensions
- dispute / override flow

---

## Phase 5 — Team-ready product
Goal: make it usable by small teams.

### Deliverables
- workspace / tenant model
- policy constraints
- budget caps
- allowlists
- audit logs
- chat / webhook integrations

---

## Not a priority right now
- tokenomics
- DAO / governance narrative
- public decentralized labor market story
- on-chain complexity before execution quality is solved
