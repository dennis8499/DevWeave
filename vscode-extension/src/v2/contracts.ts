export const DEVWEAVE_VERSION = "2.0.0" as const;
export const DEVWEAVE_SCHEMA_VERSION = 2 as const;

export type RiskLevel = "low" | "standard" | "high";
export type RunStatus =
  | "awaiting_gate"
  | "implementing"
  | "verifying"
  | "reviewing"
  | "awaiting_acceptance"
  | "blocked"
  | "cancelled"
  | "completed";

export interface RunSnapshot {
  schema_version: 2;
  run_id: string;
  revision: number;
  status: RunStatus;
  phase: string;
  risk: RiskLevel;
  base_branch: string;
  base_ref: string;
  run_branch: string;
  required_gates: string[];
  gates: Array<{ gate_id: string; status: string; fingerprint: string; approved_revision: number }>;
  tasks: Array<{ task_id: string; status: "pending" | "in_progress" | "blocked" | "completed" }>;
  pending_decision_id: string;
  verification_status: string;
  review_status: string;
  thread_status: string;
  turn_status: string;
  blockers: string[];
  created_at: string;
  updated_at: string;
}

export interface PendingDecision {
  schema_version: 2;
  decision_id: string;
  run_id: string;
  question: string;
  options: Array<{ option_id: string; label: string; description: string }>;
  recommended_option_id: string;
  allow_other: boolean;
  blocking_task_id: string;
  created_revision: number;
  status: "pending" | "resolved";
  answer: string;
}

export interface ReviewFinding {
  schema_version: 2;
  finding_id: string;
  severity: "advisory" | "warning" | "critical";
  summary: string;
  paths: string[];
  requirement_ids: string[];
  acceptance_ids: string[];
  task_ids: string[];
  status: "open" | "resolved" | "accepted";
  round: 1 | 2 | 3;
}
