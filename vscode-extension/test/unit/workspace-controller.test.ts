import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, rmSync, symlinkSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import test, { after } from "node:test";

import { initialProjection, type AppServerProjection } from "../../src/app-server/event-reducer";
import type { ServerRequest } from "../../src/app-server/session";
import { TranscriptTransport } from "../../src/app-server/transport";
import { HostBridgeClient } from "../../src/controller/host-bridge-client";
import { ReviewCoordinator } from "../../src/controller/review-coordinator";
import { WorkspaceController, type AppServerPort, type HostPort } from "../../src/controller/workspace-controller";

const TOOLS = [
  "run_inspect", "context_read", "plan_save", "decision_request", "task_update",
  "verification_run", "verification_read", "completion_request"
];
const SOURCE_FINGERPRINT = "a".repeat(64);
const TEST_ROOT = mkdtempSync(join(tmpdir(), "devweave-controller-"));
const TEST_REPOSITORY = join(TEST_ROOT, "repository");
mkdirSync(join(TEST_REPOSITORY, "src"), { recursive: true });
for (const protectedPath of [".git", ".devweave", ".codex", ".agents/skills/devweave", "docs/exec-plans"]) {
  mkdirSync(join(TEST_REPOSITORY, ...protectedPath.split("/")), { recursive: true });
}
after(() => rmSync(TEST_ROOT, { recursive: true, force: true }));

function run(phase = "planning", risk = "high", declaredPaths: string[] = ["src/**"]): Record<string, unknown> {
  return {
    run_id: "run-1", revision: 1, phase, risk, base_branch: "main", status: phase === "planning" ? "awaiting_gate" : "implementing",
    plan: { scope: ["src/**"] },
    tasks: {
      "TASK-001": {
        status: "in_progress",
        definition: { task_id: "TASK-001", declared_paths: declaredPaths }
      }
    },
    verification: {
      status: "passed", current_report_id: "verify-1",
      reports: { "verify-1": { source_digest: SOURCE_FINGERPRINT } }
    }
  };
}

class FakeHost implements HostPort {
  public readonly calls: Array<{ method: string; params: unknown }> = [];
  public currentRun = run();

  public async request(method: never, params: unknown): Promise<unknown> {
    this.calls.push({ method, params });
    if (method === "run_start" || method === "run_resume") {
      return { preflight: { codex: { path: "C:/tools/codex.exe" } }, run: this.currentRun };
    }
    this.currentRun = { ...this.currentRun, revision: Number(this.currentRun.revision) + 1 };
    return this.currentRun;
  }
}

class FakeApp implements AppServerPort {
  public projection: AppServerProjection = initialProjection();
  public readonly requests: Array<{ method: string; params: unknown }> = [];
  public readonly responses: Array<{ id: string | number; result: unknown }> = [];
  public connectCalls = 0;
  public mcpTools = [...TOOLS];
  public reviewResponses: unknown[] = [];
  public turnCompletionStatus = "interrupted";
  private projectionListener: ((state: AppServerProjection) => void) | undefined;
  private serverListener: ((request: ServerRequest) => void) | undefined;

  public async connect(): Promise<unknown> {
    this.connectCalls += 1;
    this.projection = { ...this.projection, connection: "connected" };
    this.projectionListener?.(this.projection);
    return {};
  }

  public async request(method: never, params: unknown): Promise<unknown> {
    this.requests.push({ method, params });
    if (method === "mcpServerStatus/list") {
      return { data: [{ name: "devweave", tools: Object.fromEntries(this.mcpTools.map((name) => [name, { name }])) }] };
    }
    if (method === "thread/start") return { thread: { id: "implement-thread" } };
    if (method === "thread/resume") return { thread: { id: "implement-thread" } };
    if (method === "turn/start") return { turn: { id: "turn-1" } };
    if (method === "review/start") return this.reviewResponses.shift() ?? { threadId: "review-thread", findings: [] };
    return {};
  }

  public respond(id: number | string, result: unknown): void {
    this.responses.push({ id, result });
  }

  public async waitForTurnCompleted(): Promise<unknown> {
    return { status: this.turnCompletionStatus };
  }

  public onProjection(listener: (state: AppServerProjection) => void): () => void {
    this.projectionListener = listener;
    return () => { this.projectionListener = undefined; };
  }

  public onServerRequest(listener: (request: ServerRequest) => void): () => void {
    this.serverListener = listener;
    return () => { this.serverListener = undefined; };
  }

  public emitApproval(request: ServerRequest): void {
    this.serverListener?.(request);
  }
}

test("workspace start creates a read-only thread before checking its exact required MCP", async () => {
  const host = new FakeHost();
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  const state = await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  assert.equal(state.status, "ready");
  assert.equal(state.threadId, "implement-thread");
  assert.deepEqual(app.requests.map((item) => item.method), ["thread/start", "mcpServerStatus/list"]);
  assert.deepEqual(app.requests[0].params, {
    cwd: TEST_REPOSITORY, approvalPolicy: "untrusted", approvalsReviewer: "user", sandbox: "read-only"
  });
  assert.deepEqual(app.requests[1].params, { threadId: "implement-thread", detail: "full", limit: 100 });
  assert.equal(host.calls[0].method, "run_start");
});

test("required MCP failure blocks after the thread-scoped inventory is available", async () => {
  const host = new FakeHost();
  const app = new FakeApp();
  app.mcpTools = TOOLS.slice(0, -1);
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await assert.rejects(controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" }), /tool set/);
  assert.equal(controller.state.status, "blocked");
  assert.deepEqual(app.requests.map((item) => item.method), ["thread/start", "mcpServerStatus/list"]);
});

test("implementation thread stays read-only while the turn receives exact task roots", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  assert.equal((app.requests[0].params as { sandbox: unknown }).sandbox, "read-only");
  await controller.startTurn("continue");
  assert.deepEqual(app.requests.at(-1)?.params, {
    threadId: "implement-thread",
    input: [{ type: "text", text: "continue" }],
    approvalPolicy: "untrusted",
    approvalsReviewer: "user",
    sandboxPolicy: { type: "workspaceWrite", writableRoots: [resolve(TEST_REPOSITORY, "src")], networkAccess: false }
  });
  await controller.steer("clarify");
  assert.deepEqual(app.requests.at(-1)?.params, {
    threadId: "implement-thread", expectedTurnId: "turn-1", input: [{ type: "text", text: "clarify" }]
  });
  await controller.resumeRun("run-1", undefined, "implement-thread");
  assert.equal(host.calls.at(-1)?.method, "run_resume");
  assert.deepEqual(app.requests.slice(-2).map((item) => item.method), ["thread/resume", "mcpServerStatus/list"]);
  assert.deepEqual(app.requests.at(-2)?.params, {
    threadId: "implement-thread", cwd: TEST_REPOSITORY, approvalPolicy: "untrusted",
    approvalsReviewer: "user", sandbox: "read-only"
  });
});

test("zero or multiple active tasks and non-implementation phases remain read-only", async () => {
  for (const current of [
    { ...run("implementation"), tasks: {} },
    {
      ...run("implementation"),
      tasks: {
        first: { status: "in_progress", definition: { declared_paths: ["src/**"] } },
        second: { status: "in_progress", definition: { declared_paths: ["test/**"] } }
      }
    },
    run("review")
  ]) {
    const host = new FakeHost();
    host.currentRun = current;
    const app = new FakeApp();
    const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
    await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
    await controller.startTurn("inspect");
    assert.deepEqual((app.requests.at(-1)?.params as { sandboxPolicy: unknown }).sandboxPolicy, {
      type: "readOnly", networkAccess: false
    });
  }
});

test("task write scope fails closed for widened globs, traversal, siblings, and reparse escapes", async () => {
  for (const declaredPaths of [
    ["src/foo*.ts"], ["src/*"], ["src/app.ts"], ["../src/**"],
    [".git/**"], [".devweave/**"], [".codex/**"], [".agents/**"],
    ["docs/exec-plans/**"], ["docs/**"]
  ]) {
    const host = new FakeHost();
    host.currentRun = run("implementation", "high", declaredPaths);
    const app = new FakeApp();
    const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
    await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
    await controller.startTurn("inspect");
    assert.deepEqual((app.requests.at(-1)?.params as { sandboxPolicy: unknown }).sandboxPolicy, {
      type: "readOnly", networkAccess: false
    });
    app.emitApproval({ id: declaredPaths[0], method: "item/fileChange/requestApproval", params: { path: "src/app.ts" } });
    assert.deepEqual(app.responses.at(-1)?.result, { decision: "decline" });
  }

  for (const [declaration, candidate] of [
    [".git/**", ".git/config"],
    [".devweave/**", ".devweave/runtime/authority.lock"],
    [".codex/**", ".codex/config.toml"],
    [".agents/**", ".agents/skills/devweave/scripts/host.py"],
    ["docs/exec-plans/**", "docs/exec-plans/active/run.json"],
    ["docs/**", "docs/exec-plans/active/run.json"]
  ]) {
    const host = new FakeHost();
    host.currentRun = run("implementation", "high", [declaration]);
    const app = new FakeApp();
    const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
    await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
    app.emitApproval({ id: declaration, method: "item/fileChange/requestApproval", params: { path: candidate } });
    assert.deepEqual(app.responses.at(-1)?.result, { decision: "decline" });
  }

  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  for (const path of ["src2/app.ts", "src/../outside.ts", "../src/app.ts", "src/app.ts:stream", "src/NUL.txt"]) {
    app.emitApproval({ id: path, method: "item/fileChange/requestApproval", params: { path } });
    assert.deepEqual(app.responses.at(-1)?.result, { decision: "decline" });
  }

  const outside = join(TEST_ROOT, "outside");
  mkdirSync(outside);
  const link = join(TEST_REPOSITORY, "src", "linked");
  symlinkSync(outside, link, process.platform === "win32" ? "junction" : "dir");
  app.emitApproval({ id: "reparse", method: "item/fileChange/requestApproval", params: { path: "src/linked/escape.ts" } });
  assert.deepEqual(app.responses.at(-1)?.result, { decision: "decline" });

  const linkedHost = new FakeHost();
  linkedHost.currentRun = run("implementation", "high", ["src/linked/**"]);
  const linkedApp = new FakeApp();
  const linkedController = new WorkspaceController(TEST_REPOSITORY, linkedHost, linkedApp);
  await linkedController.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  await linkedController.startTurn("inspect");
  assert.deepEqual((linkedApp.requests.at(-1)?.params as { sandboxPolicy: unknown }).sandboxPolicy, {
    type: "readOnly", networkAccess: false
  });
});

test("NTFS short-name authority aliases remain read-only and approvals are declined", {
  skip: process.platform !== "win32"
}, async () => {
  const shortRoot = join(TEST_REPOSITORY, "docs", "EXEC-P~1");
  assert.equal(existsSync(shortRoot), true, "test volume must expose the exec-plans 8.3 alias");
  const host = new FakeHost();
  host.currentRun = run("implementation", "high", ["docs/EXEC-P~1/**"]);
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  await controller.startTurn("inspect");
  assert.deepEqual((app.requests.at(-1)?.params as { sandboxPolicy: unknown }).sandboxPolicy, {
    type: "readOnly", networkAccess: false
  });
  app.emitApproval({
    id: "ntfs-short-alias",
    method: "item/fileChange/requestApproval",
    params: { path: "docs/EXEC-P~1/active/run.json" }
  });
  assert.deepEqual(app.responses.at(-1)?.result, { decision: "decline" });
});

test("approval broker auto-declines pre-gate, out-of-scope and destructive requests", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  app.emitApproval({ id: "outside", method: "item/fileChange/requestApproval", params: { path: "other/file.ts" } });
  app.emitApproval({ id: "danger", method: "item/commandExecution/requestApproval", params: { command: ["git", "push"] } });
  app.emitApproval({ id: "composite", method: "item/commandExecution/requestApproval", params: { command: "git status; git clean -fd" } });
  app.emitApproval({ id: "python", method: "item/commandExecution/requestApproval", params: { command: ["python", "-c", "print('x')"] } });
  app.emitApproval({ id: "powershell", method: "item/commandExecution/requestApproval", params: { command: ["powershell", "Set-Content", "x", "y"] } });
  assert.deepEqual(app.responses.map((item) => item.result), Array.from({ length: 5 }, () => ({ decision: "decline" })));
  assert.equal(controller.state.pendingApprovals.length, 0);
});

test("eligible approvals require explicit accept, decline, or cancel", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  app.emitApproval({ id: "read", method: "item/commandExecution/requestApproval", params: { command: ["git", "status"] } });
  assert.equal(controller.state.pendingApprovals.length, 1);
  await controller.resolveApproval("read", "accept");
  app.emitApproval({ id: "file", method: "item/fileChange/requestApproval", params: { path: "src/app.ts" } });
  await controller.resolveApproval("file", "cancel");
  assert.deepEqual(app.responses.slice(-2).map((item) => item.result), [{ decision: "accept" }, { decision: "cancel" }]);
});

test("controller routes decisions, gates and cancellation only through host methods", async () => {
  const host = new FakeHost();
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  await controller.decide({
    schema_version: 2, decision_id: "D-1", run_id: "run-1", question: "Q?",
    options: [{ option_id: "one", label: "One", description: "First" }, { option_id: "two", label: "Two", description: "Second" }],
    recommended_option_id: "one", allow_other: true, blocking_task_id: "TASK-001",
    created_revision: 1, status: "pending", answer: ""
  }, "one");
  await controller.decideGate("scope", true);
  await controller.cancel();
  assert.deepEqual(host.calls.slice(-3).map((item) => item.method), ["decision_resolve", "gate_decide", "run_cancel"]);
});

test("active-turn cancellation interrupts and awaits terminal state before host cancellation", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController(TEST_REPOSITORY, host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  await controller.startTurn("work");
  await controller.cancel();
  assert.equal(app.requests.at(-1)?.method, "turn/interrupt");
  assert.equal(host.calls.at(-1)?.method, "run_cancel");

  const blockedHost = new FakeHost();
  blockedHost.currentRun = run("implementation");
  const blockedApp = new FakeApp();
  blockedApp.turnCompletionStatus = "completed";
  const blocked = new WorkspaceController(TEST_REPOSITORY, blockedHost, blockedApp);
  await blocked.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  await blocked.startTurn("work");
  await assert.rejects(blocked.cancel(), /interrupted turn/);
  assert.notEqual(blockedHost.calls.at(-1)?.method, "run_cancel");
  assert.equal(blocked.state.status, "blocked");
});

test("high review performs at most three detached fix/reverify rounds", async () => {
  const responses = [1, 2, 3].map((round) => reviewEnvelope(round, [{
    schema_version: 2, finding_id: `F-${round}`, severity: "critical", status: "open", summary: "critical",
    paths: [], requirement_ids: [], acceptance_ids: [], task_ids: [], round
  }]));
  const port = {
    calls: 0,
    async request(): Promise<unknown> { this.calls += 1; return { reviewThreadId: `review-${this.calls}`, turn: { id: `turn-${this.calls}` } }; },
    async waitForReviewResult(): Promise<unknown> { return { text: JSON.stringify(responses.shift()) }; }
  };
  const fixes: number[] = [];
  const outcome = await new ReviewCoordinator(port).run(
    "high", "implement-thread", "main", SOURCE_FINGERPRINT,
    async (round) => { fixes.push(round); return SOURCE_FINGERPRINT; }
  );
  assert.equal(outcome.status, "blocked");
  assert.equal(outcome.round, 3);
  assert.equal(port.calls, 3);
  assert.deepEqual(fixes, [1, 2]);
});

test("standard review rejects reused identity and parses exitedReviewMode text", async () => {
  const reused = new ReviewCoordinator({
    async request() { return { reviewThreadId: "implement-thread", turn: { id: "review-turn" } }; },
    async waitForReviewResult() { return { text: JSON.stringify(reviewEnvelope(1, [])) }; }
  });
  assert.equal((await reused.run("standard", "implement-thread", "main", SOURCE_FINGERPRINT, async () => SOURCE_FINGERPRINT)).status, "blocked");
  const detached = new ReviewCoordinator({
    async request() { return { reviewThreadId: "review-thread", turn: { id: "review-turn" } }; },
    async waitForReviewResult(threadId, turnId) {
      assert.equal(threadId, "review-thread");
      assert.equal(turnId, "review-turn");
      return { text: JSON.stringify(reviewEnvelope(1, [{
        schema_version: 2, finding_id: "F-1", severity: "warning", status: "open", summary: "bounded warning",
        paths: [], requirement_ids: [], acceptance_ids: [], task_ids: [], round: 1
      }])) };
    }
  });
  const outcome = await detached.run("standard", "implement-thread", "main", SOURCE_FINGERPRINT, async () => SOURCE_FINGERPRINT);
  assert.equal(outcome.status, "passed");
  assert.equal(outcome.findings[0].severity, "warning");
});

test("malformed or contradictory detached review output fails closed", async () => {
  const values = [
    "ADVISORY [F-1] prose is not an envelope",
    JSON.stringify({ ...reviewEnvelope(1, []), severity: "critical" }),
    JSON.stringify({ ...reviewEnvelope(1, []), source_fingerprint: "b".repeat(64) })
  ];
  for (const text of values) {
    const coordinator = new ReviewCoordinator({
      async request() { return { reviewThreadId: "review-thread", turn: { id: "review-turn" } }; },
      async waitForReviewResult() { return { text }; }
    });
    const outcome = await coordinator.run("standard", "implement-thread", "main", SOURCE_FINGERPRINT, async () => SOURCE_FINGERPRINT);
    assert.equal(outcome.status, "blocked");
    assert.equal(outcome.protocolValid, false);
    assert.equal(outcome.findings[0].severity, "critical");
  }
});

test("host bridge client authenticates over stdin and never places token in spawn metadata", async () => {
  const token = "a".repeat(64);
  const transport = new TranscriptTransport((value, current) => {
    if (value.type === "hello") {
      const challenge = "challenge";
      const sessionId = "session";
      const proof = createHmac("sha256", String(value.token))
        .update(`server:${value.client_nonce}:${challenge}:${sessionId}`)
        .digest("hex");
      current.receive({ type: "challenge", challenge, session_id: sessionId, server_proof: proof });
    } else if (value.type === "proof") {
      current.receive({ type: "ready", session_id: "session" });
    } else if (typeof value.id === "number") {
      current.receive({ id: value.id, ok: true, result: { revision: 2 } });
    }
  });
  const client = new HostBridgeClient({
    transportFactory: () => transport,
    tokenFactory: () => token,
    nonceFactory: () => "client-nonce"
  });
  await client.connect("python.exe", "C:/repo/devweave_v2_host.py", "C:/repo");
  assert.deepEqual(transport.startOptions, {
    executable: "python.exe", args: ["-B", "C:/repo/devweave_v2_host.py"], cwd: "C:/repo"
  });
  assert.doesNotMatch(JSON.stringify(transport.startOptions), new RegExp(token));
  assert.equal((await client.request("gate_decide", {} ) as { revision: number }).revision, 2);
  await assert.rejects(client.request("run_inspect" as never, {}), /allowlist/);
  await client.close();
});

test("host bridge client rejects a forged server proof", async () => {
  const transport = new TranscriptTransport((value, current) => {
    if (value.type === "hello") current.receive({ type: "challenge", challenge: "x", session_id: "s", server_proof: "0".repeat(64) });
  });
  const client = new HostBridgeClient({
    transportFactory: () => transport,
    tokenFactory: () => "a".repeat(64),
    nonceFactory: () => "client-nonce"
  });
  await assert.rejects(client.connect("python.exe", "host.py", "C:/repo"), /proof/);
});

function reviewEnvelope(round: number, findings: Array<Record<string, unknown>>): Record<string, unknown> {
  const severity = findings.some((item) => item.severity === "critical")
    ? "critical" : findings.some((item) => item.severity === "warning") ? "warning" : "advisory";
  return {
    schema_version: 2,
    result: findings.some((item) => item.severity === "critical" && item.status === "open") ? "failed" : "passed",
    severity,
    source_fingerprint: SOURCE_FINGERPRINT,
    round,
    findings
  };
}
