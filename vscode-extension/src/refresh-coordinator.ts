export interface RefreshCoordinatorOptions<T> {
  read(): Promise<T>;
  publish(value: T): void;
  onError?(error: unknown): void;
}

export class RefreshCoordinator<T> {
  private pending = false;
  private cycle: Promise<T> | null = null;
  private disposed = false;

  public constructor(private readonly options: RefreshCoordinatorOptions<T>) {}

  public request(): Promise<T> {
    if (this.disposed) {
      return Promise.reject(new Error("RefreshCoordinator has been disposed."));
    }
    this.pending = true;
    if (!this.cycle) {
      this.cycle = this.drain().finally(() => {
        this.cycle = null;
      });
    }
    return this.cycle;
  }

  public dispose(): void {
    this.disposed = true;
    this.pending = false;
  }

  private async drain(): Promise<T> {
    let latest!: T;
    while (true) {
      this.pending = false;
      let value: T;
      try {
        value = await this.options.read();
      } catch (error) {
        this.options.onError?.(error);
        throw error;
      }
      latest = value;
      if (!this.disposed && !this.pending) {
        this.options.publish(value);
      }
      if (!this.pending) {
        return latest;
      }
    }
  }
}
