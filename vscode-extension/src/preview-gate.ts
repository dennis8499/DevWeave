import type { PromptBundle, PublicCommandIntent } from "./model";

export interface PreviewTicket {
  id: number;
  panelId: string;
  revision: number;
  intent: PublicCommandIntent;
  bundle: PromptBundle;
  epoch: number;
}

/**
 * Keeps the preview/copy contract in one host-side, side-effect-free module.
 * Clipboard adapters decide what to do with a taken bundle; this module only
 * decides whether that bundle is still the one the user previewed.
 */
export class PreviewGate {
  private current: PreviewTicket | null = null;
  private epoch = 0;
  private nextId = 0;
  private readonly restoredIds = new Set<number>();

  public stage(
    panelId: string,
    intent: PublicCommandIntent,
    revision: number,
    bundle: PromptBundle
  ): PreviewTicket {
    const ticket: PreviewTicket = {
      id: ++this.nextId,
      panelId,
      revision,
      intent,
      bundle,
      epoch: this.epoch
    };
    this.current = ticket;
    this.restoredIds.clear();
    return ticket;
  }

  public take(
    panelId: string,
    intent: PublicCommandIntent,
    revision: number
  ): PreviewTicket | null {
    const ticket = this.current;
    if (!ticket || ticket.epoch !== this.epoch) {
      return null;
    }
    if (ticket.panelId !== panelId || ticket.revision !== revision || !sameIntent(ticket.intent, intent)) {
      return null;
    }
    this.current = null;
    return ticket;
  }

  /**
   * Restore one failed clipboard attempt. A ticket may be restored once; a
   * later retry must either succeed or create a fresh preview.
   */
  public restore(ticket: PreviewTicket): boolean {
    if (
      ticket.epoch !== this.epoch
      || this.current !== null
      || this.restoredIds.has(ticket.id)
    ) {
      return false;
    }
    this.current = ticket;
    this.restoredIds.add(ticket.id);
    return true;
  }

  public invalidate(): void {
    this.epoch += 1;
    this.current = null;
    this.restoredIds.clear();
  }
}

function sameIntent(left: PublicCommandIntent, right: PublicCommandIntent): boolean {
  switch (left.type) {
    case "new":
      return right.type === "new" && left.goal === right.goal;
    case "feature":
      return right.type === "feature" && left.request === right.request;
    case "refactor":
      return right.type === "refactor" && left.request === right.request;
    case "bug":
      return right.type === "bug" && left.symptom === right.symptom;
    case "next":
      return right.type === "next" && left.workId === right.workId;
    case "status":
      return right.type === "status" && left.workId === right.workId && left.all === right.all;
    case "wikiBootstrap":
      return right.type === "wikiBootstrap";
    case "revise":
      return right.type === "revise" && left.workId === right.workId && left.change === right.change;
    case "approve":
      return right.type === "approve" && left.workId === right.workId;
  }
}
