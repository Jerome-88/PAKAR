# Groq configuration and small live check

The local backend now uses `https://api.groq.com/openai/v1`, model
`openai/gpt-oss-20b`, and strict structured outputs. `FREE_AI_KEY` is selected
only for the exact Groq hostname; an explicit Settings key override still wins.
The OASIS child environment resolves the same key without overwriting the
parent's existing provider credential. Both Compose configurations pass the
optional alias to API and worker containers. Existing OpenRouter keys remain
stored but are not used for Groq requests. No automatic provider fallback.

Live validation authenticated the key and confirmed the selected model is
available. One call through `BusinessLLM` returned valid structured JSON about
the synthetic Pepsodent idea: the association between colour change and tooth
cleanliness needs clinical evidence. The call consumed 519 tokens and completed
in 4.671 seconds. Provider-reported cost was unavailable; this is not a guarantee
that the account or future requests are free. The safe result is saved in
`backend/data/runtime-audit/2026-11-08/groq/smoke.json`.

Groq configuration, strict-schema and direct-OASIS regression tests passed in
the separate `pakar_groq_test` database, with one optional integration skipped.
Both Compose configurations validated. No running jobs were present before the
local backend restart. Full swarm execution and sustained RPM/TPM handling on
this Groq account have not been live-tested. Saved demo results are unchanged.

A first test mistakenly removed the alias from the environment, allowing the
installed dotenv loader to reload the developer key. Assertion diagnostics
exposed the key in tool output. The dedicated tests now mock dotenv loading;
the credential isolation fixture clears the alias as well. Rotate that Groq
key, replace `FREE_AI_KEY`, and restart API/worker processes before continued
use. No key value is included in this report or the saved live-check result.

References: [Groq structured outputs](https://console.groq.com/docs/structured-outputs)
and [Groq rate limits](https://console.groq.com/docs/rate-limits).

## Follow-up: recorded ten-persona run and public demo

The small-check limitations above are historical. A subsequent bounded Groq run
recorded ten personas over two rounds and 22 messages. Final archived analysis
`analysis_0c966db47157420b932f` preserves original simulation
`analysis_e50d61963e794cfaac38` events, persona IDs and stances: seven conditional,
one opposed and two undecided. Four AI specialist reviews completed through
continuations: Market/Finance were inherited; Legal/Compliance and Risk were
new. The frozen discussion was not regenerated. Discussion quality remains
partial because six messages are very similar and one question is unanswered;
completed reviews do not remove that limitation.

Provider handling now uses bounded waits only for HTTP 429 while preserving
deadlines, a reasoning-output reserve with low effort, bounded token requests
and smaller review windows, and required structured fields with short text.
Explicit interrupted-review retry reuses only validated frozen discussion and
preserves failed-source/model/hash provenance. Relevant backend tests passed
(32). This saved run does not establish sustained account capacity or general
live model quality.

Source, saved reports and verification are under
`backend/data/demo/pepsodent-groq-10p-2r-2026-11-08/`. A sanitized public snapshot
now powers the read-only demo; see
[source, checks and public deployment](PAKAR_PUBLIC_DEMO_2026-11-08.md).
