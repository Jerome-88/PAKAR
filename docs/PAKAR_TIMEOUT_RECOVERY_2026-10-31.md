# Partial-report recovery after runtime timeout

## Observed failure

The user's live swarm run stopped after 182.804 seconds, although its total
configured budget was 300 seconds. Preparation had consumed part of that budget;
the simulation phase then reached its own boundary while 115.215 seconds had
been reserved for specialist review. The outer error path skipped that review
phase and report construction. Six interaction events were already committed;
six model calls had completed and a seventh call had started without a final
usage record.

This is an observed live timeout, not validation of live swarm argument quality.
Earlier fixture and local-provider swarm tests remain separate evidence.

## Implemented behavior

- Replay committed interactions through the existing pairwise/swarm reducers.
  Require matching event IDs, kinds and authoritative state transitions; reject
  gaps or inconsistent state. Recovery never generates substitute dialogue.
- If the runtime process times out or its provider fails after committing valid
  interactions, retain that partial simulation and continue the originally
  planned specialist phase within the original remaining budget. Do not restart
  the simulation or automatically repeat paid inference.
- Reserve the entire runtime token allocation when a hard interruption leaves
  usage uncertain. Missing usage/cost remains unknown rather than becoming zero.
- Historical failed OASIS runs with a time-budget stop and committed events can
  expose a read-only partial-report projection. The original failed result,
  status, frozen inputs and event log remain unchanged. Detail, report and HTML
  export use the same projection; the UI explicitly says specialist AI review
  was not run. Project history retains the original execution status.
- Swarm turns use a 35-second SDK/request timeout by default, no SDK retries,
  latency preference within existing provider restrictions, and a remaining-time
  admission check before starting another turn. Parent process limits and replay
  remain necessary: synchronous SDK work is not guaranteed to be preemptible at
  exactly the per-turn timeout. These changes do not guarantee a complete debate
  or all specialist reviews within every run's budget.

The affected live run was read successfully as a partial report with six original
events and eight report sections. Recovery made zero new model calls. Its raw
result remained identical before and after the read (SHA-256
`5e8ca5dfa3d50f6f01c4f114313f4095173d2d76305c7abda75da84e3ac7b74e`).
No source document text, participant messages or credentials are copied here.

## Verification

Four focused recovery tests pass. They cover a runtime interruption, a genuinely
killed child process, continuation to the reserved review phase, historical
read/report/export without data mutation or new calls, owner isolation,
cancellation exclusion, private financial transactions, and rejection of
inconsistent event streams. Tests use local data and mocked/local providers.

Full backend pass: **247 passed, 2 skipped, 1 failed**. The failure was the local
installed-runtime swarm protocol test: cold OASIS/ML imports consumed most of its
60-second budget, leaving too little time for all eight turns under the new
admission check. Its local-only process budget is now 120 seconds, with a
5-second local-provider turn timeout. No assertions were weakened. The final
runtime/recovery suite passes **7 tests**, including both installed-runtime modes
and the separate short-budget physical process-kill case. During the subsequent
continuation package, the full recovery suite was repeated successfully:
**248 passed, 2 skipped**. The expanded final package passes **250 tests with
2 skipped**; see [continuation results](PAKAR_SPECIALIST_CONTINUATION_2026-10-31.md).

Frontend production build, ESLint and six affected report/discussion tests pass.
The existing bundle-size warning remains. `git diff --check` passes.
No paid model calls were made for this repair, and the existing credit ceiling
was not reset.
