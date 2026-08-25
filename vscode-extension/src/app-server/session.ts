import { EventEmitter } from "node:events";

import { DEVWEAVE_VERSION } from "../v2/contracts";
import { addDiagnostic, initialProjection, reduceAppServerEvent, type AppServerProjection } from "./event-reducer";
import {
  APP_SERVER_METHODS,
  AppServerError,
  SERVER_REQUEST_METHODS,
  bounded,
  isRecord,
  type AppServerMethod,
  type ServerRequestMethod
} from "./protocol";
import { ChildProcessJsonLineTransport, type JsonLineTransport } from "./transport";

interface PendingRequest {
  method: string;
  resolve(value: unknown): void;
  reject(error: Error): void;
  timeout: NodeJS.Timeout;
}

export interface ServerRequest {
  id: number | string;
  method: ServerRequestMethod;
  params: unknown;
}

export interface SessionOptions {
  requestTimeoutMs?: number;
  maxAggregateBytes?: number;
  transportFactory?: () => JsonLineTransport;
}

export class CodexAppServerSession {
  private transport: JsonLineTransport | undefined;
  private nextId = 1;
  private pending = new Map<number, PendingRequest>();
  private initialized = false;
  private aggregateBytes = 0;
  private executable = "";
  private cwd = "";
  private readonly emitter = new EventEmitter();
  private projectionValue = initialProjection();
  private readonly timeoutMs: number;
  private readonly maxAggregateBytes: number;
  private readonly transportFactory: () => JsonLineTransport;

  public constructor(options: SessionOptions = {}) {
    this.timeoutMs = options.requestTimeoutMs ?? 30_000;
    this.maxAggregateBytes = options.maxAggregateBytes ?? 10_000_000;
    this.transportFactory = options.transportFactory ?? (() => new ChildProcessJsonLineTransport());
  }

  public get projection(): AppServerProjection {
    return structuredClone(this.projectionValue);
  }

  public onProjection(listener: (state: AppServerProjection) => void): () => void {
    this.emitter.on("projection", listener);
    return () => this.emitter.off("projection", listener);
  }

  public onServerRequest(listener: (request: ServerRequest) => void): () => void {
    this.emitter.on("serverRequest", listener);
    return () => this.emitter.off("serverRequest", listener);
  }

  public async connect(executable: string, cwd: string): Promise<unknown> {
    if (this.transport) throw new AppServerError("SESSION_STATE", "App-server session is already connected.");
    this.executable = executable;
    this.cwd = cwd;
    this.aggregateBytes = 0;
    this.projectionValue = { ...initialProjection(), connection: "connecting" };
    this.publish();
    const transport = this.transportFactory();
    this.transport = transport;
    await transport.start(
      { executable, args: ["app-server"], cwd },
      {
        onLine: (line) => this.receiveLine(line),
        onStderr: (value) => this.diagnostic("app_server_stderr", value),
        onError: (error) => this.fail(error),
        onExit: (code, signal) => this.fail(new AppServerError("PROCESS_EXIT", `App-server exited (${code ?? signal ?? "unknown"}).`))
      }
    );
    const initialized = await this.internalRequest("initialize", {
      clientInfo: { name: "devweave_vscode", title: "DevWeave", version: DEVWEAVE_VERSION },
      capabilities: { experimentalApi: false }
    });
    this.sendNotification("initialized", {});
    this.initialized = true;
    this.projectionValue = { ...this.projectionValue, connection: "connected" };
    this.publish();
    return initialized;
  }

  public request(method: AppServerMethod, params: unknown): Promise<unknown> {
    if (!APP_SERVER_METHODS.includes(method)) {
      return Promise.reject(new AppServerError("METHOD_FORBIDDEN", "Method is outside the stable app-server allowlist."));
    }
    if (!this.initialized) return Promise.reject(new AppServerError("SESSION_STATE", "App-server session is not initialized."));
    return this.internalRequest(method, params);
  }

  public respond(requestId: number | string, result: unknown): void {
    this.send({ id: requestId, result });
  }

  public respondError(requestId: number | string, code: number, message: string): void {
    this.send({ id: requestId, error: { code, message: bounded(message, 1_024) } });
  }

  public async reconnect(threadId?: string): Promise<void> {
    const executable = this.executable;
    const cwd = this.cwd;
    await this.close();
    await this.connect(executable, cwd);
    if (threadId) await this.request("thread/resume", { threadId });
  }

  public async close(): Promise<void> {
    const transport = this.transport;
    this.transport = undefined;
    this.initialized = false;
    this.rejectPending(new AppServerError("SESSION_CLOSED", "App-server session closed."));
    await transport?.close();
    this.projectionValue = { ...this.projectionValue, connection: "disconnected" };
    this.publish();
  }

  private internalRequest(method: string, params: unknown): Promise<unknown> {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new AppServerError("REQUEST_TIMEOUT", `${method} timed out.`));
      }, this.timeoutMs);
      this.pending.set(id, { method, resolve, reject, timeout });
      try {
        this.send({ id, method, params });
      } catch (error) {
        clearTimeout(timeout);
        this.pending.delete(id);
        reject(error);
      }
    });
  }

  private sendNotification(method: string, params: unknown): void {
    this.send({ method, params });
  }

  private send(value: unknown): void {
    if (!this.transport) throw new AppServerError("TRANSPORT_CLOSED", "App-server transport is unavailable.");
    this.transport.send(JSON.stringify(value));
  }

  private receiveLine(line: string): void {
    this.aggregateBytes += Buffer.byteLength(line, "utf8");
    if (this.aggregateBytes > this.maxAggregateBytes) {
      this.fail(new AppServerError("AGGREGATE_TOO_LARGE", "App-server aggregate output exceeds its limit."));
      return;
    }
    let value: unknown;
    try {
      value = JSON.parse(line);
    } catch {
      this.fail(new AppServerError("MALFORMED_JSON", "App-server emitted malformed JSON."));
      return;
    }
    if (!isRecord(value)) {
      this.fail(new AppServerError("PROTOCOL_ERROR", "App-server message must be an object."));
      return;
    }
    if ((typeof value.id === "number" || typeof value.id === "string") && typeof value.method === "string") {
      if (SERVER_REQUEST_METHODS.includes(value.method as ServerRequestMethod)) {
        this.emitter.emit("serverRequest", {
          id: value.id,
          method: value.method as ServerRequestMethod,
          params: value.params
        } satisfies ServerRequest);
      } else {
        this.diagnostic("unsupported_server_request", value.method);
      }
      return;
    }
    if (typeof value.id === "number") {
      const pending = this.pending.get(value.id);
      if (!pending) {
        this.diagnostic("orphan_response", value.id);
        return;
      }
      clearTimeout(pending.timeout);
      this.pending.delete(value.id);
      if (isRecord(value.error)) {
        pending.reject(new AppServerError("REMOTE_ERROR", bounded(value.error.message ?? value.error, 2_048)));
      } else {
        pending.resolve(value.result);
      }
      return;
    }
    if (typeof value.method === "string") {
      this.projectionValue = reduceAppServerEvent(this.projectionValue, value.method, value.params);
      this.publish();
      return;
    }
    this.diagnostic("unsupported_message", "App-server message had no method or correlated id.");
  }

  private diagnostic(code: string, message: unknown): void {
    this.projectionValue = addDiagnostic(this.projectionValue, code, message);
    this.publish();
  }

  private fail(error: Error): void {
    const transport = this.transport;
    this.transport = undefined;
    void transport?.close();
    this.rejectPending(error);
    this.initialized = false;
    this.projectionValue = addDiagnostic({ ...this.projectionValue, connection: "failed" }, "app_server_failure", error.message);
    this.publish();
  }

  private rejectPending(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout);
      pending.reject(error);
    }
    this.pending.clear();
  }

  private publish(): void {
    this.emitter.emit("projection", this.projection);
  }
}
