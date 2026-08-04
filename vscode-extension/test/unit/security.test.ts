import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());
const runtimeFiles = [
  "src/clipboard.ts",
  "src/bootstrap.ts",
  "src/bootstrap-compat.ts",
  "src/dashboard.ts",
  "src/extension.ts",
  "src/filesystem.ts",
  "src/model.ts",
  "src/prompt.ts",
  "src/protocol.ts",
  "src/snapshot.ts",
  "src/tree.ts",
  "src/vscode-filesystem.ts",
  "src/vscode-bootstrap.ts",
  "src/refresh-coordinator.ts",
  "src/render-scheduler.ts",
  "src/wiki-search.ts",
  "webview/main.ts"
];

function runtimeSource(): string {
  return runtimeFiles.map((file) => readFileSync(resolve(extensionRoot, file), "utf8")).join("\n");
}

test("Extension runtime has no process, shell, or external-network path and confines writes to bootstrap", () => {
  const source = runtimeSource();
  assert.doesNotMatch(source, /from ["']node:child_process["']|from ["']child_process["']/);
  assert.doesNotMatch(source, /\b(?:exec|execFile|spawn|fork|createTerminal)\s*\(/);
  const extensionSource = readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8");
  assert.doesNotMatch(extensionSource, /workspace\.fs\.(?:writeFile|delete|rename)\s*\(/);
  const bootstrapAdapter = readFileSync(resolve(extensionRoot, "src/vscode-bootstrap.ts"), "utf8");
  assert.match(bootstrapAdapter, /workspace\.fs\.writeFile\s*\(/);
  assert.match(bootstrapAdapter, /useTrash: false/);
  assert.match(bootstrapAdapter, /code === "FileNotFound"/);
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

test("workflow mutations remain preview-first and bootstrap uses explicit confirmation", () => {
  const webview = readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8");
  const dashboard = readFileSync(resolve(extensionRoot, "src/dashboard.ts"), "utf8");
  const extension = readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8");
  const protocol = readFileSync(resolve(extensionRoot, "src/protocol.ts"), "utf8");
  assert.match(webview, /id="public-command-form"/);
  assert.match(webview, /Preview public command/);
  assert.match(webview, /data-action="confirm-copy"/);
  assert.match(webview, /type: "previewAction"/);
  assert.match(webview, /type: "copyAction"/);
  assert.match(webview, /new.*feature.*refactor.*bug.*next.*status.*revise.*approve/s);
  assert.doesNotMatch(webview, /ActionIntent JSON|compose-json|data-intent/);
  assert.doesNotMatch(webview, /type: "(?:doctor|commandSet|taskStart|knowledgePlan|close|validate)"/);
  assert.doesNotMatch(webview, /targetPaths|machineCommand|bundle\.gate/);
  assert.match(dashboard, /case "previewAction"/);
  assert.match(dashboard, /case "copyAction"/);
  assert.match(webview, /data-action="initialize"/);
  assert.match(webview, /type: "initialize"/);
  assert.match(protocol, /case "initialize"/);
  assert.match(dashboard, /case "initialize"/);
  assert.match(extension, /showWarningMessage\([\s\S]*modal: true/);
  assert.match(extension, /new BootstrapInstaller\(\)/);
});

test("Wiki bootstrap has three prompt-only entrances with one public intent", () => {
  const webview = readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8");
  const extension = readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8");
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as {
    activationEvents?: string[];
    contributes?: { commands?: Array<{ command?: string; title?: string }>; menus?: { commandPalette?: Array<{ command?: string }> } };
  };
  const commands = packageJson.contributes?.commands ?? [];
  const palette = packageJson.contributes?.menus?.commandPalette ?? [];

  assert.match(webview, /\["wikiBootstrap", "wiki bootstrap — 建立 Codebase Wiki"\]/);
  assert.match(webview, /data-action="wiki-bootstrap"/);
  assert.match(webview, /action === "wiki-bootstrap"[\s\S]*type: "wikiBootstrap"/);
  assert.ok(commands.some((item) => item.command === "devweave.wikiBootstrap" && item.title === "DevWeave: 建立 Codebase Wiki（複製 prompt）"));
  assert.ok(palette.some((item) => item.command === "devweave.wikiBootstrap"));
  assert.ok(packageJson.activationEvents?.includes("onCommand:devweave.wikiBootstrap"));
  assert.match(extension, /registerCommand\("devweave\.wikiBootstrap"/);
  assert.match(extension, /previewWikiBootstrap[\s\S]*type: "wikiBootstrap"/);
  assert.match(extension, /showWarningMessage\([\s\S]*modal: true/);
  assert.doesNotMatch(extension, /devweave\.py|knowledge bootstrap|workspace\.fs\.writeFile/);
});

test("P2 preferences and Wiki browsing stay Extension-local and discoverable", () => {
  const webview = readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8");
  const extension = readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8");
  const protocol = readFileSync(resolve(extensionRoot, "src/protocol.ts"), "utf8");
  assert.match(webview, /set-display-mode/);
  assert.match(webview, /show-all-wiki/);
  assert.match(webview, /wiki-query/);
  assert.match(webview, /wiki-type/);
  assert.match(webview, /輸入後按 Enter 套用搜尋/);
  assert.match(webview, /wikiSearch\.updateDraft/);
  assert.match(webview, /wikiSearch\.submit/);
  assert.match(webview, /id="wiki-results"/);
  assert.match(webview, /knowledgeRenderScheduler/);
  assert.doesNotMatch(webview, /renderKnowledgeOnly/);
  assert.match(webview, /case "help"/);
  assert.match(webview, /bootstrap\.complete/);
  assert.match(webview, /初始化／補齊 DevWeave/);
  assert.match(readFileSync(resolve(extensionRoot, "src/extension.ts"), "utf8"), /\.inspect\(bundle, resources, workspace\)/);
  assert.doesNotMatch(webview, /Snapshot may be newer than engine-observed state/);
  assert.match(extension, /workspaceState\.get/);
  assert.match(extension, /workspaceState\.update/);
  assert.match(extension, /已管理/);
  assert.match(extension, /未初始化/);
  assert.match(protocol, /case "setDisplayMode"/);
  assert.match(protocol, /isDisplayMode/);
});
