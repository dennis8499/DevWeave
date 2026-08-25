import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { UiEvidenceCollector } from "../src/evidence/ui-evidence";
import { TABS } from "../webview/render";

interface Options {
  output: string;
  runId: string;
  commit: string;
  codexVersion: string;
  schemaHash: string;
  screenshots: string[];
  contractOnly: boolean;
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));
  const collector = new UiEvidenceCollector({
    runId: options.runId,
    commit: options.commit,
    codexVersion: options.codexVersion,
    schemaHash: options.schemaHash
  });
  await collectContractEvidence(collector, process.cwd());
  if (!options.contractOnly && options.screenshots.length === 0) {
    throw new Error("At least one --screenshot is required unless --contract-only is explicit.");
  }
  for (const screenshot of options.screenshots) await collector.registerScreenshot(resolve(screenshot));
  collector.addAssertion(
    "screenshot-evidence",
    options.contractOnly || options.screenshots.length > 0,
    options.contractOnly ? "Explicit contract-only evidence run." : `${options.screenshots.length} screenshot(s) hashed.`
  );
  const report = await collector.write(resolve(options.output));
  if (!report.allPassed) throw new Error("One or more UI evidence assertions failed.");
  process.stdout.write(`${JSON.stringify({ output: resolve(options.output), assertions: report.assertions.length, screenshots: report.screenshots.length })}\n`);
}

async function collectContractEvidence(collector: UiEvidenceCollector, root: string): Promise<void> {
  const [manifestRaw, extension, render, webview, styles] = await Promise.all([
    readFile(resolve(root, "package.json"), "utf8"),
    readFile(resolve(root, "src/extension.ts"), "utf8"),
    readFile(resolve(root, "webview/render.ts"), "utf8"),
    readFile(resolve(root, "webview/main.ts"), "utf8"),
    readFile(resolve(root, "webview/styles.css"), "utf8")
  ]);
  const manifest = JSON.parse(manifestRaw) as { version?: string; contributes?: { commands?: Array<{ command?: string }> } };
  const commands = (manifest.contributes?.commands ?? []).map((item) => item.command).filter((item): item is string => Boolean(item));
  const expectedCommands = [
    "devweave.openControlCenter", "devweave.startRun", "devweave.resumeRun",
    "devweave.steer", "devweave.interrupt", "devweave.cancel"
  ];
  collector.addAssertion("manifest-v2", manifest.version === "2.0.0", `version=${manifest.version ?? "missing"}`);
  collector.addAssertion("command-surface", JSON.stringify(commands.sort()) === JSON.stringify(expectedCommands.sort()), commands.join(","));
  collector.addAssertion("strict-csp", extension.includes("default-src 'none'") && !/unsafe-inline|unsafe-eval/.test(extension), "External assets plus a nonce-bound script only.");
  collector.addAssertion("five-accessible-tabs", TABS.length === 5 && render.includes('role="tablist"') && render.includes('role="tabpanel"'), `tabs=${TABS.length}`);
  collector.addAssertion("reasoning-omitted", render.includes('item.type !== "reasoning"'), "Reasoning items are filtered before HTML rendering.");
  collector.addAssertion("webview-no-network-or-clipboard", !/\b(?:fetch|XMLHttpRequest|WebSocket)\b|clipboard/i.test(webview), "Webview only posts validated intents to the extension host.");
  collector.addAssertion("forced-colors", styles.includes("@media (forced-colors: active)"), "Forced-colors overrides are present.");
  collector.addAssertion("reduced-motion", styles.includes("@media (prefers-reduced-motion: reduce)"), "Reduced-motion overrides are present.");
  collector.addLog("contract", "Static Control Center contract inspection completed; authorization: token-secret-value");
}

function parseArgs(args: string[]): Options {
  const values = new Map<string, string>();
  const screenshots: string[] = [];
  let contractOnly = false;
  for (let index = 0; index < args.length; index += 1) {
    const key = args[index];
    if (key === "--contract-only") {
      contractOnly = true;
      continue;
    }
    if (!["--output", "--run-id", "--commit", "--codex-version", "--schema-hash", "--screenshot"].includes(key)) {
      throw new Error(`Unknown UI evidence argument: ${key}`);
    }
    const value = args[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for ${key}.`);
    index += 1;
    if (key === "--screenshot") screenshots.push(value);
    else {
      if (values.has(key)) throw new Error(`Duplicate UI evidence argument: ${key}`);
      values.set(key, value);
    }
  }
  const required = (key: string): string => {
    const value = values.get(key);
    if (!value) throw new Error(`Missing required UI evidence argument: ${key}`);
    return value;
  };
  return {
    output: required("--output"),
    runId: required("--run-id"),
    commit: required("--commit"),
    codexVersion: required("--codex-version"),
    schemaHash: required("--schema-hash"),
    screenshots,
    contractOnly
  };
}

void main().catch((error: unknown) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
