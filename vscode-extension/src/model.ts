export type RiskLevel = "low" | "standard" | "high";
export type WorkKind = "new" | "feature" | "refactor" | "bug";
export type GateName = "scope" | "build" | "acceptance";
export type GateStatus = "pending" | "approved" | "stale";
export type Phase =
  | "requirements"
  | "scope_review"
  | "design"
  | "build_review"
  | "implementation"
  | "verification"
  | "acceptance_review"
  | "closed";

export interface GateProjection {
  status: GateStatus | string;
  fingerprint?: string | null;
  approvedBy?: string | null;
  approvedAt?: string | null;
}

export interface TaskProjection {
  id: string;
  status: string;
  startedAt?: string | null;
  completedAt?: string | null;
  evidence: string[];
  note: string;
}

export interface EvidenceProjection {
  id: string;
  kind: string;
  status: string;
  summary: string;
  covers: string[];
  tasks: string[];
  observedResult?: string;
  commandId?: string | null;
  exitCode?: number | null;
  rawLog?: string | null;
  stale: boolean;
  bindsCurrentSource: boolean;
  sourceFingerprint?: string;
}

export interface WaiverProjection {
  kind: string;
  target: string;
  reason: string;
  gate?: string;
  actor?: string;
  createdAt?: string;
}

export interface ArtifactProjection {
  path: string;
  exists: boolean;
  text: string;
  truncated: boolean;
}

export interface WikiPageProjection {
  path: string;
  title: string;
  type: string;
  status: string;
  sources: string[];
  sourceFingerprint?: string;
  computedSourceFingerprint?: string;
  parseErrors: string[];
  bodyPreview: string;
}

export interface KnowledgeProjection {
  root: string;
  health: string;
  pages: WikiPageProjection[];
  placeholderPages: string[];
  stalePages: string[];
  critical: Diagnostic[];
  warnings: Diagnostic[];
  affectedPages: string[];
  pendingRefresh: string[];
  planned?: Record<string, unknown> | null;
}

export interface Diagnostic {
  severity: "info" | "warning" | "critical";
  code: string;
  message: string;
  path?: string;
}

export interface WorkItemProjection {
  id: string;
  title: string;
  kind: string;
  status: string;
  phase: string;
  risk: string;
  gates: Record<GateName, GateProjection>;
  scope: string[];
  scopeRationale: string;
  baselineTargets: string[];
  baselineRationale: string;
  tasks: TaskProjection[];
  evidence: EvidenceProjection[];
  waivers: WaiverProjection[];
  artifacts: ArtifactProjection[];
  events: string[];
  blocker: { task?: string; reason?: string; at?: string } | null;
  staleEvidence: string[];
  readOnly: boolean;
  updatedAt?: string;
  knowledge: KnowledgeProjection;
}

export interface CommandProjection {
  id: string;
  argv: string[];
  cwd: string;
  timeoutSeconds: number;
  requiredFor: string[];
}

export interface WorkspaceSnapshot {
  capturedAt: string;
  rootName: string | null;
  rootPath: string | null;
  projectPath: string;
  projectExists: boolean;
  managed: boolean | null;
  schemaVersion: number | null;
  project: Record<string, unknown> | null;
  commands: CommandProjection[];
  verificationProfiles: Record<string, string[]>;
  baselineFiles: string[];
  hookPresent: boolean;
  skillPresent: boolean;
  workItems: WorkItemProjection[];
  knowledge: KnowledgeProjection;
  diagnostics: Diagnostic[];
  mutationBlocked: boolean;
  source: "filesystem";
  authoritative: false;
  engineObservedAt: string | null;
  selectedWorkId: string | null;
}

export type PublicCommandName = "new" | "feature" | "refactor" | "bug" | "next" | "status" | "revise" | "approve";

export type PublicCommandIntent =
  | { type: "new"; goal: string }
  | { type: "feature"; request: string }
  | { type: "refactor"; request: string }
  | { type: "bug"; symptom: string }
  | { type: "next"; workId?: string }
  | { type: "status"; workId?: string }
  | { type: "revise"; workId: string; change: string }
  | { type: "approve"; workId: string };

// Keep the established name as a public-only compatibility alias for callers inside the extension.
export type ActionIntent = PublicCommandIntent;

export interface PromptBundle {
  chatText: string;
  command: PublicCommandName;
  workId?: string;
  warnings: string[];
  mutation: boolean;
}
