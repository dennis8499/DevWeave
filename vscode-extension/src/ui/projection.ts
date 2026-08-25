import type { ControllerState } from "../controller/workspace-controller";

export interface UiProjection {
  source: "authoritative+projection";
  stale: boolean;
  status: string;
  run: Record<string, unknown> | null;
  preflight: Record<string, unknown> | null;
  threadId: string;
  turnId: string;
  appServer: ControllerState["appServer"];
  pendingApprovals: ControllerState["pendingApprovals"];
  review: ControllerState["review"];
  diagnostics: string[];
}

export function projectUiState(state: ControllerState): UiProjection {
  return {
    source: "authoritative+projection",
    stale: state.status !== "ready" || state.appServer.connection !== "connected",
    status: state.status,
    run: state.run ? structuredClone(state.run) : null,
    preflight: state.preflight ? structuredClone(state.preflight) : null,
    threadId: state.threadId,
    turnId: state.turnId,
    appServer: structuredClone(state.appServer),
    pendingApprovals: structuredClone(state.pendingApprovals),
    review: state.review ? structuredClone(state.review) : null,
    diagnostics: [...state.diagnostics].slice(-100)
  };
}
