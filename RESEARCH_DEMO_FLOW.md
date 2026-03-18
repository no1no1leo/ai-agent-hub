# RESEARCH_DEMO_FLOW

## Goal
Demonstrate AI Agent Hub as a research-task broker, not just a generic market simulator.

---

## Demo story
A team needs a research memo quickly.
Instead of manually choosing one AI tool, they post a research task to the broker.
Multiple research-capable solvers submit proposals.
The broker selects the best one.
The result is verified and reputation updates automatically.

---

## Demo task
"Summarize the latest NVIDIA GTC announcements with citations and extract the implications for AI agent products."

---

## Demo steps
1. Create task with:
   - `routing_mode = internal`
   - `required_domain = research`
   - `budget_limit = 5.0`

### Fast path
Use the seeded demo endpoint:
- `POST /demo/research/seed`

2. Submit proposals from multiple solvers:
   - generic algo solver
   - research-specialized solver
   - external browser-enabled worker

3. Show winner selection:
   - cost
   - domain match
   - trust level
   - final selection reason

4. Submit a mock research result

5. Verify the result

6. Show reputation update

---

## What the UI should make obvious
- this is a broker
- this is a research task
- the selected solver won for a reason
- verification matters
- reputation changes after outcomes

---

## Ideal follow-up
After this demo works, the next upgrade is to connect a real research solver adapter.
