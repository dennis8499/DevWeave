import assert from "node:assert/strict";
import test from "node:test";

import { reduceAppServerEvent, initialProjection } from "../../src/app-server/event-reducer";
import { CodexAppServerSession } from "../../src/app-server/session";
import { AppServerError } from "../../src/app-server/protocol";
import { TranscriptTransport } from "../../src/app-server/transport";


function connectedHarness(timeout = 1_000): { session: CodexAppServerSession; transport: TranscriptTransport; connect: Promise<unknown> } {
  const transport = new TranscriptTransport((value, current) => {
    if (value.method === "initialize") current.receive({ id: value.id, result: { userAgent: "fixture" } });
  });
  const session = new CodexAppServerSession({ requestTimeoutMs: timeout, transportFactory: () => transport });
  const connect = session.connect("C:/tools/codex.exe", "C:/repo");
  return { session, transport, connect };
}

test("session performs one stable initialize handshake without experimental opt-in", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  assert.deepEqual(transport.startOptions, { executable: "C:/tools/codex.exe", args: ["app-server"], cwd: "C:/repo" });
  const initialize = JSON.parse(transport.sent[0]) as { method: string; params: { capabilities: { experimentalApi: boolean }; clientInfo: { name: string } } };
  assert.equal(initialize.method, "initialize");
  assert.equal(initialize.params.clientInfo.name, "devweave_vscode");
  assert.equal(initialize.params.capabilities.experimentalApi, false);
  assert.deepEqual(JSON.parse(transport.sent[1]), { method: "initialized", params: {} });
  assert.equal(session.projection.connection, "connected");
  await session.close();
});

test("stable requests correlate out-of-order responses and reject experimental methods", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  const first = session.request("thread/start", { cwd: "C:/repo" });
  const second = session.request("mcpServerStatus/list", {});
  const firstEnvelope = JSON.parse(transport.sent[2]) as { id: number };
  const secondEnvelope = JSON.parse(transport.sent[3]) as { id: number };
  transport.receive({ id: secondEnvelope.id, result: { data: ["mcp"] } });
  transport.receive({ id: firstEnvelope.id, result: { thread: { id: "thread-1" } } });
  assert.deepEqual(await first, { thread: { id: "thread-1" } });
  assert.deepEqual(await second, { data: ["mcp"] });
  await assert.rejects(
    session.request("tool/requestUserInput" as never, {}),
    (error: unknown) => error instanceof AppServerError && error.code === "METHOD_FORBIDDEN"
  );
  await session.close();
});

test("event reducer covers plan diff item usage warnings and authoritative completion", () => {
  let state = initialProjection();
  state = reduceAppServerEvent(state, "thread/started", { thread: { id: "thread-1" } });
  state = reduceAppServerEvent(state, "turn/started", { threadId: "thread-1", turn: { id: "turn-1" } });
  state = reduceAppServerEvent(state, "turn/plan/updated", { plan: [{ step: "one" }] });
  state = reduceAppServerEvent(state, "turn/diff/updated", { diff: "+line" });
  state = reduceAppServerEvent(state, "item/started", { item: { id: "msg-1", type: "agentMessage" } });
  state = reduceAppServerEvent(state, "item/agentMessage/delta", { itemId: "msg-1", delta: "projection" });
  assert.equal(state.items["msg-1"].authoritative, false);
  state = reduceAppServerEvent(state, "item/completed", { item: { id: "msg-1", type: "agentMessage", status: "completed", text: "authority" } });
  state = reduceAppServerEvent(state, "thread/tokenUsage/updated", {
    threadId: "thread-1", turnId: "turn-1",
    tokenUsage: { total: { inputTokens: 3, outputTokens: 4, totalTokens: 7 } }
  });
  state = reduceAppServerEvent(state, "mcpServer/startupStatus/updated", { name: "devweave", status: "ready" });
  state = reduceAppServerEvent(state, "warning", { message: "bounded warning" });
  assert.equal(state.threadId, "thread-1");
  assert.equal(state.turnId, "turn-1");
  assert.deepEqual(state.plan, [{ step: "one" }]);
  assert.equal(state.diff, "+line");
  assert.equal(state.items["msg-1"].content, "authority");
  assert.equal(state.items["msg-1"].authoritative, true);
  assert.deepEqual(state.usage, { inputTokens: 3, outputTokens: 4, totalTokens: 7 });
  assert.equal(state.mcpStatus?.status, "ready");
  assert.equal(state.diagnostics.at(-1)?.code, "app_server_warning");
});

test("reasoning content is discarded for deltas and completed items", () => {
  let state = reduceAppServerEvent(initialProjection(), "item/started", { item: { id: "think-1", type: "reasoning", content: "private start" } });
  state = reduceAppServerEvent(state, "item/agentMessage/delta", { itemId: "think-1", delta: "private delta" });
  state = reduceAppServerEvent(state, "item/completed", { item: { id: "think-1", type: "reasoning", content: "private final", summary: "private summary" } });
  const serialized = JSON.stringify(state);
  assert.doesNotMatch(serialized, /private start|private delta|private final|private summary/);
  assert.deepEqual(state.items["think-1"], {
    id: "think-1", type: "reasoning", status: "completed", authoritative: true, hasPrivateContent: true
  });
});

test("unknown events are diagnostic-only while malformed JSON fails and rejects pending", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  transport.receive({ method: "future/event", params: { value: 1 } });
  assert.equal(session.projection.connection, "connected");
  assert.equal(session.projection.diagnostics.at(-1)?.code, "unsupported_event");
  const pending = session.request("thread/read", { threadId: "thread-1" });
  transport.receiveRaw("not-json");
  await assert.rejects(pending, /malformed JSON/);
  assert.equal(session.projection.connection, "failed");
  await session.close();
});

test("aggregate output limit fails the connection without retaining oversized content", async () => {
  const transport = new TranscriptTransport((value, current) => {
    if (value.method === "initialize") current.receive({ id: value.id, result: {} });
  });
  const session = new CodexAppServerSession({ maxAggregateBytes: 128, transportFactory: () => transport });
  await session.connect("codex.exe", "C:/repo");
  transport.receive({ method: "warning", params: { message: "x".repeat(256) } });
  assert.equal(session.projection.connection, "failed");
  assert.doesNotMatch(JSON.stringify(session.projection), /x{64}/);
  await session.close();
});

test("server approval requests are surfaced and can receive a correlated response", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  const requests: unknown[] = [];
  session.onServerRequest((request) => requests.push(request));
  transport.receive({ id: "approval-1", method: "item/commandExecution/requestApproval", params: { command: ["git", "status"] } });
  assert.equal(requests.length, 1);
  session.respond("approval-1", { decision: "decline" });
  assert.deepEqual(JSON.parse(transport.sent.at(-1)!), { id: "approval-1", result: { decision: "decline" } });
  await session.close();
});

test("turn completion can be awaited before or after the authoritative event arrives", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  const pending = session.waitForTurnCompleted("turn-before");
  transport.receive({ method: "turn/completed", params: { threadId: "thread", turn: { id: "turn-before", status: "completed" } } });
  assert.deepEqual(await pending, { status: "completed" });
  transport.receive({ method: "turn/completed", params: { threadId: "thread", turn: { id: "turn-after", status: "failed" } } });
  assert.deepEqual(await session.waitForTurnCompleted("turn-after"), { status: "failed" });
  await session.close();
});

test("detached review completion reads the stable exitedReviewMode review field", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  const pending = session.waitForReviewResult("review-thread");
  transport.receive({
    method: "item/completed",
    params: {
      threadId: "review-thread", turnId: "review-turn", completedAtMs: 1,
      item: { id: "review-item", type: "exitedReviewMode", review: "WARNING [F-1] bounded finding" }
    }
  });
  assert.deepEqual(await pending, { text: "WARNING [F-1] bounded finding", findings: undefined });
  await session.close();
});

test("detached review compatibility fallback requires the exact reviewer thread and completed review turn", async () => {
  const { session, transport, connect } = connectedHarness();
  await connect;
  const pending = session.waitForReviewResult("review-thread", "review-turn");
  transport.receive({
    method: "item/completed",
    params: {
      threadId: "other-thread", turnId: "review-turn",
      item: { id: "wrong", type: "agentMessage", text: "CRITICAL [WRONG] wrong thread" }
    }
  });
  transport.receive({
    method: "item/completed",
    params: {
      threadId: "review-thread", turnId: "review-turn",
      item: { id: "review-message", type: "agentMessage", text: "WARNING [F-2] compatibility finding" }
    }
  });
  transport.receive({
    method: "turn/completed",
    params: { threadId: "review-thread", turn: { id: "review-turn", status: "completed" } }
  });
  assert.deepEqual(await pending, {
    text: "WARNING [F-2] compatibility finding",
    findings: undefined,
    compatibility: "authoritative_agent_message"
  });
  await session.close();
});

test("process exit rejects calls and reconnect resumes the recorded thread", async () => {
  const transports: TranscriptTransport[] = [];
  const session = new CodexAppServerSession({
    requestTimeoutMs: 1_000,
    transportFactory: () => {
      const transport = new TranscriptTransport((value, current) => {
        if (value.method === "initialize") current.receive({ id: value.id, result: {} });
        if (value.method === "thread/resume") current.receive({ id: value.id, result: { thread: { id: "thread-1" } } });
      });
      transports.push(transport);
      return transport;
    }
  });
  await session.connect("codex.exe", "C:/repo");
  const pending = session.request("turn/interrupt", { threadId: "thread-1", turnId: "turn-1" });
  transports[0].exit(9);
  await assert.rejects(pending, /exited/);
  await session.reconnect("thread-1");
  assert.equal(transports.length, 2);
  const resume = JSON.parse(transports[1].sent[2]) as { method: string; params: unknown };
  assert.equal(resume.method, "thread/resume");
  assert.deepEqual(resume.params, {
    threadId: "thread-1", cwd: "C:/repo", approvalPolicy: "untrusted",
    approvalsReviewer: "user", sandbox: "read-only"
  });
  await session.close();
});

test("request timeout is bounded", async () => {
  const { session, connect } = connectedHarness(10);
  await connect;
  await assert.rejects(session.request("turn/steer", {}), /timed out/);
  await session.close();
});
