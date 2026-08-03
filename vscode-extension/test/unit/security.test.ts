import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());
const runtimeFiles = [
  "src/clipboard.ts",
  "src/dashboard.ts",
  "src/extension.ts",
  "src/filesystem.ts",
  "src/model.ts",
  "src/prompt.ts",
  "src/protocol.ts",
  "src/snapshot.ts",
  "src/tree.ts",
  "src/vscode-filesystem.ts",
  "webview/main.ts"
];

function runtimeSource(): string {
  return runtimeFiles.map((file) => readFileSync(resolve(extensionRoot, file), "utf8")).join("\n");
}

test("Extension runtime has no process, shell, repository-write, or external-network path", () => {
  const source = runtimeSource();
  assert.doesNotMatch(source, /from ["']node:child_process["']|from ["']child_process["']/);
  assert.doesNotMatch(source, /\b(?:exec|execFile|spawn|fork|createTerminal)\s*\(/);
  assert.doesNotMatch(source, /workspace\.fs\.(?:writeFile|delete|rename)\s*\(/);
  assert.doesNotMatch(source, /\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(/);
  assert.doesNotMatch(source, /commands\.executeCommand\s*\(/);
  assert.match(source, /env\.clipboard\.writeText\s*\(/);
});

test("package and Webview keep the approved dependency and CSP boundary", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as Record<string, unknown>;
  const dependencies = Object.keys((packageJson.devDependencies ?? {}) as Record<string, unknown>);
  assert.equal(dependencies.some((name) => name === "react" || name === "react-dom"), false);
  assert.match(readFileSync(resolve(extensionRoot, "src/dashboard.ts"), "utf8"), /default-src 'none'/);
  assert.match(readFileSync(resolve(extensionRoot, "src/dashboard.ts"), "utf8"), /localResourceRoots/);
  assert.match(readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8"), /raw log/);
  assert.doesNotMatch(readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8"), /readText\s*\(\s*item\.rawLog/);
});

test("all mutation UI routes are preview-first", () => {
  const webview = readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8");
  const dashboard = readFileSync(resolve(extensionRoot, "src/dashboard.ts"), "utf8");
  assert.match(webview, /data-action="preview"/);
  assert.match(webview, /data-action="confirm-copy"/);
  assert.match(webview, /type: "previewAction"/);
  assert.match(webview, /type: "copyAction"/);
  assert.match(dashboard, /case "previewAction"/);
  assert.match(dashboard, /case "copyAction"/);
});
