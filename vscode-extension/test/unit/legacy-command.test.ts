import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("V2 exposes only governed run commands and removes prompt-copy and Wiki entry points", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as {
    activationEvents?: string[];
    contributes?: { commands?: Array<{ command?: string }> };
  };
  const extension = readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8");
  const commands = (packageJson.contributes?.commands ?? []).map((item) => item.command).sort();
  assert.deepEqual(commands, [
    "devweave.cancel",
    "devweave.interrupt",
    "devweave.openControlCenter",
    "devweave.resumeRun",
    "devweave.startRun",
    "devweave.steer"
  ]);
  assert.doesNotMatch(JSON.stringify(packageJson), /copyNextAction|wikiBootstrap|clipboard/i);
  assert.doesNotMatch(extension, /\.\/clipboard|\.\/prompt|\.\/dashboard|\.\/wiki-/);
  assert.match(extension, /new CodexAppServerSession\(\)/);
  assert.match(extension, /new WorkspaceController\(/);
});
