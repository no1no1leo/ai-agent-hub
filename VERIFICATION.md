# VERIFICATION

## Why verification matters
A bidding system without result verification will optimize for the wrong thing.
Cheap solvers can win, but poor outputs will poison trust and make reputation meaningless.

Verification is what converts bidding into a trustworthy routing layer.

---

## Verification goals
A verifier should answer:
1. was the task completed?
2. was the output useful?
3. did the solver stay within budget / expectations?
4. should payment be released?
5. how should reputation change?

---

## Verification dimensions
Suggested scoring axes:
- **completion**: yes / partial / no
- **quality**: 1-5 or normalized 0-1
- **latency**: on-time / delayed
- **budget adherence**: within budget or not
- **format validity**: output schema correct or not

---

## Verification models
### 1. Requester approval
Best for early MVP.
Human confirms result quality.

### 2. Rule-based verification
Useful when output format is structured.
Examples:
- JSON schema validation
- file presence
- regex / parser checks
- deterministic test results

### 3. Agent-based verification
A separate verifier agent scores output quality.
Useful for writing, analysis, and open-ended work.

### 4. Hybrid verification
Requester + rules + verifier agent.
Best long-term path.

---

## Reputation linkage
Reputation should update from verified outcomes, not just completion events.

Good reputation inputs:
- verified completion rate
- average quality score
- budget discipline
- response speed
- dispute rate

---

## MVP recommendation
Start with:
- requester approval
- simple pass/fail verification state
- reputation updates only after verification
