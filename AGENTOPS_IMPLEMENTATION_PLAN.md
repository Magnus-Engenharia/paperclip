# AGENTOPS_IMPLEMENTATION_PLAN.md

## Goal
Make Paperclip agent execution reliable, measurable, and release-oriented by implementing an operations-first framework (AgentOps) aligned with model/tool/orchestration/runtime best practices.

---

## Phase 1 — Observability Foundation (Day 0-2)

### 1. Run Scorecard (per run)
Add a normalized scorecard object persisted alongside heartbeat runs:

```json
{
  "runId": "...",
  "agentId": "...",
  "companyId": "...",
  "issueId": "...",
  "contextBound": true,
  "artifactCount": 2,
  "artifactPaths": ["backend/docs/openapi.yaml"],
  "acceptancePassed": false,
  "status": "failed",
  "failureReason": "missing_artifact",
  "startedAt": "...",
  "finishedAt": "...",
  "durationMs": 12345
}
```

### 2. Core metrics
Track and expose (dashboard + API):
- Issue-context binding success rate
- Artifact compliance rate
- Task completion rate
- Timeout/retry rate
- Blocker age (P0/P1)
- False-success rate (run says success but acceptance fails)

### 3. Health SLOs
- API availability >= 99.5%
- Run dispatch latency p95 < 3s
- Timeout rate < 5%
- Context-bound runs > 95%

---

## Phase 2 — Orchestration Correctness (Day 2-5)

### 1. Deterministic issue binding
For issue-mode runs:
- Require issue context envelope from scheduler
- If missing, perform server-side fallback lookup by assignee
- If still missing: fail closed with explicit code `issue_context_missing`

### 2. Checkout ownership enforcement
- Bind `checkoutRunId` to active run
- Prevent cross-run closure without ownership adoption flow
- Log ownership adoption events for stale run recovery

### 3. Completion validator
Before marking run success:
- Validate required artifact paths exist
- Validate acceptance checklist from issue
- Validate status transition rules

If validator fails, status becomes `failed_validation`.

---

## Phase 3 — Release Gate System (Day 5-8)

### 1. Canonical release gate object
Create a first-class release gate state:

```json
{
  "companyId": "...",
  "projectId": "...",
  "gates": {
    "api_contract_synced": "pass|fail|unknown",
    "core_daily_flow": "pass|fail|unknown",
    "qa_gate": "pass|fail|unknown",
    "p0_zero": "pass|fail|unknown",
    "runbook_dry_run": "pass|fail|unknown"
  },
  "overall": "ready|blocked",
  "updatedAt": "..."
}
```

### 2. Gate updater
- CTO/QA runs can update gate evidence
- Board/CEO sees aggregated readiness
- Block release if any gate != pass

### 3. Gate-linked issue generation
If gate fails, auto-create corrective issue with:
- objective ID
- exact output paths
- DoD
- evidence requirements

---

## Phase 4 — Safety + Security Controls (Day 8-10)

### Already implemented (baseline)
- Child env allowlist for runtime execution
- Command safety policy for dangerous shell patterns
- SSRF/egress guards for portability and readiness URLs
- Redaction on persisted run outputs

### Additions
1. Outbound destination telemetry
   - Record hostnames accessed by runtime fetches
2. Redaction test suite
   - Regression tests for token/JWT/auth-header masking
3. Unsafe command override audit
   - Emit explicit audit event when `PAPERCLIP_RUNTIME_ALLOW_UNSAFE_COMMANDS=true`

---

## Phase 5 — Runtime Stability & Recovery (Day 10-12)

### 1. Crash loop protection
- Detect rapid restart loops
- Auto-pause offending agents
- Keep API available while isolating bad adapters

### 2. Auto-heal policy
On `context_size_exceeded` or repeated timeout:
- reset runtime session once
- retry once with compact prompt profile
- if still failing, mark blocked with reason

### 3. Adapter compatibility matrix
- Validate payload schema per adapter mode
- Feature flags for optional envelopes (e.g., `includePaperclipEnvelope`)

---

## API Changes (proposed)

### New endpoints
- `GET /companies/:id/agentops/metrics`
- `GET /runs/:id/scorecard`
- `GET /companies/:id/release-gates`
- `PATCH /companies/:id/release-gates`

### Extended run payload
- Add `scorecardJson` to heartbeat run record

### Extended issue schema
- Add optional `acceptanceChecklist`, `requiredArtifactPaths`, `evidencePolicy`

---

## Dashboard Changes (proposed)

### AgentOps panel
- Context-bound %
- Artifact compliance %
- Timeout trend
- Top blocker list

### Release panel
- Gate statuses
- Evidence links
- “Ready to Release” binary + blockers

---

## Rollout Strategy

1. **Shadow mode** (no blocking)
   - Compute scorecards and validators but don’t block runs
2. **Warn mode**
   - Flag bad completions in UI/API
3. **Enforce mode**
   - Block success transitions when validator fails

Rollback: single config flag `AGENTOPS_ENFORCEMENT=false`.

---

## Success Criteria

- >95% runs are issue-context bound
- >90% successful runs have verified artifacts
- timeout rate cut by 50%
- false-success rate near zero
- release gate reflects true release readiness in real time

---

## First Tasks to Open
1. Implement `scorecardJson` persistence + API
2. Build completion validator (artifact + acceptance)
3. Add release gate object and dashboard widget
4. Add crash-loop isolation for unstable adapters
5. Add redaction regression tests
