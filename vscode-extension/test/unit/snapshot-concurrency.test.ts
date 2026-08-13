import test from "node:test";
import assert from "node:assert/strict";
import type { DirectoryEntry, FileSystemPort } from "../../src/filesystem";
import { WorkspaceSnapshotReader } from "../../src/snapshot";

class InstrumentedFileSystem implements FileSystemPort {
  private readonly files = new Map<string, string>();
  public readonly readCounts = new Map<string, number>();
  public activeReads = 0;
  public maxConcurrentReads = 0;

  public constructor(entries: Record<string, string>) {
    for (const [path, value] of Object.entries(entries)) {
      this.files.set(path.replaceAll("\\", "/"), value);
    }
  }

  public async exists(relativePath: string): Promise<boolean> {
    const path = relativePath.replaceAll("\\", "/");
    return this.files.has(path) || [...this.files.keys()].some((file) => file.startsWith(`${path}/`));
  }

  public async inspectPath(relativePath: string): Promise<{ kind: "missing" | "file" | "directory" | "symlink" | "other" }> {
    const path = relativePath.replaceAll("\\", "/");
    if (this.files.has(path)) return { kind: "file" };
    if ([...this.files.keys()].some((file) => file.startsWith(`${path}/`))) return { kind: "directory" };
    return { kind: "missing" };
  }

  public async readText(relativePath: string, maxBytes = 1_000_000): Promise<{ text: string; truncated: boolean }> {
    const path = relativePath.replaceAll("\\", "/");
    const text = this.files.get(path);
    if (text === undefined) throw new Error(`Missing file: ${path}`);
    this.readCounts.set(path, (this.readCounts.get(path) ?? 0) + 1);
    this.activeReads += 1;
    this.maxConcurrentReads = Math.max(this.maxConcurrentReads, this.activeReads);
    await new Promise<void>((resolve) => setTimeout(resolve, path.endsWith("b.md") ? 1 : 5));
    this.activeReads -= 1;
    return { text: text.slice(0, maxBytes), truncated: text.length > maxBytes };
  }

  public setText(relativePath: string, value: string): void {
    this.files.set(relativePath.replaceAll("\\", "/"), value);
  }

  public async readDirectory(relativePath: string): Promise<DirectoryEntry[]> {
    const path = relativePath.replaceAll("\\", "/").replace(/\/$/, "");
    const prefix = `${path}/`;
    const entries = new Map<string, DirectoryEntry>();
    for (const file of this.files.keys()) {
      if (!file.startsWith(prefix)) continue;
      const remainder = file.slice(prefix.length);
      const [name, ...rest] = remainder.split("/");
      entries.set(name, { name, kind: rest.length ? "directory" : "file" });
    }
    return [...entries.values()].reverse();
  }
}

const validProject = JSON.stringify({ managed: true, schema_version: 1, commands: [], verification_profiles: {} });
const invalidWiki = "not frontmatter";

test("snapshot reader parallelizes independent text reads while keeping diagnostics sorted", async () => {
  const files = new InstrumentedFileSystem({
    ".devweave/project.json": validProject,
    ".codex/hooks.json": "{}",
    ".agents/skills/devweave/SKILL.md": "# DevWeave",
    "wiki/a.md": invalidWiki,
    "wiki/b.md": invalidWiki
  });
  const snapshot = await new WorkspaceSnapshotReader(files, {
    rootName: "fixture",
    rootPath: "file:///fixture",
    now: () => "2026-08-04T00:00:00Z"
  }).readWorkspace();

  assert.ok(files.maxConcurrentReads > 1);
  assert.deepEqual(snapshot.knowledge.critical.filter((item) => item.code === "wiki_parse").map((item) => item.path), ["wiki/a.md", "wiki/b.md"]);
  assert.deepEqual(snapshot.knowledge.pages.map((page) => page.path), ["wiki/a.md", "wiki/b.md"]);
});

test("snapshot reader reuses unchanged Wiki pages for an incremental refresh", async () => {
  const files = new InstrumentedFileSystem({
    ".devweave/project.json": validProject,
    ".codex/hooks.json": "{}",
    ".agents/skills/devweave/SKILL.md": "# DevWeave",
    "wiki/a.md": invalidWiki,
    "wiki/b.md": invalidWiki
  });
  const reader = new WorkspaceSnapshotReader(files, {
    rootName: "fixture",
    rootPath: "file:///fixture",
    now: () => "2026-08-04T00:00:00Z"
  });

  await reader.readWorkspace();
  files.setText("wiki/a.md", invalidWiki + "\nchanged");
  await reader.readWorkspace({ paths: ["wiki/a.md"], forceFull: false });

  assert.equal(files.readCounts.get("wiki/a.md"), 2);
  assert.equal(files.readCounts.get("wiki/b.md"), 1);
});

test("snapshot reader exposes bounded Wiki provenance and keeps engine observation unavailable", async () => {
  const files = new InstrumentedFileSystem({
    ".devweave/project.json": validProject,
    ".codex/hooks.json": "{}",
    ".agents/skills/devweave/SKILL.md": "# DevWeave",
    "wiki/a.md": "---\ntitle: A\ntype: module\nstatus: active\nsources: [src/a.ts]\nsource_fingerprint: old\n---\n# A\ncontent"
  });
  const snapshot = await new WorkspaceSnapshotReader(files, {
    rootName: "fixture",
    rootPath: "file:///fixture"
  }).readWorkspace();

  const page = snapshot.knowledge.pages[0];
  assert.equal(snapshot.engineObservedAt, null);
  assert.equal(page?.path, "wiki/a.md");
  assert.equal(page?.truncated, false);
  assert.match(page?.contentHash ?? "", /^[a-f0-9]{64}$/);
  assert.equal(page?.sourceFingerprint, "old");
});
