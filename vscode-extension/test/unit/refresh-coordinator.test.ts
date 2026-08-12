import test from "node:test";
import assert from "node:assert/strict";
import { RefreshCoordinator } from "../../src/refresh-coordinator";

function deferred<T>(): { promise: Promise<T>; resolve(value: T): void; reject(error: unknown): void } {
  let resolvePromise!: (value: T) => void;
  let rejectPromise!: (error: unknown) => void;
  const promise = new Promise<T>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, resolve: resolvePromise, reject: rejectPromise };
}

async function yieldToRefresh(): Promise<void> {
  await new Promise<void>((resolve) => setImmediate(resolve));
}

test("RefreshCoordinator never overlaps reads and publishes the newest pending snapshot", async () => {
  const reads: Array<ReturnType<typeof deferred<string>>> = [];
  const published: string[] = [];
  let inFlight = 0;
  let maxInFlight = 0;
  const coordinator = new RefreshCoordinator<string>({
    read: async () => {
      inFlight += 1;
      maxInFlight = Math.max(maxInFlight, inFlight);
      const result = deferred<string>();
      reads.push(result);
      const value = await result.promise;
      inFlight -= 1;
      return value;
    },
    publish: (value) => published.push(value)
  });

  const first = coordinator.request();
  const second = coordinator.request();
  const third = coordinator.request();
  await yieldToRefresh();
  assert.equal(reads.length, 1);
  assert.equal(maxInFlight, 1);

  reads[0]?.resolve("stale");
  await yieldToRefresh();
  assert.equal(reads.length, 2);
  assert.equal(maxInFlight, 1);

  reads[1]?.resolve("latest");
  assert.deepEqual(await Promise.all([first, second, third]), ["latest", "latest", "latest"]);
  assert.deepEqual(published, ["latest"]);
  assert.equal(maxInFlight, 1);
});

test("RefreshCoordinator reports a read failure and accepts a later retry", async () => {
  const reads: Array<ReturnType<typeof deferred<string>>> = [];
  const errors: unknown[] = [];
  const coordinator = new RefreshCoordinator<string>({
    read: () => {
      const result = deferred<string>();
      reads.push(result);
      return result.promise;
    },
    publish: () => undefined,
    onError: (error) => errors.push(error)
  });

  const failed = coordinator.request();
  await yieldToRefresh();
  reads[0]?.reject(new Error("snapshot unavailable"));
  await assert.rejects(failed, /snapshot unavailable/);
  assert.equal(errors.length, 1);

  const retry = coordinator.request();
  await yieldToRefresh();
  reads[1]?.resolve("recovered");
  assert.equal(await retry, "recovered");
});

test("RefreshCoordinator forwards incremental paths and escalates a pending full refresh", async () => {
  const reads: Array<ReturnType<typeof deferred<string>>> = [];
  const changes: Array<{ paths: readonly string[]; forceFull: boolean }> = [];
  const coordinator = new RefreshCoordinator<string>({
    read: (next) => {
      changes.push(next);
      const result = deferred<string>();
      reads.push(result);
      return result.promise;
    },
    publish: () => undefined
  });

  const first = coordinator.request({ paths: ["wiki/a.md"], forceFull: false });
  await yieldToRefresh();
  const second = coordinator.request({ paths: [".devweave/project.json"], forceFull: true });
  reads[0]?.resolve("first");
  await yieldToRefresh();
  reads[1]?.resolve("second");

  assert.equal(await first, "second");
  assert.equal(await second, "second");
  assert.deepEqual(changes, [
    { paths: ["wiki/a.md"], forceFull: false },
    { paths: [".devweave/project.json"], forceFull: true }
  ]);
});
