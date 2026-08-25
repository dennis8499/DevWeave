<!-- canonical-topic: tech-debt -->
# Technical debt tracker

Track only structural debt that affects future agent work. Every entry needs an owner, evidence, and a concrete exit condition.

| ID | Owner | State | Evidence | Exit condition |
| --- | --- | --- | --- | --- |
| TD-001 | release owner | pre-release | Codex CLI is unavailable on the current PATH | Run the real Windows app-server/schema/UI walkthrough with recorded provenance, or explicitly block release |
| TD-002 | release owner | pre-release | V1 transition files remain until the legacy high-risk G3 | Approve G3, run the hash-bound finalizer, and pass the post-cutover repository/package checks |

Do not add an architecture exception here. Machine waivers belong only in `docs/architecture-exceptions.json` and must expire.
