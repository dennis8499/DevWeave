# Generated references

Files in this directory are derived, reviewable references rather than independent product truth.

- `public-schema-catalog.json` is compared with the Python public schema registry by `devweave check`.
- [`v1-export.json`](v1-export.json) and [`v1-export.md`](v1-export.md) are the byte-stable, read-only index of the recorded V1 base ref: 21 closed work items and 411 evidence files. Raw payload remains recoverable from Git history.
- `v2-cutover-manifest.json` is a generated exact path/SHA-256 allowlist. It is safe to apply only when its displayed manifest hash is the explicitly approved hash.

Regenerate the V1 index with public `export-v1`. Regenerate the cutover manifest with the release-only `devweave_v2_finalize.py prepare` command after every authorized legacy state change; `check` must report `ready` before G3 application.

Do not hand-edit a generated file to silence drift. Change its canonical schema/source, regenerate it, and rerun the checker.
