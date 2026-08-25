# Completed ExecPlans

Accepted runs move to this directory as immutable, reviewable schema-v2 JSON. Completion records remain compact; detailed logs and transient app-server state are not promoted into repository history.

The 2.0.0 finalizer workflow records the closed transition through its release-only projector, then hash-binds and retains that cutover ExecPlan alongside deterministic V1 export provenance. Finalizer apply is blocked while this strict completed record is missing, invalid, or changed after manifest preparation.
