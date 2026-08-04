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
  verifiedBy?: string;
  parseErrors: string[];
  bodyPreview: string;
}

export interface KnowledgeBootstrapProjection {
  complete: boolean;
  recommended: boolean;
  reasons: string[];
  overview: string | null;
  architecturePages: string[];
  modulePages: string[];
}

export interface KnowledgeReviewProjection {
  required: boolean;
  current: boolean;
  disposition: "promote" | "no-update" | null;
  rationale: string;
  affectedPages: string[];
  coveredChangedPaths: string[];
  uncoveredChangedPaths: string[];
  changeFingerprint: string | null;
  recordedAt: string | null;
  invalidatedAt: string | null;
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
  coveredChangedPaths: string[];
  uncoveredChangedPaths: string[];
  bootstrap: KnowledgeBootstrapProjection;
  review: KnowledgeReviewProjection;
  planned?: Record<string, unknown> | null;
}

export interface Diagnostic {
  severity: "info" | "warning" | "critical";
  code: string;
  message: string;
  path?: string;
}

export interface BootstrapCompletenessProjection {
  complete: boolean;
  expected: string[];
  missing: string[];
  conflicts: string[];
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
  knowledgeProfile?: "bootstrap";
  knowledgeReviewRequired: boolean;
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
  bootstrap: BootstrapCompletenessProjection;
  workItems: WorkItemProjection[];
  knowledge: KnowledgeProjection;
  diagnostics: Diagnostic[];
  mutationBlocked: boolean;
  source: "filesystem";
  authoritative: false;
  engineObservedAt: string | null;
  selectedWorkId: string | null;
}

export type PublicCommandName = "new" | "feature" | "refactor" | "bug" | "next" | "status" | "revise" | "approve" | "wikiBootstrap";

export type DashboardSection = "overview" | "work" | "knowledge" | "verification" | "help";
export type DisplayMode = "concise" | "advanced";

export interface DashboardPreferences {
  displayMode: DisplayMode;
}

export type CommandGroup = "start" | "progress" | "review" | "knowledge";

export interface CommandPresentation {
  name: PublicCommandName;
  group: CommandGroup;
  label: string;
  technicalLabel: string;
  description: string;
  requiresWork: boolean;
  mutation: boolean;
}

export type SnapshotGuidanceKind = "initialize" | "setup" | "start" | "select" | "next" | "blocker" | "review" | "closed";

export interface SnapshotGuidance {
  kind: SnapshotGuidanceKind;
  title: string;
  detail: string;
  command?: PublicCommandName;
  workId?: string;
  authoritative: false;
}

export interface ReviewCheck {
  key: string;
  label: string;
  ok: boolean;
  detail: string;
  nextStep?: string;
}

export type ReviewReadinessStatus = "ready" | "attention" | "not_ready" | "closed";

export interface ReviewReadiness {
  gate: GateName | null;
  status: ReviewReadinessStatus;
  summary: string;
  checks: ReviewCheck[];
}

export interface DiagnosticPresentation {
  severity: Diagnostic["severity"];
  title: string;
  detail: string;
  resolution: string;
  code: string;
  path?: string;
}

export interface AuditEventPresentation {
  at: string;
  event: string;
  summary: string;
  raw: string;
}

export type PublicCommandIntent =
  | { type: "new"; goal: string }
  | { type: "feature"; request: string }
  | { type: "refactor"; request: string }
  | { type: "bug"; symptom: string }
  | { type: "next"; workId?: string }
  | { type: "status"; workId?: string }
  | { type: "wikiBootstrap" }
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
