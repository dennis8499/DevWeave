import test from "node:test";
import assert from "node:assert/strict";
import type { DirectoryEntry, FileSystemPort } from "../../src/filesystem";
import { WorkspaceSnapshotReader } from "../../src/snapshot";

class ProjectionFileSystem implements FileSystemPort {
  public constructor(private readonly files: Record<string, string>) {}

  public async exists(relativePath: string): Promise<boolean> {
    return Object.prototype.hasOwnProperty.call(this.files, relativePath)
      || Object.keys(this.files).some((path) => path.startsWith(`${relativePath}/`));
  }

  public async readText(relativePath: string): Promise<{ text: string; truncated: boolean }> {
    const text = this.files[relativePath];
    if (text === undefined) throw new Error(`Missing ${relativePath}`);
    return { text, truncated: false };
  }

  public async readDirectory(relativePath: string): Promise<DirectoryEntry[]> {
    const prefix = `${relativePath}/`;
    const entries = new Map<string, DirectoryEntry>();
    for (const path of Object.keys(this.files)) {
      if (!path.startsWith(prefix)) continue;
      const remainder = path.slice(prefix.length);
      const [name, ...rest] = remainder.split("/");
      entries.set(name, { name, kind: rest.length ? "directory" : "file" });
    }
    return [...entries.values()];
  }
}

test("snapshot exposes missing bootstrap control paths instead of project-only readiness", async () => {
  const snapshot = await new WorkspaceSnapshotReader(new ProjectionFileSystem({
    ".devweave/project.json": JSON.stringify({ managed: true, schema_version: 1, commands: [], verification_profiles: {} })
  }), {
    rootName: "projection",
    rootPath: "file:///projection",
    bootstrapPaths: [
      ".devweave/project.json",
      ".codex/hooks.json",
      "AGENTS.md",
      ".agents/skills/tdd/SKILL.md"
    ]
  }).readWorkspace();

  assert.equal(snapshot.projectExists, true);
  assert.equal(snapshot.bootstrap.complete, false);
  assert.deepEqual(snapshot.bootstrap.expected, [".agents/skills/tdd/SKILL.md", ".codex/hooks.json", ".devweave/project.json", "AGENTS.md"].sort());
  assert.deepEqual(snapshot.bootstrap.missing, [".agents/skills/tdd/SKILL.md", ".codex/hooks.json", "AGENTS.md"].sort());
});
