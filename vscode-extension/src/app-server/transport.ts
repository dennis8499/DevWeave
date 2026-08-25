import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { TextDecoder } from "node:util";

import { AppServerError } from "./protocol";

export interface TransportStartOptions {
  executable: string;
  args: string[];
  cwd: string;
}

export interface TransportHandlers {
  onLine(line: string): void;
  onStderr(value: string): void;
  onError(error: Error): void;
  onExit(code: number | null, signal: NodeJS.Signals | null): void;
}

export interface JsonLineTransport {
  start(options: TransportStartOptions, handlers: TransportHandlers): Promise<void>;
  send(line: string): void;
  close(): Promise<void>;
}

export class ChildProcessJsonLineTransport implements JsonLineTransport {
  private child: ChildProcessWithoutNullStreams | undefined;
  private handlers: TransportHandlers | undefined;
  private stdoutBuffer = "";
  private stderrBytes = 0;

  public constructor(
    private readonly maxLineBytes = 1_000_000,
    private readonly maxStderrBytes = 262_144
  ) {}

  public async start(options: TransportStartOptions, handlers: TransportHandlers): Promise<void> {
    if (this.child) throw new AppServerError("TRANSPORT_STATE", "Transport is already started.");
    this.handlers = handlers;
    const child = spawn(options.executable, options.args, {
      cwd: options.cwd,
      shell: false,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"]
    });
    this.child = child;
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => this.consumeStdout(chunk));
    child.stderr.on("data", (chunk: string) => this.consumeStderr(chunk));
    child.on("error", (error) => handlers.onError(error));
    child.on("exit", (code, signal) => handlers.onExit(code, signal));
  }

  public send(line: string): void {
    if (!this.child?.stdin.writable) throw new AppServerError("TRANSPORT_CLOSED", "App-server stdin is closed.");
    if (Buffer.byteLength(line, "utf8") > this.maxLineBytes) {
      throw new AppServerError("FRAME_TOO_LARGE", "Outbound app-server message exceeds its limit.");
    }
    this.child.stdin.write(`${line}\n`, "utf8");
  }

  public async close(): Promise<void> {
    const child = this.child;
    this.child = undefined;
    if (!child) return;
    child.stdin.end();
    if (child.exitCode === null && child.signalCode === null) child.kill();
  }

  private consumeStdout(chunk: string): void {
    this.stdoutBuffer += chunk;
    if (Buffer.byteLength(this.stdoutBuffer, "utf8") > this.maxLineBytes && !this.stdoutBuffer.includes("\n")) {
      this.handlers?.onError(new AppServerError("FRAME_TOO_LARGE", "Inbound app-server line exceeds its limit."));
      void this.close();
      return;
    }
    let newline = this.stdoutBuffer.indexOf("\n");
    while (newline >= 0) {
      const line = this.stdoutBuffer.slice(0, newline).replace(/\r$/, "");
      this.stdoutBuffer = this.stdoutBuffer.slice(newline + 1);
      if (Buffer.byteLength(line, "utf8") > this.maxLineBytes) {
        this.handlers?.onError(new AppServerError("FRAME_TOO_LARGE", "Inbound app-server line exceeds its limit."));
        void this.close();
        return;
      }
      this.handlers?.onLine(line);
      newline = this.stdoutBuffer.indexOf("\n");
    }
  }

  private consumeStderr(chunk: string): void {
    if (this.stderrBytes >= this.maxStderrBytes) return;
    const remaining = this.maxStderrBytes - this.stderrBytes;
    const bytes = Buffer.from(chunk, "utf8").subarray(0, remaining);
    this.stderrBytes += bytes.byteLength;
    this.handlers?.onStderr(new TextDecoder("utf8", { fatal: false }).decode(bytes));
  }
}

export class TranscriptTransport implements JsonLineTransport {
  public readonly sent: string[] = [];
  public startOptions: TransportStartOptions | undefined;
  private handlers: TransportHandlers | undefined;

  public constructor(private readonly onSend?: (value: Record<string, unknown>, transport: TranscriptTransport) => void) {}

  public async start(options: TransportStartOptions, handlers: TransportHandlers): Promise<void> {
    this.startOptions = options;
    this.handlers = handlers;
  }

  public send(line: string): void {
    this.sent.push(line);
    this.onSend?.(JSON.parse(line) as Record<string, unknown>, this);
  }

  public async close(): Promise<void> {
    this.handlers = undefined;
  }

  public receive(value: unknown): void {
    this.handlers?.onLine(JSON.stringify(value));
  }

  public receiveRaw(value: string): void {
    this.handlers?.onLine(value);
  }

  public stderr(value: string): void {
    this.handlers?.onStderr(value);
  }

  public exit(code: number | null = 0): void {
    this.handlers?.onExit(code, null);
  }
}
