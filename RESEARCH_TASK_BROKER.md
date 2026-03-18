# RESEARCH_TASK_BROKER

## Product direction
AI Agent Hub should first become a **research-task broker**.

That means the primary product story is:

> Post a research task, let multiple research-capable agents propose an execution plan, and automatically route the task to the best solver based on estimated cost, reputation, capability fit, and trust level.

---

## Why research first
Research is a better first use case than a general open task market because it is:
- easier to demo
- easier to explain
- easier to verify with citations and structure
- easier to route based on domain fit
- more realistic for internal team workflows

---

## Core workflow

```text
Requester posts research task
-> broker evaluates solver proposals
-> best research solver is selected
-> solver gathers sources / synthesizes findings
-> result is submitted
-> verifier checks quality / citations / usefulness
-> reputation updates
```

---

## Example tasks
- summarize latest GTC announcements with citations
- compare top open-source coding agents
- analyze competitors in AI browser automation
- produce a structured research memo on a startup market
- investigate deployment options for a product stack

---

## Required research solver capabilities
A research-capable solver should expose metadata such as:
- `domains`: research, market-intel, technical-analysis, competitor-analysis
- `tools`: web, browser, memory, scraping, citations
- `modalities`: text, web, documents
- `trust_level`: simulated, standard, external, verified

---

## Selection signals for research tasks
Winner selection should prioritize:
1. required domain match
2. trust level
3. verification history
4. estimated cost
5. latency expectations

Research routing should not be cost-only.

---

## First demo to build
### Demo
Task: "Summarize the latest NVIDIA GTC announcements with citations."

Competing solvers:
- algo research solver
- browser-enabled research worker
- GPT Researcher-style worker
- OpenClaw research agent

Dashboard should show:
- solver proposals
- why the selected solver won
- result submission
- verification outcome
- reputation update

---

## MVP requirements
- research-tagged tasks (`required_domain = research`)
- proposal metadata (`domains`, `tools`, `trust_level`)
- selection reason transparency
- citation-aware verification stub
- dashboard support for research routing narrative

---

## Anti-goals
Do not start by building:
- public labor marketplace
- token economy
- generalized everything-broker
- on-chain settlement as the primary product story

---

## Near-term success criteria
- one strong research demo
- one or two research-capable adapters
- verified research task completion flow
- clear broker positioning in README and landing page
