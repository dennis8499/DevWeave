# Active ExecPlans

Each active run has exactly one strict schema-v2 JSON ExecPlan in this directory after cutover. The plan owns approved intent, immutable tasks, risk, Gates, decisions, verification plan, and current revision. Agents discover active runs through `inspect` or `run_inspect`; they do not infer state from filenames or edit JSON directly.

Ignored runtime data may reference a plan by run ID, but cannot supersede it.
