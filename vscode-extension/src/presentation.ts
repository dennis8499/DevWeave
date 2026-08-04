import {
  AuditEventPresentation,
  CommandPresentation,
  Diagnostic,
  DiagnosticPresentation,
  GateName,
  ReviewCheck,
  ReviewReadiness,
  SnapshotGuidance,
  WorkItemProjection,
  WorkspaceSnapshot
} from "./model";

const COMMANDS: readonly CommandPresentation[] = [
  {
    name: "new",
    group: "start",
    label: "開始新工作",
    technicalLabel: "$devweave new",
    description: "從一個清楚的目標建立第一個工作項目。",
    requiresWork: false,
    mutation: true
  },
  {
    name: "feature",
    group: "start",
    label: "新增功能",
    technicalLabel: "$devweave feature",
    description: "描述要加入的使用者功能或產品行為。",
    requiresWork: false,
    mutation: true
  },
  {
    name: "refactor",
    group: "start",
    label: "整理程式",
    technicalLabel: "$devweave refactor",
    description: "整理既有程式，同時保留可驗證的行為。",
    requiresWork: false,
    mutation: true
  },
  {
    name: "bug",
    group: "start",
    label: "回報問題",
    technicalLabel: "$devweave bug",
    description: "用實際觀察到的症狀開始一個修正流程。",
    requiresWork: false,
    mutation: true
  },
  {
    name: "next",
    group: "progress",
    label: "詢問下一步",
    technicalLabel: "$devweave next",
    description: "請 engine 根據目前 work 回傳權威的下一步。",
    requiresWork: false,
    mutation: false
  },
  {
    name: "status",
    group: "progress",
    label: "查看目前狀態",
    technicalLabel: "$devweave status",
    description: "請 engine 回報 work、gate、evidence 與阻塞狀態。",
    requiresWork: false,
    mutation: false
  },
  {
    name: "revise",
    group: "review",
    label: "修改方向",
    technicalLabel: "$devweave revise",
    description: "修改目前決策；既有 gate 或 evidence 可能因此失效。",
    requiresWork: true,
    mutation: true
  },
  {
    name: "approve",
    group: "review",
    label: "核准目前階段",
    technicalLabel: "$devweave approve",
    description: "核准畫面標示的目前 gate，不在公開命令加入 gate 參數。",
    requiresWork: true,
    mutation: true
  },
  {
    name: "wikiBootstrap",
    group: "knowledge",
    label: "建立 Codebase Wiki",
    technicalLabel: "$devweave wiki bootstrap",
    description: "請 engine 探索 repository 並建立或補齊 Codebase Wiki。",
    requiresWork: false,
    mutation: true
  }
];

export function commandPresentations(): readonly CommandPresentation[] {
  return COMMANDS;
}

export function buildSnapshotGuidance(snapshot: WorkspaceSnapshot, selectedWork: WorkItemProjection | null): SnapshotGuidance {
  if (!snapshot.projectExists) {
    return {
      kind: "initialize",
      title: "先初始化這個 workspace",
      detail: "確認後 Extension 才會寫入固定 bootstrap bundle；完成後請確認 Codex hook、verification commands，再建立第一個 work。",
      authoritative: false
    };
  }

  if (snapshot.managed !== true) {
    return {
      kind: "setup",
      title: "先確認 DevWeave 管理狀態",
      detail: "目前 repository 沒有啟用 managed workflow；請在 Codex Chat 使用 status 確認，再 Refresh。",
      command: "status",
      authoritative: false
    };
  }

  const activeWorks = snapshot.workItems.filter((item) => item.status === "active");
  if (!selectedWork) {
    if (activeWorks.length === 0) {
      return {
        kind: "start",
        title: "開始一個新工作",
        detail: "目前沒有進行中的 work；可從開始新工作、回報問題或新增功能開始，不會自動把 closed history 當成目前工作。",
        command: "new",
        authoritative: false
      };
    }
    return {
      kind: "select",
      title: "選擇目前要查看的工作",
      detail: `目前有 ${activeWorks.length} 個進行中的 work；選取後即可查看該 work 的 gate、blocker 與下一步提示。`,
      command: "status",
      authoritative: false
    };
  }

  if (selectedWork.status === "closed" || selectedWork.phase === "closed") {
    return {
      kind: "closed",
      title: "這是已結束的歷史工作",
      detail: "目前只提供唯讀瀏覽；如要開始新方向，請建立新的 work，不會修改或重新開啟這筆歷史。",
      command: "new",
      authoritative: false
    };
  }

  if (selectedWork.blocker) {
    return {
      kind: "blocker",
      title: "先處理目前的阻塞",
      detail: `${selectedWork.blocker.task ?? "目前 task"}：${selectedWork.blocker.reason ?? "請在 Codex Chat 查看阻塞原因。"} Extension 只提供檔案快照提示；請用 next/status 取得 engine 判定。`,
      command: "next",
      workId: selectedWork.id,
      authoritative: false
    };
  }

  return {
    kind: "next",
    title: "詢問這個 work 的權威下一步",
    detail: "以下只是根據檔案快照的建議；複製 $devweave next 後到 Codex Chat 送出，完成後回到 Extension Refresh。",
    command: "next",
    workId: selectedWork.id,
    authoritative: false
  };
}

export function buildReviewReadiness(snapshot: WorkspaceSnapshot, work: WorkItemProjection | null): ReviewReadiness {
  if (!work || work.status === "closed" || work.phase === "closed") {
    return {
      gate: null,
      status: "closed",
      summary: "沒有可核准的進行中工作；歷史 work 僅供唯讀瀏覽。",
      checks: []
    };
  }

  const gate = nextGate(work);
  const checks: ReviewCheck[] = [
    diagnosticCheck(snapshot),
    blockerCheck(work),
    gateCheck(work, gate),
    taskCheck(work),
    evidenceCheck(work, gate),
    independentReviewCheck(work, gate),
    knowledgeCheck(work)
  ];
  const failed = checks.filter((check) => !check.ok);
  const status: ReviewReadiness["status"] = failed.length === 0
    ? "ready"
    : failed.some((check) => check.level === "critical" || check.key === "diagnostics" || check.key === "blocker" || check.key === "gate")
      ? "not_ready"
      : "attention";
  const summary = status === "ready"
    ? `${presentGate(gate)} 的審查條件目前看起來已備妥；這是檔案快照投影，送出 approve 前仍由 engine 驗證。`
    : status === "not_ready"
      ? `${presentGate(gate)} 目前未就緒，尚未具備完整審查條件，請先處理下方標示的問題。`
      : `${presentGate(gate)} 有需要留意的 task、evidence 或 Knowledge 狀態，建議先確認再審查。`;
  return { gate, status, summary, checks };
}

export function presentDiagnostic(diagnostic: Diagnostic): DiagnosticPresentation {
  const copy = diagnosticCopy[diagnostic.code] ?? {
    title: "需要注意的 workspace 問題",
    resolution: "先在 Codex Chat 使用 $devweave status 確認狀態，處理問題後再 Refresh。"
  };
  return {
    severity: diagnostic.severity,
    title: copy.title,
    detail: diagnostic.message,
    resolution: copy.resolution,
    code: diagnostic.code,
    ...(diagnostic.path ? { path: diagnostic.path } : {})
  };
}

export function presentAuditEvent(raw: string): AuditEventPresentation {
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value)) {
      throw new Error("event must be an object");
    }
    const event = stringValue(value.event ?? value.type ?? value.action ?? value.kind, "未知事件");
    const at = stringValue(value.at ?? value.created_at ?? value.timestamp ?? value.time, "時間未知");
    return {
      at,
      event,
      summary: auditSummary(event, value),
      raw
    };
  } catch {
    return {
      at: "時間未知",
      event: "格式無法解析",
      summary: "這筆稽核事件格式無法解析；請展開原始內容確認。",
      raw
    };
  }
}

export function presentStatus(value: string): string {
  return statusLabels[value] ?? (value || "未知");
}

export function presentPhase(value: string): string {
  return phaseLabels[value] ?? (value || "未知階段");
}

export function presentGate(value: string | null): string {
  if (!value) return "目前 gate";
  return gateLabels[value] ?? value;
}

export function presentRisk(value: string): string {
  return riskLabels[value] ?? (value || "未知風險");
}

function nextGate(work: WorkItemProjection): GateName | null {
  if (work.gates.scope.status !== "approved") return "scope";
  if (work.gates.build.status !== "approved") return "build";
  if (work.gates.acceptance.status !== "approved") return "acceptance";
  return null;
}

function diagnosticCheck(snapshot: WorkspaceSnapshot): ReviewCheck {
  const critical = snapshot.diagnostics.filter((item) => item.severity === "critical");
  return {
    key: "diagnostics",
    label: "Workspace contract",
    ok: critical.length === 0 && !snapshot.mutationBlocked,
    detail: critical.length === 0 ? "沒有 critical diagnostic。" : `${critical.length} 個 critical diagnostic 會阻止安全操作。`,
    nextStep: critical.length === 0 ? undefined : "先查看問題細節，使用 status 與 Codex Chat 修正後再 Refresh。"
  };
}

function blockerCheck(work: WorkItemProjection): ReviewCheck {
  return {
    key: "blocker",
    label: "目前阻塞",
    ok: !work.blocker,
    detail: work.blocker ? `${work.blocker.task ?? "Task"}: ${work.blocker.reason ?? "需要處理。"}` : "沒有記錄中的 blocker。",
    nextStep: work.blocker ? "先處理 blocker，再重新取得 engine status。" : undefined
  };
}

function gateCheck(work: WorkItemProjection, gate: GateName | null): ReviewCheck {
  if (!gate) {
    return { key: "gate", label: "目前 gate", ok: true, detail: "所有 gate 都已投影為核准。" };
  }
  const status = work.gates[gate].status;
  const reviewable = status === "pending" || status === "approved";
  return {
    key: "gate",
    label: `${presentGate(gate)} 狀態`,
    ok: reviewable,
    detail: status === "approved" ? "目前 gate 已核准。" : status === "pending" ? "目前 gate 等待 reviewer 審查；這是要確認的階段，不是缺失條件。" : `目前為「${presentStatus(status)}」，需要先重新取得 engine 狀態。`,
    nextStep: reviewable ? undefined : "在 Codex Chat 使用 next/status 取得 engine 的審查要求。"
  };
}

function taskCheck(work: WorkItemProjection): ReviewCheck {
  const incomplete = work.tasks.filter((task) => !["completed", "approved", "passed"].includes(task.status));
  return {
    key: "tasks",
    label: "工作任務",
    ok: incomplete.length === 0,
    detail: incomplete.length === 0 ? "已投影的 task 都已完成。" : `${incomplete.length} 個 task 尚未完成。`,
    nextStep: incomplete.length === 0 ? undefined : "依 task note 與 plan 順序處理未完成項目。"
  };
}

function evidenceCheck(work: WorkItemProjection, gate: GateName | null): ReviewCheck {
  const failed = work.evidence.filter((item) => item.status === "failed");
  const stale = work.evidence.filter((item) => item.stale || !item.bindsCurrentSource);
  const required = gate === "acceptance";
  const ok = failed.length === 0 && stale.length === 0 && (!required || work.evidence.length > 0);
  const detail = failed.length > 0
    ? `${failed.length} 個 evidence 失敗。`
    : stale.length > 0
      ? `${stale.length} 個 evidence 已過期或未綁定目前 source。`
      : required && work.evidence.length === 0
        ? "尚未有 acceptance 所需 evidence。"
        : "沒有 failed 或 stale evidence。";
  return {
    key: "evidence",
    label: "驗證 evidence",
    ok,
    detail,
    nextStep: ok ? undefined : "重新執行對應 verification，再回到 Extension Refresh。"
  };
}

function independentReviewCheck(work: WorkItemProjection, gate: GateName | null): ReviewCheck {
  if (gate !== "acceptance" || work.risk !== "high") {
    return {
      key: "independent-review",
      label: "Independent Review",
      ok: true,
      detail: "僅 high-risk G3 需要此檢查；目前風險或 gate 不適用。",
      level: "info"
    };
  }
  const current = work.evidence
    .filter((item) => item.kind === "review" && !item.stale && item.bindsCurrentSource)
    .sort((left, right) => left.id.localeCompare(right.id));
  const latest = current.at(-1);
  if (!latest?.review) {
    return {
      key: "independent-review",
      label: "Independent Review",
      ok: false,
      detail: "尚未有 current independent review；missing 或 unavailable 會需要人工留意。",
      nextStep: "在 Codex Chat 依 verification instructions 完成 Review Agent，再 Refresh。",
      level: "warning"
    };
  }
  const review = latest.review;
  if (review.result === "critical") {
    return {
      key: "independent-review",
      label: "Independent Review",
      ok: false,
      detail: `Review ${latest.id} 有 critical finding；G3 目前 not-ready。`,
      nextStep: "先處理 finding，或由人工依 engine 規則確認具名 narrow waiver。",
      level: "critical"
    };
  }
  if (review.result === "unavailable" || review.severity === "advisory" || review.findings.some((item) => item.severity === "advisory")) {
    return {
      key: "independent-review",
      label: "Independent Review",
      ok: false,
      detail: review.result === "unavailable"
        ? `Review ${latest.id} unavailable；可繼續人工 G3，但需要留意。`
        : `Review ${latest.id} 通過但包含 advisory finding；需要留意。`,
      nextStep: "查看 raw evidence 與 report findings，再由人工確認是否繼續。",
      level: "warning"
    };
  }
  return {
    key: "independent-review",
    label: "Independent Review",
    ok: review.result === "passed",
    detail: review.result === "passed" ? `Review ${latest.id} 已針對目前 source 通過。` : `Review ${latest.id} 結果需要 engine 重新確認。`,
    nextStep: review.result === "passed" ? undefined : "在 Codex Chat 使用 status 取得 engine 的 review 判定。",
    level: review.result === "passed" ? "info" : "warning"
  };
}

function knowledgeCheck(work: WorkItemProjection): ReviewCheck {
  const knowledge = work.knowledge;
  const pending = [...knowledge.pendingRefresh, ...knowledge.uncoveredChangedPaths];
  const reviewMissing = knowledge.review.required && !knowledge.review.current;
  const ok = pending.length === 0 && !reviewMissing;
  return {
    key: "knowledge",
    label: "Knowledge 更新",
    ok,
    detail: ok ? "沒有待更新的 Knowledge 頁面。" : `${pending.length} 個 Knowledge 路徑待處理${reviewMissing ? "，且 Knowledge Review 尚未完成" : ""}。`,
    nextStep: ok ? undefined : "查看受影響頁面；verification 階段依 Knowledge Review 決定 promote 或 no-update。"
  };
}

const diagnosticCopy: Record<string, { title: string; resolution: string }> = {
  project_missing: { title: "尚未初始化 DevWeave", resolution: "使用「初始化 DevWeave」開始；這是唯一會在確認後寫入固定 bootstrap bundle 的操作。" },
  project_invalid: { title: "DevWeave 設定檔無法讀取", resolution: "不要覆寫檔案；先在 Codex Chat 使用 status 確認並修正 project.json，再 Refresh。" },
  managed_missing: { title: "缺少 workspace 管理設定", resolution: "在 Codex Chat 確認 managed workflow 設定，修正後再 Refresh。" },
  managed_disabled: { title: "這個 workspace 尚未啟用 managed workflow", resolution: "先確認是否要啟用 DevWeave；Extension 不會自行修改 managed 設定。" },
  hook_missing: { title: "Codex hook 尚未就緒", resolution: "完成初始化或依 repository 指引確認 hook，之後回到 Extension Refresh。" },
  skill_missing: { title: "DevWeave skill 尚未就緒", resolution: "確認 repository 的 DevWeave skill 已存在，再重新整理 snapshot。" },
  unsupported_schema: { title: "DevWeave schema 版本不支援", resolution: "請在 Codex Chat 取得相容性建議；Extension 不會自行 migration 或覆寫狀態。" },
  json_parse: { title: "某個 DevWeave JSON 無法解析", resolution: "先備份並修正格式，再使用 status 確認 contract；critical 狀態下不會執行 mutation。" },
  commands_invalid: { title: "Verification command 設定不完整", resolution: "補上 verification commands/profile，讓後續驗證能有明確執行項目。" },
  workspace_unavailable: { title: "尚未選擇可讀取的 workspace", resolution: "選擇一個 VS Code repository 後重新開啟 Control Center。" }
};

const statusLabels: Record<string, string> = {
  approved: "已核准",
  pending: "待處理",
  stale: "已過期",
  passed: "已通過",
  failed: "失敗",
  completed: "已完成",
  in_progress: "進行中",
  blocked: "已阻塞",
  active: "進行中",
  closed: "已結束",
  healthy: "正常",
  warning: "需要注意",
  critical: "嚴重問題",
  placeholder: "待補內容",
  success: "成功"
};

const phaseLabels: Record<string, string> = {
  requirements: "需求整理",
  scope_review: "G1 範圍審查",
  design: "設計",
  build_review: "G2 建置審查",
  implementation: "實作",
  verification: "驗證",
  acceptance_review: "G3 驗收審查",
  closed: "已結束"
};

const gateLabels: Record<string, string> = {
  scope: "G1 範圍",
  build: "G2 設計與建置",
  acceptance: "G3 驗收"
};

const riskLabels: Record<string, string> = {
  low: "低風險",
  standard: "一般風險",
  high: "高風險"
};

function auditSummary(event: string, value: Record<string, unknown>): string {
  const normalized = event.toLowerCase();
  if (normalized.includes("approved") || normalized.includes("approve")) {
    return `已記錄核准事件${value.gate ? `：${String(value.gate)}` : ""}。`;
  }
  if (normalized.includes("revise")) return "已記錄決策修改；既有審查結果可能需要重新確認。";
  if (normalized.includes("evidence")) return "已記錄驗證 evidence 變化。";
  if (normalized.includes("task")) return "已記錄工作 task 狀態變化。";
  if (normalized.includes("bootstrap")) return "已記錄初始化或 Wiki bootstrap 事件。";
  return `已記錄「${event}」事件。`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}
