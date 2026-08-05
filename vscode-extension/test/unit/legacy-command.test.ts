import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("legacy copyNextAction command opens the Control Center preview flow", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as {
    contributes?: { commands?: Array<{ command?: string; title?: string }> };
  };
  const extension = readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8");
  const method = extension.match(/public async copyNextAction\(\): Promise<void> \{([\s\S]*?)\n  \}/)?.[1] ?? "";

  assert.ok(packageJson.contributes?.commands?.some((command) => command.command === "devweave.copyNextAction"));
  assert.match(method, /dashboard\?\.show\(/);
  assert.match(method, /dashboard\?\.previewAction\(/);
  assert.doesNotMatch(method, /await this\.copy\(\{ type: "next"/);
});
