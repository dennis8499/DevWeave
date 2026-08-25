import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

import { initialProjection } from "../../src/app-server/event-reducer";
import type { UiProjection } from "../../src/ui/projection";
import { parseUiIntent } from "../../src/ui/protocol";
import { nextTabIndex, renderControlCenter, TABS } from "../../webview/render";

const extensionRoot = resolve(process.cwd());

function fixture(): UiProjection {
  const appServer = initialProjection();
  appServer.connection = "connected";
  appServer.threadStatus = "active";
  appServer.turnStatus = "completed";
  appServer.plan = [{ step: "Implement vertical slice" }];
  appServer.diff = "+<unsafe>";
  appServer.usage = { inputTokens: 3, outputTokens: 4, totalTokens: 7 };
  appServer.items = {
    visible: { id: "visible", type: "agentMessage", status: "completed", authoritative: true, content: "done <ok>" },
    private: { id: "private", type: "reasoning", status: "completed", authoritative: true, hasPrivateContent: true }
  };
  return {
    source: "authoritative+projection",
    stale: false,
    status: "ready",
    run: {
      run_id: "run-1",
      status: "awaiting_gate",
      plan: { goal: "Ship <script>" },
      verification: { status: "passed" },
      review: { status: "passed" },
      gates: { G2: { status: "pending" } },
      pending_decision: {
        decision_id: "D-1", question: "Choose?", allow_other: true,
        options: [{ option_id: "safe", label: "Safe" }]
      }
    },
    preflight: {
      status: "ready",
      codex: { version: "codex-cli 1.2.3" },
      app_server: { schema_sha256: "a".repeat(64) }
    },
    threadId: "thread-1",
    turnId: "turn-1",
    appServer,
    pendingApprovals: [{
      request: { id: "approval-1", method: "item/fileChange/requestApproval", params: {} },
      assessment: { eligible: true, reason: "Declared task scope", paths: ["src/app.ts"], readOnly: false }
    }],
    review: {
      status: "passed", round: 1, reviewerThreadId: "review-thread",
      findings: [{
        schema_version: 2, finding_id: "F-1", severity: "warning", summary: "Bounded",
        paths: ["src/app.ts"], requirement_ids: ["REQ-1"], acceptance_ids: ["AC-1"],
        task_ids: ["TASK-1"], status: "open", round: 1
      }],
      unresolvedCritical: false
    },
    diagnostics: ["healthy"]
  };
}

test("Control Center renders the complete V2 state with authority and safe escaping", () => {
  const html = renderControlCenter(fixture());
  for (const label of ["Connection", "Preflight", "Codex", "Run", "Thread", "Turn", "Usage", "Plan &amp; diff", "Gates", "Tools, approvals &amp; decisions", "Verification &amp; review", "Diagnostics"]) {
    assert.match(html, new RegExp(label));
  }
  assert.match(html, /Authoritative \/ current/);
  assert.match(html, /codex-cli 1\.2\.3/);
  assert.match(html, /7 total \(3 in \/ 4 out\)/);
  assert.match(html, /Ship &lt;script&gt;/);
  assert.match(html, /\+&lt;unsafe&gt;/);
  assert.match(html, /done &lt;ok&gt;/);
  assert.match(html, /data-action="decision-other"/);
  assert.doesNotMatch(html, /type="reasoning"|>reasoning<|private start|private final/);
});

test("five semantic tabs use roving tabindex, hidden inactive panels, and complete keyboard movement", () => {
  const html = renderControlCenter(fixture(), "plan");
  assert.equal(TABS.length, 5);
  assert.equal(html.match(/role="tab"/g)?.length, 5);
  assert.equal(html.match(/role="tabpanel"/g)?.length, 5);
  assert.equal(html.match(/role="tabpanel"[^>]*hidden/g)?.length, 4);
  assert.match(html, /id="tab-plan"[^>]*aria-selected="true"[^>]*tabindex="0"/);
  assert.equal(nextTabIndex(0, "ArrowRight"), 1);
  assert.equal(nextTabIndex(0, "ArrowLeft"), 4);
  assert.equal(nextTabIndex(2, "ArrowDown"), 3);
  assert.equal(nextTabIndex(2, "ArrowUp"), 1);
  assert.equal(nextTabIndex(2, "Home"), 0);
  assert.equal(nextTabIndex(2, "End"), 4);
  assert.equal(nextTabIndex(2, "PageDown"), 2);
});

test("Webview intents are exact, bounded, and contain no legacy prompt-copy or Wiki surface", () => {
  assert.deepEqual(parseUiIntent({ type: "start", goal: "Implement V2", scope: "src/**", risk: "high" }), {
    type: "start", goal: "Implement V2", scope: "src/**", risk: "high"
  });
  assert.deepEqual(parseUiIntent({ type: "approval", requestId: "one", decision: "decline" }), {
    type: "approval", requestId: "one", decision: "decline"
  });
  assert.equal(parseUiIntent({ type: "cancel", extra: true }), null);
  assert.equal(parseUiIntent({ type: "decision", decisionId: "D", optionId: "one", other: "two" }), null);
  assert.equal(parseUiIntent({ type: "copyNextAction" }), null);
  assert.equal(parseUiIntent({ type: "wikiBootstrap" }), null);
});

test("Webview source preserves focus and supports forced colors and reduced motion", () => {
  const main = readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8");
  const styles = readFileSync(resolve(extensionRoot, "webview/styles.css"), "utf8");
  assert.match(main, /dataset\.focusKey/);
  assert.match(main, /CSS\.escape\(focusKey\)/);
  assert.match(main, /nextTabIndex\(current, event\.key, tabs\.length\)/);
  assert.match(styles, /@media \(forced-colors: active\)/);
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/);
});
