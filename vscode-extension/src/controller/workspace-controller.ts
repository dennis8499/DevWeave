import { EventEmitter } from "node:events";

import type { AppServerProjection } from "../app-server/event-reducer";
import type { ServerRequest } from "../app-server/session";
import type { PendingDecision, ReviewFinding, RiskLevel } from "../v2/contracts";
import { ApprovalBroker, type ApprovalAssessment, type ApprovalDecision } from "./approval-broker";
import type { HostMethod } from "./host-bridge-client";
import { ReviewCoordinator, type ReviewOutcome } from "./review-coordinator";
import { writableTaskRoots } from "./task-scope";

const REQUIRED_AGENT_TOOLS = [
  "run_inspect", "context_read", "plan_save", "decision_request", "task_update",
  "verification_run", "verification_read", "completion_request"
] as const;

export interface HostPort {
  request(method: HostMethod, params: unknown): Promise<unknown>;
}

export interface AppServerPort {
  projection: AppServerProjection;
  connect(executable: string, cwd: string): Promise<unknown>;
  request(method: "thread/start" | "thread/resume" | "thread/read" | "turn/start" | "turn/steer" | "turn/interrupt" | "review/start" | "mcpServerStatus/list" | "config/mcpServer/reload", params: unknown): Promise<unknown>;
  respond(requestId: number | string, result: unknown): void;
  waitForReviewResult?(reviewerThreadId: string): Promise<unknown>;
  waitForTurnCompleted?(turnId: string): Promise<unknown>;
  onProjection(listener: (state: AppServerProjection) => void): () => void;
  onServerRequest(listener: (request: ServerRequest) => void): () => void;
}

interface PendingApproval {
  request: ServerRequest;
  assessment: ApprovalAssessment;
}

export interface ControllerState {
  status: "idle" | "connecting" | "ready" | "blocked" | "cancelled";
  run: Record<string, unknown> | null;
  preflight: Record<string, unknown> | null;
  appServer: AppServerProjection;
  threadId: string;
  turnId: string;
  pendingApprovals: PendingApproval[];
  review: ReviewOutcome | null;
  diagnostics: string[];
}

export class WorkspaceController {
  private readonly emitter = new EventEmitter();
  private readonly approvals = new Map<number | string, PendingApproval>();
  private readonly broker: ApprovalBroker;
  private readonly reviewCoordinator: ReviewCoordinator;
  private stateValue: ControllerState;

  public constructor(
    private readonly repository: string,
    private readonly host: HostPort,
    private readonly appServer: AppServerPort
  ) {
    this.broker = new ApprovalBroker(repository);
    this.reviewCoordinator = new ReviewCoordinator(appServer);
    this.stateValue = {
      status: "idle", run: null, preflight: null, appServer: appServer.projection,
      threadId: "", turnId: "", pendingApprovals: [], review: null, diagnostics: []
    };
    appServer.onProjection((projection) => {
      this.stateValue = { ...this.stateValue, appServer: projection };
      this.publish();
    });
    appServer.onServerRequest((request) => this.receiveApproval(request));
  }

  public get state(): ControllerState {
    return structuredClone(this.stateValue);
  }

  public subscribe(listener: (state: ControllerState) => void): () => void {
    this.emitter.on("state", listener);
    return () => this.emitter.off("state", listener);
  }

  public async startRun(params: { draft: Record<string, unknown>; slug: string; codex_path?: string }): Promise<ControllerState> {
    this.transition("connecting");
    try {
      const response = record(await this.host.request("run_start", params));
      const run = record(response.run);
      const preflight = record(response.preflight);
      const codex = record(preflight.codex);
      if (typeof codex.path !== "string") throw new Error("Codex preflight did not return an executable path.");
      await this.appServer.connect(codex.path, this.repository);
      const thread = record(await this.appServer.request("thread/start", this.threadParams(run)));
      const threadId = extractId(record(thread.thread), "id") || extractId(thread, "threadId", "thread_id");
      if (!threadId) throw new Error("App-server did not return a thread id.");
      await this.assertRequiredMcp(threadId);
      this.stateValue = { ...this.stateValue, status: "ready", run, preflight, threadId };
      this.publish();
      return this.state;
    } catch (error) {
      this.block(error);
      throw error;
    }
  }

  public async resumeRun(runId: string, codexPath?: string, threadId?: string): Promise<ControllerState> {
    this.transition("connecting");
    try {
      const response = record(await this.host.request("run_resume", { run_id: runId, ...(codexPath ? { codex_path: codexPath } : {}) }));
      const run = record(response.run);
      const preflight = record(response.preflight);
      const codex = record(preflight.codex);
      if (typeof codex.path !== "string") throw new Error("Codex preflight did not return an executable path.");
      if (this.appServer.projection.connection !== "connected") await this.appServer.connect(codex.path, this.repository);
      let activeThread = threadId ?? "";
      if (activeThread) await this.appServer.request("thread/resume", { threadId: activeThread, ...this.threadParams(run) });
      else {
        const started = record(await this.appServer.request("thread/start", this.threadParams(run)));
        activeThread = extractId(record(started.thread), "id") || extractId(started, "threadId", "thread_id");
      }
      await this.assertRequiredMcp(activeThread);
      this.stateValue = { ...this.stateValue, status: "ready", run, preflight, threadId: activeThread };
      this.publish();
      return this.state;
    } catch (error) {
      this.block(error);
      throw error;
    }
  }

  public async startTurn(input: string): Promise<string> {
    this.assertReady();
    const response = record(await this.appServer.request("turn/start", {
      threadId: this.stateValue.threadId,
      input: [{ type: "text", text: input }],
      approvalPolicy: "untrusted",
      approvalsReviewer: "user",
      sandboxPolicy: this.turnSandboxPolicy(this.stateValue.run ?? {})
    }));
    this.stateValue = { ...this.stateValue, turnId: extractId(record(response.turn), "id") || extractId(response, "turnId", "turn_id") };
    this.publish();
    return this.stateValue.turnId;
  }

  public async steer(input: string): Promise<void> {
    this.assertReady();
    await this.appServer.request("turn/steer", {
      threadId: this.stateValue.threadId,
      expectedTurnId: this.stateValue.turnId,
      input: [{ type: "text", text: input }]
    });
  }

  public async interrupt(): Promise<void> {
    this.assertReady();
    await this.appServer.request("turn/interrupt", { threadId: this.stateValue.threadId, turnId: this.stateValue.turnId });
  }

  public async decide(decision: PendingDecision, optionId?: string, other?: string): Promise<void> {
    const run = this.requireRun();
    const updated = await this.host.request("decision_resolve", {
      run_id: run.run_id, expected_revision: run.revision,
      mutation_id: `decision-${decision.decision_id}-${run.revision}`,
      decision_id: decision.decision_id,
      ...(optionId ? { option_id: optionId } : {}),
      ...(other ? { other } : {})
    });
    this.setRun(record(updated));
  }

  public async decideGate(gateId: string, approve: boolean, review?: ReviewOutcome): Promise<void> {
    const run = this.requireRun();
    if (approve && review && review.status !== "passed") throw new Error("A blocked review cannot approve acceptance.");
    const reviewResult = review && review.reviewerThreadId !== "self-review" ? {
      schema_version: 2,
      result: review.result,
      severity: review.severity,
      source_fingerprint: review.sourceFingerprint,
      implementation_thread_id: this.stateValue.threadId,
      reviewer_thread_id: review.reviewerThreadId,
      review_turn_id: review.reviewTurnId,
      round: review.round,
      findings: review.findings
    } : undefined;
    const updated = await this.host.request("gate_decide", {
      run_id: run.run_id, expected_revision: run.revision,
      mutation_id: `gate-${gateId}-${run.revision}-${approve ? "approve" : "reject"}`,
      gate_id: gateId, approve,
      ...(reviewResult ? { review_result: reviewResult } : {})
    });
    this.setRun(record(updated));
  }

  public async cancel(): Promise<void> {
    try {
      const run = this.requireRun();
      for (const [requestId] of this.approvals) {
        this.appServer.respond(requestId, { decision: "decline" });
        this.approvals.delete(requestId);
      }
      this.syncApprovals();
      if (this.stateValue.turnId) {
        if (!this.appServer.waitForTurnCompleted) throw new Error("Cancellation cannot confirm terminal turn state.");
        await this.appServer.request("turn/interrupt", {
          threadId: this.stateValue.threadId,
          turnId: this.stateValue.turnId
        });
        const terminal = record(await this.appServer.waitForTurnCompleted(this.stateValue.turnId));
        if (terminal.status !== "interrupted") throw new Error("Cancellation requires an authoritative interrupted turn.");
      }
      const updated = await this.host.request("run_cancel", {
        run_id: run.run_id, expected_revision: run.revision, mutation_id: `cancel-${run.revision}`
      });
      this.setRun(record(updated));
      this.transition("cancelled");
    } catch (error) {
      this.block(error);
      throw error;
    }
  }

  public async refreshRun(codexPath?: string): Promise<void> {
    const run = this.requireRun();
    const response = record(await this.host.request("run_resume", {
      run_id: run.run_id,
      ...(codexPath ? { codex_path: codexPath } : {})
    }));
    this.stateValue = {
      ...this.stateValue,
      run: record(response.run),
      preflight: record(response.preflight)
    };
    this.publish();
  }

  public async resolveApproval(requestId: number | string, decision: ApprovalDecision): Promise<void> {
    const pending = this.approvals.get(requestId);
    if (!pending) throw new Error("Approval request is not pending.");
    this.broker.assertDecision(pending.assessment, decision);
    this.appServer.respond(requestId, { decision });
    this.approvals.delete(requestId);
    this.syncApprovals();
  }

  public async reviewForAcceptance(
    fixAndReverify: (round: number, findings: ReviewFinding[]) => Promise<void>
  ): Promise<ReviewOutcome> {
    const run = this.requireRun();
    const sourceFingerprint = currentVerificationFingerprint(run);
    const outcome = await this.reviewCoordinator.run(
      run.risk as RiskLevel,
      this.stateValue.threadId,
      String(run.base_branch ?? ""),
      sourceFingerprint,
      async (round, findings) => {
        await fixAndReverify(round, findings);
        return currentVerificationFingerprint(this.requireRun());
      }
    );
    this.stateValue = { ...this.stateValue, review: outcome, status: outcome.status === "passed" ? "ready" : "blocked" };
    this.publish();
    return outcome;
  }

  private receiveApproval(request: ServerRequest): void {
    const run = this.stateValue.run ?? {};
    const assessment = this.broker.assess(request, run);
    this.approvals.set(request.id, { request, assessment });
    this.syncApprovals();
    if (!assessment.eligible) {
      this.appServer.respond(request.id, { decision: "decline" });
      this.approvals.delete(request.id);
      this.stateValue.diagnostics.push(`approval_declined:${assessment.reason}`);
      this.syncApprovals();
    }
  }

  private async assertRequiredMcp(threadId: string): Promise<void> {
    const response = record(await this.appServer.request("mcpServerStatus/list", {
      threadId, detail: "full", limit: 100
    }));
    const servers = Array.isArray(response.data) ? response.data : Array.isArray(response.servers) ? response.servers : [];
    const devweave = servers.map(record).find((server) => server.name === "devweave");
    if (!devweave) throw new Error("Required DevWeave MCP server is not ready.");
    const tools = Object.keys(record(devweave.tools)).sort();
    if (JSON.stringify(tools) !== JSON.stringify([...REQUIRED_AGENT_TOOLS].sort())) {
      throw new Error("Required DevWeave MCP tool set is not exact/current.");
    }
  }

  private threadParams(run: Record<string, unknown>): Record<string, unknown> {
    return {
      cwd: this.repository,
      approvalPolicy: "untrusted",
      approvalsReviewer: "user",
      sandbox: "read-only"
    };
  }

  private turnSandboxPolicy(run: Record<string, unknown>): Record<string, unknown> {
    const roots = run.phase === "implementation" ? writableTaskRoots(this.repository, run) : [];
    return roots.length > 0
      ? { type: "workspaceWrite", writableRoots: roots, networkAccess: false }
      : { type: "readOnly", networkAccess: false };
  }

  private assertReady(): void {
    if (this.stateValue.status !== "ready" || !this.stateValue.threadId) throw new Error("Workspace controller is not ready.");
  }

  private requireRun(): Record<string, unknown> {
    if (!this.stateValue.run) throw new Error("No authoritative run is loaded.");
    return this.stateValue.run;
  }

  private setRun(run: Record<string, unknown>): void {
    this.stateValue = { ...this.stateValue, run };
    this.publish();
  }

  private transition(status: ControllerState["status"]): void {
    this.stateValue = { ...this.stateValue, status };
    this.publish();
  }

  private block(error: unknown): void {
    const message = error instanceof Error ? error.message : String(error);
    this.stateValue = { ...this.stateValue, status: "blocked", diagnostics: [...this.stateValue.diagnostics, message].slice(-100) };
    this.publish();
  }

  private syncApprovals(): void {
    this.stateValue = { ...this.stateValue, pendingApprovals: [...this.approvals.values()] };
    this.publish();
  }

  private publish(): void {
    this.emitter.emit("state", this.state);
  }
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function extractId(value: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) if (typeof value[key] === "string") return value[key];
  return "";
}

function currentVerificationFingerprint(run: Record<string, unknown>): string {
  const verification = record(run.verification);
  const reportId = typeof verification.current_report_id === "string" ? verification.current_report_id : "";
  const report = record(record(verification.reports)[reportId]);
  const source = typeof report.source_digest === "string" ? report.source_digest : "";
  if (!/^[0-9a-f]{64}$/.test(source) || verification.status !== "passed") {
    throw new Error("Current verification source fingerprint is unavailable.");
  }
  return source;
}
