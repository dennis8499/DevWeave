import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import test from "node:test";

type SpawnResult = {
  error?: Error;
  signal: string | null;
  status: number | null;
};

type SpawnCall = {
  args: string[];
  command: string;
  options: Record<string, unknown>;
};

type RunnerModule = {
  discoverUnitTests: (testRoot: string) => Promise<string[]>;
  runUnitTests: (options: {
    extensionRoot: string;
    nodeExecutable: string;
    spawn: (command: string, args: string[], options: Record<string, unknown>) => SpawnResult;
    testRoot: string;
    tsxCli: string;
    writeError: (message: string) => void;
  }) => Promise<number>;
};

async function loadRunner(): Promise<RunnerModule> {
  // @ts-ignore The JavaScript CLI module is exercised through its approved runtime seam.
  return import("../../scripts/run-unit-tests.mjs") as Promise<RunnerModule>;
}

test("unit-test runner discovers a deterministic suite and fails closed for every abnormal child outcome", async () => {
  const root = await mkdtemp(join(tmpdir(), "devweave-unit-runner-"));
  const testRoot = join(root, "test", "unit");
  const nested = join(testRoot, "nested");
  const emptyRoot = join(root, "empty");
  try {
    await mkdir(nested, { recursive: true });
    await mkdir(emptyRoot, { recursive: true });
    await writeFile(join(testRoot, "zeta.test.ts"), "// root test\n", "utf8");
    await writeFile(join(nested, "alpha.test.ts"), "// nested test\n", "utf8");
    await writeFile(join(nested, "ignored.ts"), "// not a test\n", "utf8");
    await writeFile(join(nested, "ignored.test.js"), "// wrong extension\n", "utf8");

    const { discoverUnitTests, runUnitTests } = await loadRunner();
    const discovered = await discoverUnitTests(testRoot);
    assert.deepEqual(
      discovered.map((path) => relative(testRoot, path).replaceAll("\\", "/")),
      ["nested/alpha.test.ts", "zeta.test.ts"]
    );

    const nodeExecutable = join(root, "node");
    const tsxCli = join(root, "tsx-cli.mjs");
    const calls: SpawnCall[] = [];
    const errors: string[] = [];
    const run = (result: SpawnResult, selectedRoot = testRoot) => runUnitTests({
      extensionRoot: root,
      nodeExecutable,
      spawn: (command, args, options) => {
        calls.push({ command, args, options });
        return result;
      },
      testRoot: selectedRoot,
      tsxCli,
      writeError: (message) => errors.push(message)
    });

    assert.equal(await run({ status: 0, signal: null }), 0);
    assert.deepEqual(calls[0], {
      command: nodeExecutable,
      args: [tsxCli, "--test", ...discovered],
      options: { cwd: root, shell: false, stdio: "inherit" }
    });

    assert.equal(await run({ status: 7, signal: null }), 7);
    assert.equal(await run({ status: null, signal: null, error: new Error("spawn blocked") }), 1);
    assert.equal(await run({ status: null, signal: "SIGTERM" }), 1);
    assert.equal(await run({ status: 0, signal: null }, emptyRoot), 1);
    assert.ok(errors.some((message) => message.includes("spawn blocked")));
    assert.ok(errors.some((message) => message.includes("SIGTERM")));
    assert.ok(errors.some((message) => message.includes("No unit test files found")));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
