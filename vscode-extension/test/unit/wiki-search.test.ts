import test from "node:test";
import assert from "node:assert/strict";
import { RenderScheduler } from "../../src/render-scheduler";
import { WikiSearchModel } from "../../src/wiki-search";

const pages = [
  { path: "wiki/architecture/engine.md", title: "Knowledge Engine", type: "architecture", bodyPreview: "VSCode snapshot projection" },
  { path: "wiki/modules/runtime.md", title: "Runtime", type: "module", bodyPreview: "Watcher refresh coordinator" },
  { path: "wiki/guides/search.md", title: "Search Guide", type: "guide", bodyPreview: "Contains matching only" }
];

test("WikiSearchModel keeps draft input separate until Enter commits it", () => {
  const model = new WikiSearchModel(pages);

  assert.equal(model.updateDraft("engine").appliedQuery, "");
  assert.deepEqual(model.filter(), pages);

  assert.equal(model.submit().appliedQuery, "engine");
  assert.deepEqual(model.filter().map((page) => page.path), ["wiki/architecture/engine.md"]);
});

test("WikiSearchModel matches title, path, and body case-insensitively with contains semantics", () => {
  const model = new WikiSearchModel(pages);

  model.updateDraft("VSCODE");
  model.submit();
  assert.deepEqual(model.filter().map((page) => page.path), ["wiki/architecture/engine.md"]);

  model.updateDraft("GUIDES");
  model.submit();
  assert.deepEqual(model.filter().map((page) => page.path), ["wiki/guides/search.md"]);
});

test("WikiSearchModel applies exact type filtering and show-all state", () => {
  const model = new WikiSearchModel(pages, { pageLimit: 1 });

  model.setType("module");
  assert.deepEqual(model.visiblePages().map((page) => page.path), ["wiki/modules/runtime.md"]);

  model.setType("all");
  assert.deepEqual(model.visiblePages().map((page) => page.path), ["wiki/architecture/engine.md"]);
  model.setShowAll(true);
  assert.deepEqual(model.visiblePages().map((page) => page.path), pages.map((page) => page.path));
});

test("RenderScheduler coalesces local renders into one frame", () => {
  const frames: Array<() => void> = [];
  let renders = 0;
  const scheduler = new RenderScheduler(() => { renders += 1; }, (callback) => frames.push(callback));

  scheduler.request();
  scheduler.request();
  assert.equal(frames.length, 1);
  assert.equal(renders, 0);

  frames.shift()?.();
  assert.equal(renders, 1);
  scheduler.request();
  assert.equal(frames.length, 1);
});
