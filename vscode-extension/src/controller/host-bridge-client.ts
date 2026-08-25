import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

import { AppServerError, bounded, isRecord } from "../app-server/protocol";
import { ChildProcessJsonLineTransport, type JsonLineTransport } from "../app-server/transport";

export const HOST_METHODS = [
  "run_start",
  "run_resume",
  "decision_resolve",
  "gate_decide",
  "run_cancel"
] as const;

export type HostMethod = typeof HOST_METHODS[number];

interface PendingRequest {
  resolve(value: unknown): void;
  reject(error: Error): void;
  timeout: NodeJS.Timeout;
}

export interface HostBridgeOptions {
  timeoutMs?: number;
  transportFactory?: () => JsonLineTransport;
  tokenFactory?: () => string;
  nonceFactory?: () => string;
}

export class HostBridgeClient {
  private transport: JsonLineTransport | undefined;
  private token = "";
  private clientNonce = "";
  private sessionId = "";
  private nextId = 1;
  private readonly pending = new Map<number, PendingRequest>();
  private handshakeResolve: (() => void) | undefined;
  private handshakeReject: ((error: Error) => void) | undefined;
  private state: "disconnected" | "challenge" | "proof" | "ready" | "failed" = "disconnected";
  private readonly timeoutMs: number;
  private readonly transportFactory: () => JsonLineTransport;
  private readonly tokenFactory: () => string;
  private readonly nonceFactory: () => string;

  public constructor(options: HostBridgeOptions = {}) {
    this.timeoutMs = options.timeoutMs ?? 10_000;
    this.transportFactory = options.transportFactory ?? (() => new ChildProcessJsonLineTransport());
    this.tokenFactory = options.tokenFactory ?? (() => randomBytes(32).toString("hex"));
    this.nonceFactory = options.nonceFactory ?? (() => randomBytes(24).toString("hex"));
  }

  public async connect(pythonExecutable: string, hostScript: string, cwd: string): Promise<void> {
    if (this.transport) throw new AppServerError("HOST_STATE", "Host bridge is already connected.");
    this.token = this.tokenFactory();
    this.clientNonce = this.nonceFactory();
    this.state = "challenge";
    const transport = this.transportFactory();
    this.transport = transport;
    await transport.start(
      { executable: pythonExecutable, args: ["-B", hostScript], cwd },
      {
        onLine: (line) => this.receiveLine(line),
        onStderr: () => undefined,
        onError: (error) => this.fail(error),
        onExit: (code) => this.fail(new AppServerError("HOST_EXIT", `Host bridge exited (${code ?? "unknown"}).`))
      }
    );
    const handshake = new Promise<void>((resolve, reject) => {
      this.handshakeResolve = resolve;
      this.handshakeReject = reject;
    });
    this.send({ type: "hello", token: this.token, client_nonce: this.clientNonce });
    const timer = setTimeout(() => this.fail(new AppServerError("HOST_TIMEOUT", "Host bridge handshake timed out.")), this.timeoutMs);
    try {
      await handshake;
    } finally {
      clearTimeout(timer);
    }
  }

  public request(method: HostMethod, params: unknown): Promise<unknown> {
    if (!HOST_METHODS.includes(method)) {
      return Promise.reject(new AppServerError("HOST_METHOD_FORBIDDEN", "Method is outside the host allowlist."));
    }
    if (this.state !== "ready") return Promise.reject(new AppServerError("HOST_STATE", "Host bridge is not authenticated."));
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new AppServerError("HOST_TIMEOUT", `${method} timed out.`));
      }, this.timeoutMs);
      this.pending.set(id, { resolve, reject, timeout });
      try {
        this.send({ id, method, params, session_id: this.sessionId });
      } catch (error) {
        clearTimeout(timeout);
        this.pending.delete(id);
        reject(error);
      }
    });
  }

  public async close(): Promise<void> {
    const transport = this.transport;
    this.transport = undefined;
    this.state = "disconnected";
    this.token = "";
    this.clientNonce = "";
    this.sessionId = "";
    this.rejectPending(new AppServerError("HOST_CLOSED", "Host bridge closed."));
    await transport?.close();
  }

  private receiveLine(line: string): void {
    let raw: unknown;
    try {
      raw = JSON.parse(line);
    } catch {
      this.fail(new AppServerError("HOST_PROTOCOL", "Host bridge emitted malformed JSON."));
      return;
    }
    if (!isRecord(raw)) {
      this.fail(new AppServerError("HOST_PROTOCOL", "Host bridge response must be an object."));
      return;
    }
    if (this.state === "challenge") {
      this.receiveChallenge(raw);
      return;
    }
    if (this.state === "proof") {
      if (raw.type !== "ready" || raw.session_id !== this.sessionId) {
        this.fail(new AppServerError("HOST_AUTH", "Host bridge ready response is invalid."));
        return;
      }
      this.state = "ready";
      this.token = "";
      this.clientNonce = "";
      this.handshakeResolve?.();
      this.handshakeResolve = undefined;
      this.handshakeReject = undefined;
      return;
    }
    if (this.state !== "ready" || typeof raw.id !== "number") {
      this.fail(new AppServerError("HOST_PROTOCOL", "Unexpected host bridge response."));
      return;
    }
    const pending = this.pending.get(raw.id);
    if (!pending) return;
    clearTimeout(pending.timeout);
    this.pending.delete(raw.id);
    if (raw.ok === true) {
      pending.resolve(raw.result);
    } else {
      const error = isRecord(raw.error) ? raw.error : {};
      pending.reject(new AppServerError(
        typeof error.code === "string" ? error.code : "HOST_ERROR",
        bounded(error.message ?? "Host operation failed.", 2_048)
      ));
    }
  }

  private receiveChallenge(raw: Record<string, unknown>): void {
    if (raw.type !== "challenge" || typeof raw.challenge !== "string" || typeof raw.session_id !== "string" || typeof raw.server_proof !== "string") {
      this.fail(new AppServerError("HOST_AUTH", "Host bridge challenge is invalid."));
      return;
    }
    this.sessionId = raw.session_id;
    const expected = this.digest("server", raw.challenge, this.sessionId);
    const received = Buffer.from(raw.server_proof, "hex");
    const expectedBytes = Buffer.from(expected, "hex");
    if (received.length !== expectedBytes.length || !timingSafeEqual(received, expectedBytes)) {
      this.fail(new AppServerError("HOST_AUTH", "Host bridge server proof was rejected."));
      return;
    }
    const proof = this.digest("client", raw.challenge, this.sessionId);
    this.state = "proof";
    this.send({ type: "proof", client_proof: proof });
  }

  private digest(role: string, challenge: string, sessionId: string): string {
    return createHmac("sha256", this.token)
      .update(`${role}:${this.clientNonce}:${challenge}:${sessionId}`, "utf8")
      .digest("hex");
  }

  private send(value: unknown): void {
    if (!this.transport) throw new AppServerError("HOST_CLOSED", "Host bridge transport is unavailable.");
    this.transport.send(JSON.stringify(value));
  }

  private fail(error: Error): void {
    this.state = "failed";
    this.token = "";
    this.clientNonce = "";
    this.handshakeReject?.(error);
    this.handshakeResolve = undefined;
    this.handshakeReject = undefined;
    this.rejectPending(error);
    const transport = this.transport;
    this.transport = undefined;
    void transport?.close();
  }

  private rejectPending(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout);
      pending.reject(error);
    }
    this.pending.clear();
  }
}
