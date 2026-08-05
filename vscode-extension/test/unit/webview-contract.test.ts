import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import { dashboardPanelState, dashboardSectionDefinitions, moveDashboardSection } from "../../src/dashboard-sections";
import { mountWikiResults } from "../../src/wiki-results-mount";

const extensionRoot = resolve(process.cwd());

test("Wiki result mount writes rendered markup into the dedicated result host", () => {
  const host = { innerHTML: "" };
  const fakeDocument = {
    querySelector(selector: string) {
      return selector === "#wiki-results" ? host : null;
    }
  };

  assert.equal(mountWikiResults(fakeDocument, "<p>結果</p>"), true);
  assert.equal(host.innerHTML, "<p>結果</p>");
});

test("Webview contract keeps preview metadata, stale reset, and accessible five-tab navigation", () => {
  const source = readFileSync(resolve(extensionRoot, "webview/main.ts"), "utf8");
  const styles = readFileSync(resolve(extensionRoot, "webview/styles.css"), "utf8");
  assert.match(source, /mountWikiResults\(document, renderKnowledgeResults\(\)\)/);
  assert.match(source, /message\.revision !== snapshotRevision/);
  assert.match(source, /pendingIntent = message\.intent/);
  assert.match(source, /role="tablist"[\s\S]*aria-orientation="horizontal"/);
  assert.match(source, /role="tabpanel"/);
  assert.match(source, /sectionDefinitions\.map\(\(\[section\]\) => renderSectionPanel\(section\)\)/);
  assert.match(source, /hidden aria-hidden=\\"true\\"/);
  assert.match(source, /aria-labelledby="\$\{panel\.labelledBy\}"/);
  assert.match(source, /aria-controls="tabpanel-/);
  assert.match(source, /ArrowRight|ArrowDown/);
  assert.match(source, /ArrowLeft|ArrowUp/);
  assert.match(source, /moveDashboardSection\(currentSection, event\.key\)/);
  assert.match(source, /tabindex="\$\{selectedSection === id \? 0 : -1\}"/);
  assert.match(source, /目前有多個 active work/);
  assert.match(source, /取消勾選即可查詢全部 active work/);
  assert.match(source, /case "next"[\s\S]*activeWorks\.length === 0/);
  assert.match(source, /case "status"[\s\S]*\{ type: command, all: true \}/);
  assert.match(source, /errorDetail = message\.detail/);
  assert.match(source, /查看 technical 詳情/);
  assert.match(source, /預覽公開操作/);
  assert.doesNotMatch(source, /Preview public command/);
  assert.match(styles, /@media \(forced-colors: active\)/);

  const definitions = dashboardSectionDefinitions;
  assert.equal(definitions.length, 5);
  const panelStates = definitions.map(([section]) => dashboardPanelState(section, "overview"));
  assert.deepEqual(panelStates.map((panel) => panel.id), definitions.map(([section]) => `tabpanel-${section}`));
  assert.deepEqual(panelStates.map((panel) => panel.labelledBy), definitions.map(([section]) => `section-tab-${section}`));
  assert.equal(panelStates.filter((panel) => panel.hidden).length, 4);
  assert.equal(panelStates.find((panel) => panel.id === "tabpanel-overview")?.tabIndex, 0);
  assert.equal(moveDashboardSection("overview", "ArrowRight"), "work");
  assert.equal(moveDashboardSection("overview", "ArrowLeft"), "help");
  assert.equal(moveDashboardSection("work", "ArrowDown"), "knowledge");
  assert.equal(moveDashboardSection("knowledge", "ArrowUp"), "work");
  assert.equal(moveDashboardSection("knowledge", "Home"), "overview");
  assert.equal(moveDashboardSection("knowledge", "End"), "help");
  assert.equal(moveDashboardSection("overview", "PageDown"), null);
  console.log("[accessibility] tabs=5 panels=5 hidden-inactive=4 keyboard=arrows/Home/End focus-restore=section-key forced-colors=checked");
});
