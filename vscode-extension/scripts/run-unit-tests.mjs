import { spawnSync } from "node:child_process";
import { readdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const extensionRoot = fileURLToPath(new URL("../", import.meta.url));
const require = createRequire(import.meta.url);

export async function discoverUnitTests(testRoot) {
  const root = resolve(testRoot);
  const discovered = [];

  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const absolute = join(directory, entry.name);
      if (entry.isDirectory()) {
        await visit(absolute);
      } else if (entry.isFile() && entry.name.endsWith(".test.ts")) {
        discovered.push({
          absolute,
          relative: relative(root, absolute).replaceAll("\\", "/")
        });
      }
    }
  }

  await visit(root);
  discovered.sort((left, right) => left.relative < right.relative ? -1 : left.relative > right.relative ? 1 : 0);
  return discovered.map((entry) => entry.absolute);
}

export async function runUnitTests({
  extensionRoot: configuredExtensionRoot = extensionRoot,
  testRoot = join(configuredExtensionRoot, "test", "unit"),
  nodeExecutable = process.execPath,
  tsxCli,
  spawn = spawnSync,
  writeError = (message) => console.error(message)
} = {}) {
  try {
    const tests = await discoverUnitTests(testRoot);
    if (tests.length === 0) {
      throw new Error(`No unit test files found under ${testRoot}.`);
    }

    const resolvedTsxCli = tsxCli ?? require.resolve("tsx/cli");
    const result = spawn(
      nodeExecutable,
      [resolvedTsxCli, "--test", ...tests],
      { cwd: configuredExtensionRoot, shell: false, stdio: "inherit" }
    );

    if (result.error) throw result.error;
    if (typeof result.status === "number") return result.status;
    if (result.signal) {
      throw new Error(`Unit test process terminated by signal ${result.signal}.`);
    }
    throw new Error("Unit test process exited without a numeric status.");
  } catch (error) {
    writeError(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

const invokedScript = process.argv[1] ? resolve(process.argv[1]) : "";
if (invokedScript === resolve(fileURLToPath(import.meta.url))) {
  process.exitCode = await runUnitTests();
}
