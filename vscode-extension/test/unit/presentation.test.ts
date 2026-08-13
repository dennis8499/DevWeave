import assert from "node:assert/strict";
import test from "node:test";
import {
  buildReviewReadiness,
  buildSnapshotGuidance,
  commandPresentations,
  presentAuditEvent,
  presentStatus,
  presentDiagnostic
} from "../../src/presentation";
import type { Diagnostic, KnowledgeProjection, WorkItemProjection, WorkspaceSnapshot } from "../../src/model";
import { parseWebviewMessage } from "../../src/protocol";

function knowledge(): KnowledgeProjection {
  return {
    root: "wiki",
    health: "healthy",
    pages: [],
    placeholderPages: [],
    stalePages: [],
    critical: [],
    warnings: [],
    affectedPages: [],
    pendingRefresh: [],
    coveredChangedPaths: [],
    uncoveredChangedPaths: [],
    bootstrap: {
      complete: true,
      recommended: false,
      reasons: [],
      overview: "wiki/overview.md",
      architecturePages: ["wiki/architecture/system.md"],
      modulePages: ["wiki/modules/runtime.md"]
    },
    review: {
      required: false,
      current: false,
      disposition: null,
      rationale: "",
      affectedPages: [],
      coveredChangedPaths: [],
      uncoveredChangedPaths: [],
      changeFingerprint: null,
      recordedAt: null,
      invalidatedAt: null
    },
    planned: null
  };
}

function work(overrides: Partial<WorkItemProjection> = {}): WorkItemProjection {
  return {
    id: "work-1",
    title: "改善 Control Center",
    kind: "feature",
    status: "active",
    phase: "implementation",
    risk: "standard",
    gates: {
      scope: { status: "approved" },
      build: { status: "approved" },
      acceptance: { status: "pending" }
    },
    scope: ["vscode-extension/**"],
    scopeRationale: "UX",
    baselineTargets: [],
    baselineRationale: "",
    tasks: [{ id: "TASK-001", status: "pending", evidence: [], note: "" }],
    evidence: [],
    waivers: [],
    artifacts: [],
    events: [],
    blocker: null,
    staleEvidence: [],
    readOnly: false,
    updatedAt: "2026-08-03T01:00:00Z",
    knowledgeProfile: undefined,
    knowledgeReviewRequired: false,
    knowledge: knowledge(),
    detailLoaded: true,
    ...overrides
  };
}

function snapshot(workItems: WorkItemProjection[] = []): WorkspaceSnapshot {
  return {
    capturedAt: "2026-08-03T02:00:00Z",
    rootName: "DevWeave",
    rootPath: "file:///repo",
    projectPath: ".devweave/project.json",
    projectExists: true,
    managed: true,
    schemaVersion: 1,
    project: {},
    commands: [],
    verificationProfiles: { standard: ["unit-tests"] },
    baselineFiles: [],
    hookPresent: true,
    skillPresent: true,
    bootstrap: { complete: true, expected: [], missing: [], conflicts: [], pathKinds: {}, conflictReasons: {} },
    workItems,
    knowledge: knowledge(),
    diagnostics: [],
    mutationBlocked: false,
    source: "filesystem",
    authoritative: false,
    engineObservedAt: "2026-08-03T01:00:00Z",
    engineGateStatus: "unavailable",
    projectionReadiness: "ready",
    selectedWorkId: workItems[0]?.id ?? null
  };
}

test("command catalog groups all nine public commands in task language", () => {
  const catalog = commandPresentations();

  assert.deepEqual(
    catalog.map((item) => item.name),
    ["new", "feature", "refactor", "bug", "next", "status", "revise", "approve", "wikiBootstrap"]
  );
  assert.deepEqual([...new Set(catalog.map((item) => item.group))], ["start", "progress", "review", "knowledge"]);
  assert.ok(catalog.every((item) => item.label.length > 0 && item.description.length > 0 && item.technicalLabel.length > 0));
  assert.equal(catalog.find((item) => item.name === "approve")?.requiresWork, true);
  assert.equal(catalog.find((item) => item.name === "status")?.mutation, false);
});

test("snapshot guidance is explicitly non-authoritative and hands off next to Codex", () => {
  const current = work();
  const guidance = buildSnapshotGuidance(snapshot([current]), current);

  assert.equal(guidance.authoritative, false);
  assert.equal(guidance.command, "next");
  assert.equal(guidance.workId, current.id);
  assert.match(guidance.title, /快照|下一步/);
  assert.match(guidance.detail, /Codex Chat|Refresh/);
});

test("snapshot guidance handles an empty active-work state without selecting closed history", () => {
  const closed = work({ id: "closed-1", status: "closed", phase: "closed" });
  const guidance = buildSnapshotGuidance(snapshot([closed]), null);

  assert.equal(guidance.authoritative, false);
  assert.equal(guidance.command, "new");
  assert.equal(guidance.workId, undefined);
  assert.deepEqual(guidance.planModeGuidance, { required: true, stage: "initial" });
  assert.match(guidance.detail, /active|新工作|new/i);
});

test("snapshot guidance marks G1 and G2 work with a required Plan Mode stage", () => {
  const g1 = work({ phase: "requirements" });
  const g2 = work({ phase: "design" });

  assert.deepEqual(buildSnapshotGuidance(snapshot([g1]), g1).planModeGuidance, { required: true, stage: "g1" });
  assert.deepEqual(buildSnapshotGuidance(snapshot([g2]), g2).planModeGuidance, { required: true, stage: "g2" });
});

test("snapshot guidance does not block post-G2 work with an initial Plan Mode prompt", () => {
  const current = work({ phase: "implementation" });
  const guidance = buildSnapshotGuidance(snapshot([current]), current);

  assert.equal(guidance.kind, "next");
  assert.deepEqual(guidance.planModeGuidance, { required: false, stage: "post-g2" });
  assert.match(guidance.detail, /Codex Chat|Refresh/);
});

test("snapshot guidance makes initialization and bootstrap write boundary explicit", () => {
  const uninitialized = snapshot([]);
  uninitialized.projectExists = false;
  uninitialized.managed = null;
  const guidance = buildSnapshotGuidance(uninitialized, null);

  assert.equal(guidance.kind, "initialize");
  assert.equal(guidance.command, undefined);
  assert.match(guidance.detail, /固定 bootstrap|寫入/);
  assert.equal(guidance.authoritative, false);
});

test("review readiness explains gate, blocker, stale evidence, task and Wiki checks", () => {
  const current = work({
    phase: "acceptance_review",
    blocker: { task: "TASK-002", reason: "Verification failed" },
    staleEvidence: ["evidence-stale"],
    tasks: [{ id: "TASK-001", status: "pending", evidence: [], note: "尚未完成" }],
    evidence: [{
      id: "evidence-stale",
      kind: "test",
      status: "passed",
      summary: "old",
      covers: [],
      tasks: [],
      stale: true,
      bindsCurrentSource: false
    }],
    knowledge: {
      ...knowledge(),
      pendingRefresh: ["wiki/modules/runtime.md"]
    }
  });
  const readiness = buildReviewReadiness(snapshot([current]), current);

  assert.equal(readiness.gate, "acceptance");
  assert.equal(readiness.status, "not_ready");
  assert.match(readiness.summary, /不能|待處理|未就緒/);
  assert.ok(readiness.checks.some((check) => /blocker/i.test(check.key)));
  assert.ok(readiness.checks.some((check) => /evidence/i.test(check.key)));
  assert.ok(readiness.checks.some((check) => /task/i.test(check.key)));
  assert.ok(readiness.checks.some((check) => /knowledge|wiki/i.test(check.key)));
});

test("review readiness can be ready for a pending gate without pretending the gate is approved", () => {
  const current = work({
    phase: "scope_review",
    gates: {
      scope: { status: "pending" },
      build: { status: "pending" },
      acceptance: { status: "pending" }
    },
    tasks: [],
    evidence: []
  });
  const readiness = buildReviewReadiness(snapshot([current]), current);

  assert.equal(readiness.gate, "scope");
  assert.equal(readiness.status, "ready");
  assert.ok(readiness.checks.find((check) => check.key === "gate")?.detail.includes("等待 reviewer"));
});

test("high-risk acceptance readiness projects independent review states", () => {
  const base = work({
    risk: "high",
    phase: "acceptance_review",
    tasks: [{ id: "TASK-001", status: "completed", evidence: ["EVID-001"], note: "done" }],
    evidence: [{
      id: "EVID-001",
      kind: "acceptance",
      status: "passed",
      summary: "acceptance",
      covers: ["AC-001"],
      tasks: ["TASK-001"],
      stale: false,
      bindsCurrentSource: true
    }]
  });
  const missing = buildReviewReadiness(snapshot([base]), base);
  assert.equal(missing.status, "attention");
  assert.equal(missing.checks.find((check) => check.key === "independent-review")?.level, "warning");

  const passed = {
    ...base,
    evidence: [...base.evidence, {
      id: "EVID-002",
      kind: "review",
      status: "passed",
      summary: "review passed",
      covers: ["AC-001"],
      tasks: ["TASK-001"],
      stale: false,
      bindsCurrentSource: true,
      review: {
        result: "passed" as const,
        severity: "none" as const,
        reviewerId: "opaque-agent",
        contextMode: "isolated_read_only",
        reportSha256: "hash",
        findings: [],
        covers: ["AC-001"],
        tasks: ["TASK-001"]
      }
    }]
  };
  const passedReadiness = buildReviewReadiness(snapshot([passed]), passed);
  assert.equal(passedReadiness.status, "ready");
  assert.equal(passedReadiness.checks.find((check) => check.key === "independent-review")?.ok, true);

  for (const severity of ["advisory", "unavailable"] as const) {
    const attention = {
      ...passed,
      evidence: passed.evidence.map((item) => item.kind === "review" ? {
        ...item,
        review: { ...item.review!, result: severity === "advisory" ? "passed" as const : "unavailable" as const, severity: severity === "advisory" ? "advisory" as const : "none" as const }
      } : item)
    };
    const readiness = buildReviewReadiness(snapshot([attention]), attention);
    assert.equal(readiness.status, "attention");
    assert.equal(readiness.checks.find((check) => check.key === "independent-review")?.level, "warning");
  }

  const critical = {
    ...passed,
    evidence: passed.evidence.map((item) => item.kind === "review" ? {
      ...item,
      status: "failed",
      review: { ...item.review!, result: "critical" as const, severity: "critical" as const, findings: [{ id: "F-001", severity: "critical" as const, title: "risk", evidence: "data loss", recommendation: "fix" }] }
    } : item)
  };
  const criticalReadiness = buildReviewReadiness(snapshot([critical]), critical);
  assert.equal(criticalReadiness.status, "not_ready");
  assert.equal(criticalReadiness.checks.find((check) => check.key === "independent-review")?.level, "critical");
});

test("closed work is explicitly not reviewable", () => {
  const current = work({ status: "closed", phase: "closed" });
  const readiness = buildReviewReadiness(snapshot([current]), current);

  assert.equal(readiness.status, "closed");
  assert.equal(readiness.gate, null);
});

test("diagnostics and audit events become readable while preserving technical raw data", () => {
  const diagnostic: Diagnostic = {
    severity: "critical",
    code: "project_invalid",
    message: "Project JSON is invalid.",
    path: ".devweave/project.json"
  };
  const rendered = presentDiagnostic(diagnostic);
  assert.match(rendered.title, /設定|project/i);
  assert.match(rendered.resolution, /修正|Codex|確認/);
  assert.equal(rendered.code, diagnostic.code);
  assert.equal(rendered.path, diagnostic.path);

  const event = presentAuditEvent('{"at":"2026-08-03T02:00:00Z","event":"gate.approved","work":"work-1"}');
  assert.equal(event.at, "2026-08-03T02:00:00Z");
  assert.match(event.summary, /核准|approved|gate/i);
  assert.equal(event.raw, '{"at":"2026-08-03T02:00:00Z","event":"gate.approved","work":"work-1"}');

  const malformed = presentAuditEvent("not json");
  assert.equal(malformed.raw, "not json");
  assert.match(malformed.summary, /事件|格式|讀取/);
});

test("display mode protocol accepts only the typed preference message", () => {
  assert.deepEqual(parseWebviewMessage({ type: "setDisplayMode", mode: "advanced" }), {
    type: "setDisplayMode",
    mode: "advanced"
  });
  assert.equal(parseWebviewMessage({ type: "setDisplayMode", mode: "compact" }), null);
  assert.equal(parseWebviewMessage({ type: "setDisplayMode", mode: "concise", extra: true }), null);
});

test("readiness and bootstrap statuses are presented in Traditional Chinese", () => {
  assert.equal(presentStatus("ready"), "可進一步審查");
  assert.equal(presentStatus("not_ready"), "尚未就緒");
  assert.equal(presentStatus("attention"), "需要注意");
  assert.equal(presentStatus("initialized"), "已完成初始化");
});
