import { bounded, isRecord } from "../app-server/protocol";
import type { ReviewFinding, RiskLevel } from "../v2/contracts";

export interface ReviewRequestPort {
  request(method: "review/start", params: unknown): Promise<unknown>;
  waitForReviewResult?(reviewerThreadId: string): Promise<unknown>;
}

export interface ReviewOutcome {
  status: "passed" | "blocked";
  round: number;
  reviewerThreadId: string;
  findings: ReviewFinding[];
  unresolvedCritical: boolean;
}

export class ReviewCoordinator {
  public constructor(private readonly appServer: ReviewRequestPort) {}

  public async run(
    risk: RiskLevel,
    implementationThreadId: string,
    baseBranch: string,
    fixAndReverify: (round: number, findings: ReviewFinding[]) => Promise<void>
  ): Promise<ReviewOutcome> {
    if (risk === "low") {
      return { status: "passed", round: 1, reviewerThreadId: "self-review", findings: [], unresolvedCritical: false };
    }
    const maxRounds = risk === "high" ? 3 : 1;
    let last: ReviewOutcome | undefined;
    for (let round = 1; round <= maxRounds; round += 1) {
      let response = await this.appServer.request("review/start", {
        threadId: implementationThreadId,
        delivery: "detached",
        target: { type: "baseBranch", branch: baseBranch }
      });
      const initial = isRecord(response) ? response : {};
      const reviewerId = typeof initial.reviewThreadId === "string"
        ? initial.reviewThreadId
        : typeof initial.threadId === "string" ? initial.threadId : typeof initial.thread_id === "string" ? initial.thread_id : "";
      if (!Array.isArray(initial.findings) && typeof initial.text !== "string" && reviewerId && this.appServer.waitForReviewResult) {
        const completed = await this.appServer.waitForReviewResult(reviewerId);
        response = { ...record(completed), threadId: reviewerId };
      }
      const parsed = parseReviewResponse(response, round);
      if (!parsed.reviewerThreadId || parsed.reviewerThreadId === implementationThreadId) {
        return { ...parsed, status: "blocked", unresolvedCritical: true };
      }
      last = parsed;
      if (!parsed.unresolvedCritical) return parsed;
      if (risk !== "high" || round === maxRounds) return { ...parsed, status: "blocked" };
      await fixAndReverify(round, parsed.findings);
    }
    return last ?? { status: "blocked", round: maxRounds, reviewerThreadId: "", findings: [], unresolvedCritical: true };
  }
}

export function parseReviewResponse(value: unknown, round: number): ReviewOutcome {
  const response = isRecord(value) ? value : {};
  const reviewerThreadId = typeof response.threadId === "string"
    ? bounded(response.threadId, 256)
    : typeof response.reviewThreadId === "string"
      ? bounded(response.reviewThreadId, 256)
      : typeof response.thread_id === "string" ? bounded(response.thread_id, 256) : "";
  const findings = Array.isArray(response.findings)
    ? response.findings.slice(0, 128).map((item, index) => parseFinding(item, round, index))
    : parseFindingText(typeof response.text === "string" ? response.text : "", round);
  const unresolvedCritical = findings.some((item) => item.severity === "critical" && item.status === "open");
  return {
    status: unresolvedCritical ? "blocked" : "passed",
    round,
    reviewerThreadId,
    findings,
    unresolvedCritical
  };
}

function parseFinding(value: unknown, round: number, index: number): ReviewFinding {
  const item = isRecord(value) ? value : {};
  const severity = item.severity === "critical" || item.severity === "warning" ? item.severity : "advisory";
  const status = item.status === "resolved" || item.status === "accepted" ? item.status : "open";
  return {
    schema_version: 2,
    finding_id: typeof item.id === "string" ? bounded(item.id, 128) : `FIND-${round}-${index + 1}`,
    severity,
    summary: bounded(item.summary ?? "Review finding", 4_096),
    paths: stringArray(item.paths),
    requirement_ids: stringArray(item.requirement_ids),
    acceptance_ids: stringArray(item.acceptance_ids),
    task_ids: stringArray(item.task_ids),
    status,
    round: round as 1 | 2 | 3
  };
}

function parseFindingText(text: string, round: number): ReviewFinding[] {
  return text.split(/\r?\n/).slice(0, 128).flatMap((line, index) => {
    const match = /^(CRITICAL|WARNING|ADVISORY)\s*(?:\[([^\]]+)\])?\s*(.*)$/i.exec(line.trim());
    if (!match) return [];
    return [parseFinding({ id: match[2] || `FIND-${round}-${index + 1}`, severity: match[1].toLowerCase(), summary: match[3] }, round, index)];
  });
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").slice(0, 256).map((item) => bounded(item, 512)) : [];
}

function record(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}
