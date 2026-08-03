import assert from "node:assert/strict";
import test from "node:test";
import { FileSystemPort, DirectoryEntry } from "../../src/filesystem";
import { PublicCommandIntent, WorkspaceSnapshot } from "../../src/model";
import { DevWeavePromptComposer } from "../../src/prompt";
import { parsePublicCommandIntent, parseWebviewMessage } from "../../src/protocol";
import { WorkspaceSnapshotReader } from "../../src/snapshot";

class MemoryFileSystem implements FileSystemPort {
  private readonly files = new Map<string, string>();

  public constructor(entries: Record<string, string>) {
    for (const [path, text] of Object.entries(entries)) {
      this.files.set(this.normalize(path), text);
    }
  }

  public async exists(relativePath: string): Promise<boolean> {
    const path = this.normalize(relativePath);
    return path === "." || this.files.has(path) || [...this.files.keys()].some((file) => file.startsWith(path + "/"));
  }

  public async readText(relativePath: string, maxBytes = 1_000_000): Promise<{ text: string; truncated: boolean }> {
    const value = this.files.get(this.normalize(relativePath));
    if (value === undefined) {
      throw new Error("Missing file: " + relativePath);
    }
    const truncated = Buffer.byteLength(value, "utf8") > maxBytes;
    return { text: truncated ? value.slice(0, maxBytes) : value, truncated };
  }

  public async readDirectory(relativePath: string): Promise<DirectoryEntry[]> {
    const parent = this.normalize(relativePath);
    const prefix = parent === "." ? "" : parent + "/";
    const entries = new Map<string, DirectoryEntry>();
    for (const file of this.files.keys()) {
      if (!file.startsWith(prefix)) {
        continue;
      }
      const remainder = file.slice(prefix.length);
      if (!remainder) {
        continue;
      }
      const [name, ...rest] = remainder.split("/");
      entries.set(name, { name, kind: rest.length > 0 ? "directory" : "file" });
    }
    return [...entries.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  private normalize(value: string): string {
    const normalized = value.replaceAll("\\", "/").replace(/^\.\//, "").replace(/\/$/, "");
    return normalized || ".";
  }
}

function managedEntries(): Record<string, string> {
  return {
    ".devweave/project.json": JSON.stringify({
      managed: true,
      schema_version: 1,
      commands: [{
        id: "unit-tests",
        argv: ["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd: ".",
        required_for: ["high", "low", "standard"],
        timeout_seconds: 240
      }],
      verification_profiles: { high: ["unit-tests"], standard: ["unit-tests"], low: ["unit-tests"] }
    }),
    ".codex/hooks.json": "{}",
    ".agents/skills/devweave/SKILL.md": "# DevWeave",
    ".devweave/baseline/architecture.json": "{}",
    ".devweave/work-items/demo/state.json": JSON.stringify({
      schema_version: 1,
      id: "demo",
      title: "Demo work",
      kind: "feature",
      status: "active",
      phase: "implementation",
      risk: { level: "high" },
      scope: { paths: ["vscode-extension/**"], rationale: "test" },
      gates: { scope: { status: "approved" }, build: { status: "approved" }, acceptance: { status: "pending" } },
      tasks: { "TASK-001": { status: "completed", evidence: ["evidence-1"] } },
      updated_at: "2026-08-03T01:00:00Z"
    }),
    ".devweave/work-items/demo/brief.md": "# Demo",
    ".devweave/work-items/demo/evidence/evidence-1.json": JSON.stringify({
      id: "evidence-1",
      kind: "test",
      status: "passed",
      summary: "passed",
      stale: true,
      binds_current_source: true
    }),
    "wiki/index.md": "---\ntitle: Wiki index\ntype: architecture\nstatus: active\nsources: []\n---\n# Index",
    "wiki/overview.md": "---\ntitle: Overview\ntype: synthesis\nstatus: placeholder\nsources: []\n---\n# Placeholder"
  };
}

function snapshotFixture(): WorkspaceSnapshot {
  return {
    capturedAt: "2026-08-03T01:00:00Z",
    rootName: "fixture",
    rootPath: "file:///fixture",
    projectPath: ".devweave/project.json",
    projectExists: true,
    managed: true,
    schemaVersion: 1,
    project: {},
    commands: [],
    verificationProfiles: {},
    baselineFiles: [],
    hookPresent: true,
    skillPresent: true,
    workItems: [],
    knowledge: { root: "wiki", health: "healthy", pages: [], placeholderPages: [], stalePages: [], critical: [], warnings: [], affectedPages: [], pendingRefresh: [], planned: null },
    diagnostics: [],
    mutationBlocked: false,
    source: "filesystem",
    authoritative: false,
    engineObservedAt: null,
    selectedWorkId: null
  };
}

test("snapshot reader projects array commands, placeholder Wiki, work state, and stale evidence", async () => {
  const reader = new WorkspaceSnapshotReader(new MemoryFileSystem(managedEntries()), {
    rootName: "fixture",
    rootPath: "file:///fixture",
    now: () => "2026-08-03T01:00:00Z"
  });
  const snapshot = await reader.readWorkspace();

  assert.equal(snapshot.projectExists, true);
  assert.equal(snapshot.managed, true);
  assert.equal(snapshot.commands[0]?.id, "unit-tests");
  assert.deepEqual(snapshot.commands[0]?.argv.slice(0, 3), ["python", "-B", "-m"]);
  assert.deepEqual(snapshot.workItems[0]?.staleEvidence, ["evidence-1"]);
  assert.deepEqual(snapshot.knowledge.placeholderPages, ["wiki/overview.md"]);
  assert.equal(snapshot.knowledge.health, "warning");
  assert.equal(snapshot.diagnostics.some((item) => item.code === "project_invalid"), false);
});

test("snapshot reader reports an uninitialized workspace without invoking an engine", async () => {
  const reader = new WorkspaceSnapshotReader(new MemoryFileSystem({ "wiki/index.md": "placeholder" }), {
    rootName: "empty",
    rootPath: "file:///empty",
    now: () => "2026-08-03T01:00:00Z"
  });
  const snapshot = await reader.readWorkspace();

  assert.equal(snapshot.projectExists, false);
  assert.equal(snapshot.managed, null);
  assert.ok(snapshot.diagnostics.some((item) => item.code === "project_missing"));
  assert.deepEqual(snapshot.workItems, []);
});

test("snapshot reader keeps managed false explicit and preserves multiple active/closed work items", async () => {
  const entries = managedEntries();
  entries[".devweave/project.json"] = JSON.stringify({ managed: false, schema_version: 1, commands: [] });
  entries[".devweave/work-items/closed/state.json"] = JSON.stringify({
    schema_version: 1,
    id: "closed",
    title: "Closed work",
    kind: "feature",
    status: "closed",
    phase: "closed",
    risk: { level: "low" },
    gates: {},
    tasks: {},
    updated_at: "2026-08-03T02:00:00Z"
  });
  const reader = new WorkspaceSnapshotReader(new MemoryFileSystem(entries), {
    rootName: "managed-false",
    rootPath: "file:///managed-false",
    now: () => "2026-08-03T02:00:00Z"
  });
  const snapshot = await reader.readWorkspace();

  assert.equal(snapshot.managed, false);
  assert.ok(snapshot.diagnostics.some((item) => item.code === "managed_disabled"));
  assert.equal(snapshot.workItems.length, 2);
  assert.ok(snapshot.workItems.some((item) => item.status === "closed"));
  assert.ok(snapshot.diagnostics.some((item) => item.code === "legacy_work"));
});

test("snapshot reader fails closed for malformed and unsupported project/state", async () => {
  const malformed = managedEntries();
  malformed[".devweave/project.json"] = "{";
  const malformedSnapshot = await new WorkspaceSnapshotReader(new MemoryFileSystem(malformed), {
    rootName: "malformed",
    rootPath: "file:///malformed"
  }).readWorkspace();
  assert.equal(malformedSnapshot.mutationBlocked, true);
  assert.ok(malformedSnapshot.diagnostics.some((item) => item.code === "json_parse"));

  const unsupported = managedEntries();
  unsupported[".devweave/project.json"] = JSON.stringify({ managed: true, schema_version: 99, commands: [] });
  unsupported[".devweave/work-items/demo/state.json"] = JSON.stringify({ schema_version: 99, id: "demo", status: "active", phase: "implementation" });
  const unsupportedSnapshot = await new WorkspaceSnapshotReader(new MemoryFileSystem(unsupported), {
    rootName: "unsupported",
    rootPath: "file:///unsupported"
  }).readWorkspace();
  assert.equal(unsupportedSnapshot.mutationBlocked, true);
  assert.ok(unsupportedSnapshot.diagnostics.some((item) => item.code === "unsupported_schema"));
  assert.ok(unsupportedSnapshot.diagnostics.some((item) => item.code === "work_unsupported_schema"));
  assert.equal(unsupportedSnapshot.workItems[0]?.readOnly, true);
});

test("snapshot reader marks stale Wiki metadata and missing hook without rebuilding fingerprints", async () => {
  const entries = managedEntries();
  delete entries[".codex/hooks.json"];
  entries["wiki/stale.md"] = "---\ntitle: Stale\ntype: modules\nstatus: active\nsource_fingerprint: old\ncomputed_source_fingerprint: new\nsources: []\n---\n# Stale";
  const snapshot = await new WorkspaceSnapshotReader(new MemoryFileSystem(entries), {
    rootName: "stale",
    rootPath: "file:///stale"
  }).readWorkspace();

  assert.ok(snapshot.diagnostics.some((item) => item.code === "hook_missing"));
  assert.deepEqual(snapshot.knowledge.stalePages, ["wiki/stale.md"]);
  assert.equal(snapshot.knowledge.pages.find((page) => page.path === "wiki/stale.md")?.computedSourceFingerprint, "new");
});

test("public prompt composition is deterministic, sanitized, and machine-command free", () => {
  const composer = new DevWeavePromptComposer();
  const snapshot = snapshotFixture();
  const intent: PublicCommandIntent = {
    type: "feature",
    request: "Review C:\\Users\\owner\\repo; ghp_1234567890123456"
  };
  const first = composer.compose(intent, snapshot);
  const second = composer.compose(intent, snapshot);

  assert.deepEqual(first, second);
  assert.equal(first.command, "feature");
  assert.equal(first.chatText.startsWith("$devweave feature "), true);
  assert.equal(first.mutation, true);
  assert.equal("machineCommand" in first, false);
  assert.equal("targetPaths" in first, false);
  assert.equal("gate" in first, false);
  assert.equal(first.chatText.includes("C:\\"), false);
  assert.equal(first.chatText.includes("|"), false);
  assert.equal(first.chatText.includes("ghp_1234567890123456"), false);
});

test("prompt composer redacts absolute paths and credential-like values", () => {
  const composer = new DevWeavePromptComposer();
  const bundle = composer.compose({
    type: "bug",
    symptom: "Review C:\\Users\\owner\\repo; ghp_1234567890123456"
  }, snapshotFixture());

  assert.equal(bundle.chatText.includes("C:\\Users"), false);
  assert.equal(bundle.chatText.includes("ghp_1234567890123456"), false);
  assert.ok(bundle.warnings.some((warning) => warning.includes("absolute")));
  assert.ok(bundle.warnings.some((warning) => warning.includes("credential")));
});

test("mutation public prompt is disabled when the snapshot has a critical diagnostic", () => {
  const composer = new DevWeavePromptComposer();
  const snapshot = { ...snapshotFixture(), mutationBlocked: true, diagnostics: [{ severity: "critical" as const, code: "json_parse", message: "invalid" }] };
  assert.throws(() => composer.compose({ type: "feature", request: "Feature" }, snapshot), /read-only diagnostic state/);
  assert.equal(composer.compose({ type: "status" }, snapshot).chatText, "$devweave status");
});

test("every public command produces the documented command text", () => {
  const composer = new DevWeavePromptComposer();
  const snapshot = snapshotFixture();
  const cases: Array<[PublicCommandIntent, string, boolean]> = [
    [{ type: "new", goal: "建立第一個切片" }, "$devweave new 建立第一個切片", true],
    [{ type: "feature", request: "新增 CSV 匯出" }, "$devweave feature 新增 CSV 匯出", true],
    [{ type: "refactor", request: "整理 prompt seam" }, "$devweave refactor 整理 prompt seam", true],
    [{ type: "bug", symptom: "初始化失敗" }, "$devweave bug 初始化失敗", true],
    [{ type: "next", workId: "demo" }, "$devweave next demo", false],
    [{ type: "next" }, "$devweave next", false],
    [{ type: "status", workId: "demo" }, "$devweave status demo", false],
    [{ type: "status" }, "$devweave status", false],
    [{ type: "revise", workId: "demo", change: "調整公開命令欄位" }, "$devweave revise demo 調整公開命令欄位", true],
    [{ type: "approve", workId: "demo" }, "$devweave approve demo", true]
  ];

  for (const [intent, expected, mutation] of cases) {
    const bundle = composer.compose(intent, snapshot);
    assert.equal(bundle.chatText, expected, intent.type);
    assert.equal(bundle.command, intent.type, intent.type);
    assert.equal(bundle.mutation, mutation, intent.type);
    assert.equal(bundle.chatText.includes("python"), false, intent.type);
    assert.equal(bundle.chatText.includes("--repo"), false, intent.type);
    assert.equal(bundle.chatText.includes("gate"), false, intent.type);
  }
});

test("public Webview protocol accepts public intents and rejects machine actions", () => {
  const action: PublicCommandIntent = { type: "approve", workId: "demo" };
  assert.deepEqual(parsePublicCommandIntent(action), action);
  assert.deepEqual(parsePublicCommandIntent({ type: "next" }), { type: "next" });
  assert.deepEqual(parsePublicCommandIntent({ type: "next", workId: "demo" }), { type: "next", workId: "demo" });
  assert.deepEqual(parsePublicCommandIntent({ type: "status" }), { type: "status" });
  assert.deepEqual(parsePublicCommandIntent({ type: "status", workId: "demo" }), { type: "status", workId: "demo" });
  assert.equal(parsePublicCommandIntent({ type: "feature", request: "   " }), null);
  assert.equal(parsePublicCommandIntent({ type: "bug", symptom: "" }), null);
  assert.equal(parsePublicCommandIntent({ type: "revise", workId: "", change: "change" }), null);
  assert.equal(parsePublicCommandIntent({ type: "revise", workId: "demo", change: "   " }), null);
  assert.equal(parsePublicCommandIntent({ type: "approve" }), null);
  assert.deepEqual(parseWebviewMessage({ type: "copyAction", intent: action }), { type: "copyAction", intent: action });
  assert.deepEqual(parseWebviewMessage({ type: "selectWork", workId: null }), { type: "selectWork", workId: null });
  assert.deepEqual(parseWebviewMessage({ type: "refresh" }), { type: "refresh" });
  assert.deepEqual(parseWebviewMessage({ type: "initialize" }), { type: "initialize" });
  assert.equal(parseWebviewMessage({ type: "initialize", unexpected: true }), null);
  assert.equal(parseWebviewMessage({ type: "refresh", unexpected: true }), null);
  assert.equal(parseWebviewMessage({ type: "copyAction", intent: { type: "approve" } }), null);
  assert.equal(parseWebviewMessage({ type: "executeCommand", command: "python" }), null);
  assert.equal(parsePublicCommandIntent({ type: "doctor" }), null);
  assert.equal(parsePublicCommandIntent({ type: "commandSet", id: "x" }), null);
  assert.equal(parsePublicCommandIntent({ type: "taskStart", workId: "demo" }), null);
  assert.equal(parsePublicCommandIntent({ type: "knowledgePlan", workId: "demo" }), null);
  assert.equal(parsePublicCommandIntent({ type: "close", workId: "demo" }), null);
  assert.equal(parsePublicCommandIntent({ type: "revise", workId: "demo" }), null);
  assert.equal(parsePublicCommandIntent({ type: "approve", workId: "demo", gate: "build" }), null);
});
