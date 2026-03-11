# SECURITY_HARDENING_PLAN.md

## Scope
Leakage/exfiltration risk reduction in Paperclip runtime execution paths.

## Implemented now

### 1) Child env allowlist baseline
Patched `server/src/services/workspace-runtime.ts` to stop blindly inheriting full host env for key runtime execution paths.

Changes:
- Added `buildSafeBaseEnv()` helper with allowlist keys:
  - `PATH`, `HOME`, `SHELL`, `TMPDIR`, `LANG`, `LC_ALL`, `LC_CTYPE`, `TERM`, `TZ`
- Switched these call sites from `process.env` spread to safe base env:
  - `runGit(...): spawn(..., env)`
  - `buildWorkspaceCommandEnv(...)`
  - `startLocalRuntimeService(...)` local process env construction

Security effect:
- Reduces accidental propagation of host secrets (API keys/tokens) into child processes.

## Next hardening steps (recommended)

1. **Network egress allowlist**
   - Restrict `fetch` targets for portability/runtime checks.
   - Block metadata/internal ranges by default.

2. **Command execution policy**
   - Reduce `shell -c` usage where possible.
   - Introduce strict validation for config-driven commands.

3. **Run-output redaction pass**
   - Apply redaction to persisted run payload text, not only event payloads.

4. **Context boundary controls**
   - Enforce issue/project binding; fail closed when issue context is missing for issue-mode runs.

5. **Delete-path robustness**
   - Fix backend 500s in agent/project delete flows to prevent orphaned state.

## Verification checklist
- [ ] Runtime children still boot with required env
- [ ] No regressions in workspace provisioning
- [ ] No secrets from host env appear in child runtime diagnostics
- [ ] Existing tests pass
