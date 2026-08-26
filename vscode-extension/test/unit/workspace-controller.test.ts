import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import test from "node:test";

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

function run(phase = "planning", risk = "high"): Record<string, unknown> {
  return {
    run_id: "run-1", revision: 1, phase, risk, base_branch: "main", status: phase === "planning" ? "awaiting_gate" : "implementing",
    plan: { scope: ["src/**"] },
    tasks: {
      "TASK-001": {
        status: "in_progress",
        definition: { task_id: "TASK-001", declared_paths: ["src/**"] }
      }
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
  const controller = new WorkspaceController("C:/repo", host, app);
  const state = await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  assert.equal(state.status, "ready");
  assert.equal(state.threadId, "implement-thread");
  assert.deepEqual(app.requests.map((item) => item.method), ["thread/start", "mcpServerStatus/list"]);
  assert.deepEqual(app.requests[0].params, {
    cwd: "C:/repo", approvalPolicy: "untrusted", approvalsReviewer: "user", sandbox: "read-only"
  });
  assert.deepEqual(app.requests[1].params, { threadId: "implement-thread", detail: "full", limit: 100 });
  assert.equal(host.calls[0].method, "run_start");
});

test("required MCP failure blocks after the thread-scoped inventory is available", async () => {
  const host = new FakeHost();
  const app = new FakeApp();
  app.mcpTools = TOOLS.slice(0, -1);
  const controller = new WorkspaceController("C:/repo", host, app);
  await assert.rejects(controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" }), /tool set/);
  assert.equal(controller.state.status, "blocked");
  assert.deepEqual(app.requests.map((item) => item.method), ["thread/start", "mcpServerStatus/list"]);
});

test("implementation thread uses workspace-write with network disabled and resume is idempotent", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController("C:/repo", host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  assert.equal((app.requests[0].params as { sandbox: unknown }).sandbox, "workspace-write");
  await controller.startTurn("continue");
  assert.deepEqual(app.requests.at(-1)?.params, {
    threadId: "implement-thread",
    input: [{ type: "text", text: "continue" }],
    approvalPolicy: "untrusted",
    approvalsReviewer: "user",
    sandboxPolicy: { type: "workspaceWrite", writableRoots: ["C:/repo"], networkAccess: false }
  });
  await controller.steer("clarify");
  assert.deepEqual(app.requests.at(-1)?.params, {
    threadId: "implement-thread", expectedTurnId: "turn-1", input: [{ type: "text", text: "clarify" }]
  });
  await controller.resumeRun("run-1", undefined, "implement-thread");
  assert.equal(host.calls.at(-1)?.method, "run_resume");
  assert.deepEqual(app.requests.slice(-2).map((item) => item.method), ["thread/resume", "mcpServerStatus/list"]);
  assert.deepEqual(app.requests.at(-2)?.params, {
    threadId: "implement-thread", cwd: "C:/repo", approvalPolicy: "untrusted",
    approvalsReviewer: "user", sandbox: "workspace-write"
  });
});

test("approval broker auto-declines pre-gate, out-of-scope and destructive requests", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController("C:/repo", host, app);
  await controller.startRun({ draft: { run_id: "run-1" }, slug: "slice" });
  app.emitApproval({ id: "outside", method: "item/fileChange/requestApproval", params: { path: "other/file.ts" } });
  app.emitApproval({ id: "danger", method: "item/commandExecution/requestApproval", params: { command: ["git", "push"] } });
  assert.deepEqual(app.responses.map((item) => item.result), [{ decision: "decline" }, { decision: "decline" }]);
  assert.equal(controller.state.pendingApprovals.length, 0);
});

test("eligible approvals require explicit accept, decline, or cancel", async () => {
  const host = new FakeHost();
  host.currentRun = run("implementation");
  const app = new FakeApp();
  const controller = new WorkspaceController("C:/repo", host, app);
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
  const controller = new WorkspaceController("C:/repo", host, app);
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

test("high review performs at most three detached fix/reverify rounds", async () => {
  const responses = [1, 2, 3].map((round) => ({
    reviewThreadId: `review-${round}`,
    findings: [{ id: `F-${round}`, severity: "critical", status: "open", summary: "critical" }]
  }));
  const port = {
    calls: 0,
    async request(): Promise<unknown> { this.calls += 1; return responses.shift(); }
  };
  const fixes: number[] = [];
  const outcome = await new ReviewCoordinator(port).run("high", "implement-thread", "main", async (round) => { fixes.push(round); });
  assert.equal(outcome.status, "blocked");
  assert.equal(outcome.round, 3);
  assert.equal(port.calls, 3);
  assert.deepEqual(fixes, [1, 2]);
});

test("standard review rejects reused identity and parses exitedReviewMode text", async () => {
  const reused = new ReviewCoordinator({ async request() { return { reviewThreadId: "implement-thread", findings: [] }; } });
  assert.equal((await reused.run("standard", "implement-thread", "main", async () => undefined)).status, "blocked");
  const detached = new ReviewCoordinator({
    async request() { return { reviewThreadId: "review-thread" }; },
    async waitForReviewResult() { return { text: "WARNING [F-1] bounded advisory" }; }
  });
  const outcome = await detached.run("standard", "implement-thread", "main", async () => undefined);
  assert.equal(outcome.status, "passed");
  assert.equal(outcome.findings[0].severity, "warning");
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
