import { createHash } from "node:crypto";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { basename, dirname } from "node:path";

import { bounded } from "../app-server/protocol";

const DEFAULT_LOG_LIMIT_BYTES = 262_144;
const DEFAULT_SCREENSHOT_LIMIT_BYTES = 5_000_000;
const MAX_ASSERTIONS = 256;
const MAX_SCREENSHOTS = 32;

export interface UiEvidenceProvenance {
  runId: string;
  commit: string;
  codexVersion: string;
  schemaHash: string;
}

export interface UiEvidenceAssertion {
  name: string;
  passed: boolean;
  details: string;
}

export interface UiEvidenceLog {
  source: string;
  message: string;
}

export interface UiEvidenceScreenshot {
  name: string;
  byteLength: number;
  sha256: string;
}

export interface UiEvidenceReport {
  schemaVersion: 2;
  kind: "devweave-ui-evidence";
  capturedAt: string;
  provenance: UiEvidenceProvenance;
  assertions: UiEvidenceAssertion[];
  logs: UiEvidenceLog[];
  screenshots: UiEvidenceScreenshot[];
  allPassed: boolean;
  limits: { logBytes: number; screenshotBytes: number };
}

export interface UiEvidenceOptions {
  logLimitBytes?: number;
  screenshotLimitBytes?: number;
  now?: () => Date;
}

export class UiEvidenceCollector {
  private readonly assertions: UiEvidenceAssertion[] = [];
  private readonly logs: UiEvidenceLog[] = [];
  private readonly screenshots: UiEvidenceScreenshot[] = [];
  private readonly capturedAt: string;
  private readonly logLimitBytes: number;
  private readonly screenshotLimitBytes: number;
  private logBytes = 0;

  public constructor(
    private readonly provenance: UiEvidenceProvenance,
    options: UiEvidenceOptions = {}
  ) {
    validateProvenance(provenance);
    this.logLimitBytes = positiveLimit(options.logLimitBytes ?? DEFAULT_LOG_LIMIT_BYTES, "logLimitBytes");
    this.screenshotLimitBytes = positiveLimit(options.screenshotLimitBytes ?? DEFAULT_SCREENSHOT_LIMIT_BYTES, "screenshotLimitBytes");
    this.capturedAt = (options.now ?? (() => new Date()))().toISOString();
  }

  public addAssertion(name: string, passed: boolean, details = ""): void {
    if (this.assertions.length >= MAX_ASSERTIONS) throw new Error("UI evidence assertion limit exceeded.");
    const normalizedName = requiredText(name, "assertion name", 128);
    if (this.assertions.some((item) => item.name === normalizedName)) {
      throw new Error(`Duplicate UI evidence assertion: ${normalizedName}`);
    }
    this.assertions.push({ name: normalizedName, passed, details: bounded(details, 4_096) });
  }

  public addLog(source: string, message: unknown): boolean {
    const normalizedSource = requiredText(source, "log source", 128);
    const normalizedMessage = bounded(message, 8_192);
    const remaining = this.logLimitBytes - this.logBytes;
    if (remaining <= 0) return false;
    const entry = {
      source: normalizedSource,
      message: sliceUtf8(normalizedMessage, Math.max(0, remaining - Buffer.byteLength(normalizedSource, "utf8")))
    };
    const bytes = Buffer.byteLength(entry.source, "utf8") + Buffer.byteLength(entry.message, "utf8");
    if (!entry.message || bytes > remaining) return false;
    this.logs.push(entry);
    this.logBytes += bytes;
    return true;
  }

  public async registerScreenshot(path: string): Promise<UiEvidenceScreenshot> {
    if (this.screenshots.length >= MAX_SCREENSHOTS) throw new Error("UI evidence screenshot limit exceeded.");
    const metadata = await stat(path);
    if (!metadata.isFile()) throw new Error("UI evidence screenshot must be a regular file.");
    if (metadata.size <= 0 || metadata.size > this.screenshotLimitBytes) {
      throw new Error(`UI evidence screenshot must be between 1 and ${this.screenshotLimitBytes} bytes.`);
    }
    const bytes = await readFile(path);
    const screenshot = {
      name: bounded(basename(path), 256),
      byteLength: bytes.byteLength,
      sha256: createHash("sha256").update(bytes).digest("hex")
    };
    this.screenshots.push(screenshot);
    return { ...screenshot };
  }

  public report(): UiEvidenceReport {
    return {
      schemaVersion: 2,
      kind: "devweave-ui-evidence",
      capturedAt: this.capturedAt,
      provenance: { ...this.provenance },
      assertions: this.assertions.map((item) => ({ ...item })),
      logs: this.logs.map((item) => ({ ...item })),
      screenshots: this.screenshots.map((item) => ({ ...item })),
      allPassed: this.assertions.length > 0 && this.assertions.every((item) => item.passed),
      limits: { logBytes: this.logLimitBytes, screenshotBytes: this.screenshotLimitBytes }
    };
  }

  public async write(path: string): Promise<UiEvidenceReport> {
    const report = this.report();
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, `${canonicalJson(report)}\n`, { encoding: "utf8", flag: "w" });
    return report;
  }
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortValue(value));
}

function validateProvenance(value: UiEvidenceProvenance): void {
  requiredText(value.runId, "runId", 128);
  requiredText(value.codexVersion, "codexVersion", 512);
  if (!/^[a-f0-9]{7,64}$/i.test(value.commit)) throw new Error("UI evidence commit must be a Git object id.");
  if (!/^[a-f0-9]{64}$/i.test(value.schemaHash)) throw new Error("UI evidence schemaHash must be SHA-256.");
}

function requiredText(value: string, field: string, maximum: number): string {
  if (typeof value !== "string" || !value.trim() || value.length > maximum) {
    throw new Error(`UI evidence ${field} is invalid.`);
  }
  return value.trim();
}

function positiveLimit(value: number, field: string): number {
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`UI evidence ${field} must be a positive integer.`);
  return value;
}

function sliceUtf8(value: string, maximumBytes: number): string {
  if (maximumBytes <= 0) return "";
  const bytes = Buffer.from(value, "utf8");
  if (bytes.byteLength <= maximumBytes) return value;
  return bytes.subarray(0, maximumBytes).toString("utf8").replace(/\uFFFD$/u, "");
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (typeof value !== "object" || value === null) return value;
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, sortValue(item)])
  );
}
