export interface RefreshChangeSet {
  readonly paths: readonly string[];
  readonly forceFull: boolean;
}

export interface RefreshCoordinatorOptions<T> {
  read(changes: RefreshChangeSet): Promise<T>;
  publish(value: T): void;
  onError?(error: unknown): void;
}

export class RefreshCoordinator<T> {
  private pending = false;
  private cycle: Promise<T> | null = null;
  private disposed = false;
  private pendingPaths = new Set<string>();
  private pendingForceFull = false;

  public constructor(private readonly options: RefreshCoordinatorOptions<T>) {}

  public request(changes: Partial<RefreshChangeSet> = {}): Promise<T> {
    if (this.disposed) {
      return Promise.reject(new Error("RefreshCoordinator has been disposed."));
    }
    if (changes.forceFull ?? changes.paths === undefined) {
      this.pendingForceFull = true;
    }
    for (const path of changes.paths ?? []) {
      this.pendingPaths.add(path);
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
    this.pendingPaths.clear();
    this.pendingForceFull = false;
  }

  private async drain(): Promise<T> {
    let latest!: T;
    while (true) {
      this.pending = false;
      const changes: RefreshChangeSet = {
        paths: [...this.pendingPaths].sort(),
        forceFull: this.pendingForceFull
      };
      this.pendingPaths.clear();
      this.pendingForceFull = false;
      let value: T;
      try {
        value = await this.options.read(changes);
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
