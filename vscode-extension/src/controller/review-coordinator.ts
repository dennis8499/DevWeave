import { bounded, isRecord } from "../app-server/protocol";
import type { ReviewFinding, RiskLevel } from "../v2/contracts";

export interface ReviewRequestPort {
  request(method: "review/start", params: unknown): Promise<unknown>;
  waitForReviewResult?(reviewerThreadId: string, reviewTurnId?: string): Promise<unknown>;
}

export interface ReviewOutcome {
  status: "passed" | "blocked";
  result: "passed" | "failed";
  severity: "advisory" | "warning" | "critical";
  sourceFingerprint: string;
  round: number;
  reviewerThreadId: string;
  reviewTurnId: string;
  findings: ReviewFinding[];
  unresolvedCritical: boolean;
  protocolValid: boolean;
}

interface ReviewBinding {
  round: number;
  sourceFingerprint: string;
  implementationThreadId: string;
  reviewerThreadId: string;
  reviewTurnId: string;
}

const ENVELOPE_FIELDS = ["schema_version", "result", "severity", "source_fingerprint", "round", "findings"].sort();
const FINDING_FIELDS = [
  "schema_version", "finding_id", "severity", "summary", "paths",
  "requirement_ids", "acceptance_ids", "task_ids", "status", "round"
].sort();

export class ReviewCoordinator {
  public constructor(private readonly appServer: ReviewRequestPort) {}

  public async run(
    risk: RiskLevel,
    implementationThreadId: string,
    baseBranch: string,
    sourceFingerprint: string,
    fixAndReverify: (round: number, findings: ReviewFinding[]) => Promise<string>
  ): Promise<ReviewOutcome> {
    if (!isSha256(sourceFingerprint)) {
      return protocolFailure(1, sourceFingerprint, implementationThreadId, "", "", "Current verification fingerprint is unavailable.");
    }
    if (risk === "low") {
      return {
        status: "passed", result: "passed", severity: "advisory", sourceFingerprint,
        round: 1, reviewerThreadId: "self-review", reviewTurnId: "self-review",
        findings: [], unresolvedCritical: false, protocolValid: true
      };
    }
    const maxRounds = risk === "high" ? 3 : 1;
    let expectedSource = sourceFingerprint;
    let last: ReviewOutcome | undefined;
    for (let round = 1; round <= maxRounds; round += 1) {
      let response: unknown;
      let reviewerId = "";
      let reviewTurnId = "";
      try {
        response = await this.appServer.request("review/start", {
          threadId: implementationThreadId,
          delivery: "detached",
          target: {
            type: "custom",
            instructions: reviewInstructions(baseBranch, expectedSource, round)
          }
        });
        const initial = isRecord(response) ? response : {};
        reviewerId = typeof initial.reviewThreadId === "string"
          ? bounded(initial.reviewThreadId, 256)
          : typeof initial.threadId === "string" ? bounded(initial.threadId, 256)
            : typeof initial.thread_id === "string" ? bounded(initial.thread_id, 256) : "";
        const reviewTurn = record(initial.turn);
        reviewTurnId = typeof reviewTurn.id === "string" ? bounded(reviewTurn.id, 256) : "";
        if (!reviewerId || !reviewTurnId || !this.appServer.waitForReviewResult) {
          return protocolFailure(round, expectedSource, implementationThreadId, reviewerId, reviewTurnId, "Detached review transport binding is incomplete.");
        }
        const completed = await this.appServer.waitForReviewResult(reviewerId, reviewTurnId);
        response = completed;
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return protocolFailure(round, expectedSource, implementationThreadId, reviewerId, reviewTurnId, message);
      }
      const parsed = parseReviewResponse(response, {
        round,
        sourceFingerprint: expectedSource,
        implementationThreadId,
        reviewerThreadId: reviewerId,
        reviewTurnId
      });
      if (!reviewerId || reviewerId === implementationThreadId) {
        return protocolFailure(round, expectedSource, implementationThreadId, reviewerId, reviewTurnId, "Review thread is not detached.");
      }
      last = parsed;
      if (parsed.status === "passed") return parsed;
      if (!parsed.protocolValid || risk !== "high" || round === maxRounds) return parsed;
      expectedSource = await fixAndReverify(round, parsed.findings);
      if (!isSha256(expectedSource)) {
        return protocolFailure(round, expectedSource, implementationThreadId, reviewerId, reviewTurnId, "Fix/reverify did not produce a current fingerprint.");
      }
    }
    return last ?? protocolFailure(maxRounds, expectedSource, implementationThreadId, "", "", "Review produced no result.");
  }
}

export function parseReviewResponse(value: unknown, binding: ReviewBinding): ReviewOutcome {
  const response = isRecord(value) ? value : {};
  if (typeof response.text !== "string") {
    return protocolFailure(binding.round, binding.sourceFingerprint, binding.implementationThreadId, binding.reviewerThreadId, binding.reviewTurnId, "Review result has no exact JSON text.");
  }
  let envelope: unknown;
  try {
    envelope = JSON.parse(response.text.trim());
  } catch {
    return protocolFailure(binding.round, binding.sourceFingerprint, binding.implementationThreadId, binding.reviewerThreadId, binding.reviewTurnId, "Review result is not exact JSON.");
  }
  if (!isRecord(envelope) || !sameFields(envelope, ENVELOPE_FIELDS)) {
    return protocolFailure(binding.round, binding.sourceFingerprint, binding.implementationThreadId, binding.reviewerThreadId, binding.reviewTurnId, "Review envelope fields are malformed.");
  }
  if (
    envelope.schema_version !== 2
    || (envelope.result !== "passed" && envelope.result !== "failed")
    || !isSeverity(envelope.severity)
    || envelope.source_fingerprint !== binding.sourceFingerprint
    || envelope.round !== binding.round
    || !Array.isArray(envelope.findings)
    || envelope.findings.length > 128
  ) {
    return protocolFailure(binding.round, binding.sourceFingerprint, binding.implementationThreadId, binding.reviewerThreadId, binding.reviewTurnId, "Review envelope binding is contradictory.");
  }
  const findings: ReviewFinding[] = [];
  try {
    for (let index = 0; index < envelope.findings.length; index += 1) {
      findings.push(parseFinding(envelope.findings[index], binding.round, index));
    }
  } catch (error) {
    return protocolFailure(
      binding.round, binding.sourceFingerprint, binding.implementationThreadId,
      binding.reviewerThreadId, binding.reviewTurnId,
      error instanceof Error ? error.message : "Review finding is malformed."
    );
  }
  if (new Set(findings.map((item) => item.finding_id)).size !== findings.length) {
    return protocolFailure(binding.round, binding.sourceFingerprint, binding.implementationThreadId, binding.reviewerThreadId, binding.reviewTurnId, "Review finding ids are duplicated.");
  }
  const calculated = findings.reduce<ReviewOutcome["severity"]>(
    (current, finding) => severityRank(finding.severity) > severityRank(current) ? finding.severity : current,
    "advisory"
  );
  if (calculated !== envelope.severity) {
    return protocolFailure(binding.round, binding.sourceFingerprint, binding.implementationThreadId, binding.reviewerThreadId, binding.reviewTurnId, "Review severity contradicts its findings.");
  }
  const unresolvedCritical = findings.some((item) => item.severity === "critical" && item.status === "open");
  const passed = envelope.result === "passed" && !unresolvedCritical;
  return {
    status: passed ? "passed" : "blocked",
    result: envelope.result,
    severity: envelope.severity,
    sourceFingerprint: binding.sourceFingerprint,
    round: binding.round,
    reviewerThreadId: binding.reviewerThreadId,
    reviewTurnId: binding.reviewTurnId,
    findings,
    unresolvedCritical,
    protocolValid: true
  };
}

function reviewInstructions(baseBranch: string, sourceFingerprint: string, round: number): string {
  return [
    `Review all changes on the current branch against base branch ${JSON.stringify(baseBranch)} in read-only mode.`,
    "Return exactly one JSON object with no Markdown fence or prose.",
    `Use schema_version 2, source_fingerprint ${sourceFingerprint}, and round ${round}.`,
    "Required fields: schema_version,result,severity,source_fingerprint,round,findings.",
    "result is passed or failed; severity is advisory, warning, or critical.",
    "Each finding must contain exactly schema_version,finding_id,severity,summary,paths,requirement_ids,acceptance_ids,task_ids,status,round.",
    "Finding status is open, resolved, or accepted. Use an empty findings array only when no findings exist."
  ].join(" ");
}

function parseFinding(value: unknown, round: number, index: number): ReviewFinding {
  if (!isRecord(value) || !sameFields(value, FINDING_FIELDS)) throw new Error(`Review finding ${index + 1} fields are malformed.`);
  if (
    value.schema_version !== 2
    || typeof value.finding_id !== "string"
    || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value.finding_id)
    || !isSeverity(value.severity)
    || typeof value.summary !== "string"
    || value.summary.length === 0
    || value.summary.length > 4_096
    || (value.status !== "open" && value.status !== "resolved" && value.status !== "accepted")
    || value.round !== round
  ) throw new Error(`Review finding ${index + 1} values are malformed.`);
  return {
    schema_version: 2,
    finding_id: value.finding_id,
    severity: value.severity,
    summary: value.summary,
    paths: pathArray(value.paths, "paths"),
    requirement_ids: stringArray(value.requirement_ids, "requirement_ids"),
    acceptance_ids: stringArray(value.acceptance_ids, "acceptance_ids"),
    task_ids: stringArray(value.task_ids, "task_ids"),
    status: value.status,
    round: round as 1 | 2 | 3
  };
}

function protocolFailure(
  round: number,
  sourceFingerprint: string,
  implementationThreadId: string,
  reviewerThreadId: string,
  reviewTurnId: string,
  message: string
): ReviewOutcome {
  const finding: ReviewFinding = {
    schema_version: 2,
    finding_id: "DEVWEAVE-REVIEW-PROTOCOL",
    severity: "critical",
    summary: bounded(message || "Detached review protocol failed.", 4_096),
    paths: [], requirement_ids: [], acceptance_ids: [], task_ids: [], status: "open",
    round: Math.min(3, Math.max(1, round)) as 1 | 2 | 3
  };
  return {
    status: "blocked", result: "failed", severity: "critical", sourceFingerprint,
    round, reviewerThreadId, reviewTurnId, findings: [finding], unresolvedCritical: true, protocolValid: false
  };
}

function sameFields(value: Record<string, unknown>, fields: string[]): boolean {
  return JSON.stringify(Object.keys(value).sort()) === JSON.stringify(fields);
}

function stringArray(value: unknown, name: string): string[] {
  if (!Array.isArray(value) || value.length > 256 || !value.every((item) => typeof item === "string" && item.length <= 512)) {
    throw new Error(`Review finding ${name} is malformed.`);
  }
  const result = value as string[];
  if (new Set(result).size !== result.length) throw new Error(`Review finding ${name} contains duplicates.`);
  return result;
}

function pathArray(value: unknown, name: string): string[] {
  const paths = stringArray(value, name);
  if (paths.some((item) => item.startsWith("/") || /^[A-Za-z]:[\\/]/.test(item) || item.replaceAll("\\", "/").split("/").includes(".."))) {
    throw new Error(`Review finding ${name} contains a non-relative path.`);
  }
  return paths;
}

function severityRank(value: ReviewOutcome["severity"]): number {
  return value === "critical" ? 2 : value === "warning" ? 1 : 0;
}

function isSeverity(value: unknown): value is ReviewOutcome["severity"] {
  return value === "advisory" || value === "warning" || value === "critical";
}

function isSha256(value: string): boolean {
  return /^[0-9a-f]{64}$/.test(value);
}

function record(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}
