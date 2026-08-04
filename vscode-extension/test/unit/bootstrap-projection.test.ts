import test from "node:test";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import type { DirectoryEntry, FileSystemPort } from "../../src/filesystem";
import type { BootstrapCompatibilityKind } from "../../src/bootstrap-compat";
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

  public async readBytes(relativePath: string): Promise<Uint8Array> {
    return new TextEncoder().encode((await this.readText(relativePath)).text);
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

function contract(destination: string, kind: BootstrapCompatibilityKind, text: string, transform: "copy" | "date" = "copy") {
  const bytes = new TextEncoder().encode(text);
  return {
    destination,
    transform,
    byteLength: bytes.byteLength,
    sha256: createHash("sha256").update(bytes).digest("hex"),
    existingPolicy: "adopt-compatible" as const,
    compatibility: kind
  };
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

test("snapshot uses the same semantic contracts as installer for evolved bootstrap files", async () => {
  const entries: Record<string, string> = {
    ".devweave/project.json": JSON.stringify({
      schema_version: 1,
      managed: true,
      locale: "zh-TW",
      commands: [],
      verification_profiles: { low: [], standard: [], high: [] },
      evidence: { raw_log_limit_bytes: 5_000_000 },
      knowledge: { enabled: true, root: "wiki" }
    }, null, 2),
    ".devweave/baseline/product.md": "# Product Baseline\n\n## Vision\nEvolved.\n\n## Accepted Capabilities\nEvolved.\n\n## Roadmap\nEvolved.\n",
    ".devweave/baseline/architecture.md": "# Architecture Baseline\n\n## System Context\nEvolved.\n\n## Boundaries and Interfaces\nEvolved.\n\n## Accepted Decisions\nEvolved.\n",
    ".devweave/baseline/quality.md": "# Quality Baseline\n\n## Quality Attributes\nEvolved.\n\n## Verification Commands\nEvolved.\n\n## Operational Constraints\nEvolved.\n",
    "wiki/index.md": "---\ntype: index\n---\n# Evolved index\n",
    "wiki/overview.md": "---\ntype: overview\n---\n# Evolved overview\n",
    "wiki/log.md": "---\ntype: log\n---\n# Evolved log\n"
  };
  const bootstrapFiles = [
    contract(".devweave/project.json", "devweave-project-v1", entries[".devweave/project.json"]),
    contract(".devweave/baseline/product.md", "baseline-product-v1", entries[".devweave/baseline/product.md"]),
    contract(".devweave/baseline/architecture.md", "baseline-architecture-v1", entries[".devweave/baseline/architecture.md"]),
    contract(".devweave/baseline/quality.md", "baseline-quality-v1", entries[".devweave/baseline/quality.md"]),
    contract("wiki/index.md", "wiki-index-v1", entries["wiki/index.md"], "date"),
    contract("wiki/overview.md", "wiki-overview-v1", entries["wiki/overview.md"], "date"),
    contract("wiki/log.md", "wiki-log-v1", entries["wiki/log.md"], "date")
  ];
  const snapshot = await new WorkspaceSnapshotReader(new ProjectionFileSystem(entries), {
    rootName: "evolved",
    rootPath: "file:///evolved",
    bootstrapPaths: [],
    bootstrapFiles
  }).readWorkspace();

  assert.equal(snapshot.bootstrap.complete, true);
  assert.deepEqual(snapshot.bootstrap.missing, []);
  assert.deepEqual(snapshot.bootstrap.conflicts, []);
});

test("snapshot keeps semantic bootstrap conflicts visible", async () => {
  const project = JSON.stringify({
    schema_version: 1,
    managed: false,
    locale: "zh-TW",
    commands: [],
    verification_profiles: { low: [], standard: [], high: [] },
    evidence: { raw_log_limit_bytes: 5_000_000 },
    knowledge: { enabled: true, root: "wiki" }
  });
  const snapshot = await new WorkspaceSnapshotReader(new ProjectionFileSystem({ ".devweave/project.json": project }), {
    rootName: "invalid-evolved",
    rootPath: "file:///invalid-evolved",
    bootstrapFiles: [contract(".devweave/project.json", "devweave-project-v1", "{\"schema_version\":1}")]
  }).readWorkspace();

  assert.equal(snapshot.bootstrap.complete, false);
  assert.deepEqual(snapshot.bootstrap.conflicts, [".devweave/project.json"]);
});
