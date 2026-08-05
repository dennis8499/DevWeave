import type { PlanModeGuidance, PublicCommandIntent, WorkspaceSnapshot } from "./model";

export function planModeGuidanceForIntent(intent: PublicCommandIntent, snapshot: WorkspaceSnapshot): PlanModeGuidance | undefined {
  if (["new", "feature", "refactor", "bug", "wikiBootstrap"].includes(intent.type)) {
    return { required: true, stage: "initial" };
  }
  if (intent.type !== "revise" && intent.type !== "approve") {
    return undefined;
  }
  const work = snapshot.workItems.find((item) => item.id === intent.workId);
  return work ? planModeGuidanceForPhase(work.phase) : undefined;
}

export function planModeGuidanceForPhase(phase: string): PlanModeGuidance | undefined {
  if (["requirements", "scope_review"].includes(phase)) {
    return { required: true, stage: "g1" };
  }
  if (["design", "build_review"].includes(phase)) {
    return { required: true, stage: "g2" };
  }
  if (["implementation", "verification", "acceptance_review"].includes(phase)) {
    return { required: false, stage: "post-g2" };
  }
  return undefined;
}
