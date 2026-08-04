export type ScheduleFrame = (callback: () => void) => void;

export class RenderScheduler {
  private queued = false;

  public constructor(
    private readonly render: () => void,
    private readonly scheduleFrame: ScheduleFrame
  ) {}

  public request(): void {
    if (this.queued) return;
    this.queued = true;
    this.scheduleFrame(() => {
      this.queued = false;
      this.render();
    });
  }
}
