import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());
const source = (path: string): string => readFileSync(resolve(extensionRoot, path), "utf8");

test("process execution is isolated to bounded JSONL transports with shell disabled", () => {
  const transport = source("src/app-server/transport.ts");
  const bridge = source("src/controller/host-bridge-client.ts");
  const otherRuntime = [
    "src/extension.ts", "src/app-server/session.ts", "src/app-server/event-reducer.ts",
    "src/controller/workspace-controller.ts", "src/controller/approval-broker.ts",
    "src/controller/review-coordinator.ts", "webview/main.ts", "webview/render.ts"
  ].map(source).join("\n");
  assert.match(transport, /from "node:child_process"/);
  assert.match(transport, /spawn\(options\.executable, options\.args/);
  assert.match(transport, /shell: false/);
  assert.match(transport, /windowsHide: true/);
  assert.doesNotMatch(otherRuntime, /from ["']node:child_process["']/);
  assert.match(bridge, /args: \["-B", hostScript\]/);
  assert.doesNotMatch(bridge, /env:\s*\{[^}]*token/is);
});

test("Webview has a strict CSP and no direct network, filesystem, shell, or clipboard channel", () => {
  const extension = source("src/extension.ts");
  const webview = source("webview/main.ts");
  const manifest = JSON.parse(source("package.json")) as { devDependencies?: Record<string, unknown> };
  assert.match(extension, /default-src 'none'/);
  assert.match(extension, /script-src 'nonce-\$\{nonce\}'/);
  assert.doesNotMatch(extension, /unsafe-inline|unsafe-eval/);
  assert.match(extension, /localResourceRoots/);
  assert.doesNotMatch(webview, /\b(?:fetch|XMLHttpRequest|WebSocket)\b|clipboard|child_process|workspace\.fs/i);
  assert.equal(Boolean(manifest.devDependencies?.react || manifest.devDependencies?.["react-dom"]), false);
});

test("reasoning and unvalidated Webview messages cannot cross the presentation boundary", () => {
  const reducer = source("src/app-server/event-reducer.ts");
  const renderer = source("webview/render.ts");
  const extension = source("src/extension.ts");
  assert.match(reducer, /type === "reasoning"/);
  assert.match(renderer, /item\.type !== "reasoning"/);
  assert.match(extension, /const intent = parseUiIntent\(value\)/);
  assert.match(extension, /rejected an invalid Control Center message/);
  assert.doesNotMatch(renderer, /hasPrivateContent[^\n]*content/);
});

test("all privileged workflow mutations route through the authenticated private host bridge", () => {
  const extension = source("src/extension.ts");
  const controller = source("src/controller/workspace-controller.ts");
  const bridge = source("src/controller/host-bridge-client.ts");
  assert.doesNotMatch(extension, /workspace\.fs\.(?:writeFile|delete|rename)\s*\(/);
  assert.match(controller, /this\.host\.request\("run_start"/);
  assert.match(controller, /this\.host\.request\("decision_resolve"/);
  assert.match(controller, /this\.host\.request\("gate_decide"/);
  assert.match(bridge, /createHmac\("sha256", this\.token\)/);
  assert.match(bridge, /this\.send\(\{ type: "hello", token: this\.token/);
});
