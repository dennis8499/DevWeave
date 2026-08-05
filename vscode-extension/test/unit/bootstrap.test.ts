import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import {
  BootstrapInstaller,
  BootstrapPathKind,
  BootstrapResourceReader,
  BootstrapWorkspace,
  BootstrapBundle
} from "../../src/bootstrap";
import type { BootstrapCompatibilityKind } from "../../src/bootstrap-compat";

class MemoryBootstrapWorkspace implements BootstrapWorkspace {
  private readonly files = new Map<string, Uint8Array>();
  private readonly directories = new Set<string>();
  private readonly symlinks = new Set<string>();
  public failWritePath: string | undefined;

  public async stat(relativePath: string): Promise<BootstrapPathKind> {
    if (this.files.has(relativePath)) return "file";
    if (this.directories.has(relativePath)) return "directory";
    if (this.symlinks.has(relativePath)) return "symlink";
    return "absent";
  }

  public async readBytes(relativePath: string): Promise<Uint8Array> {
    const bytes = this.files.get(relativePath);
    if (!bytes) throw new Error(`Missing file: ${relativePath}`);
    return bytes.slice();
  }

  public async writeBytes(relativePath: string, bytes: Uint8Array): Promise<void> {
    if (relativePath === this.failWritePath) throw new Error("simulated write failure");
    this.files.set(relativePath, bytes.slice());
  }

  public async createDirectory(relativePath: string): Promise<void> {
    this.directories.add(relativePath);
  }

  public async delete(relativePath: string): Promise<void> {
    this.files.delete(relativePath);
    this.directories.delete(relativePath);
  }

  public seedDirectory(relativePath: string): void {
    this.directories.add(relativePath);
  }

  public seedFile(relativePath: string, text: string): void {
    this.files.set(relativePath, new TextEncoder().encode(text));
  }

  public seedSymlink(relativePath: string): void {
    this.symlinks.add(relativePath);
  }

  public text(relativePath: string): string {
    const bytes = this.files.get(relativePath);
    return bytes ? new TextDecoder().decode(bytes) : "";
  }
}

class MemoryBootstrapResources implements BootstrapResourceReader {
  public constructor(private readonly entries: Record<string, string>) {}

  public async read(source: string): Promise<Uint8Array> {
    const value = this.entries[source];
    if (value === undefined) throw new Error(`Missing resource: ${source}`);
    return new TextEncoder().encode(value);
  }
}

function bundle(): BootstrapBundle {
  return {
    schemaVersion: 1,
    bundleVersion: "test",
    directories: [".devweave", "wiki"],
    files: [{
      source: "project.json",
      destination: ".devweave/project.json",
      transform: "copy",
      byteLength: 17,
      sha256: "05c7e868def5b9baf9c16edbd5834ff501ff38aff6bbab33780a2a89fe28c577"
    }]
  };
}

function compatibleProject(): string {
  return JSON.stringify({
    schema_version: 1,
    managed: true,
    locale: "zh-TW",
    commands: [],
    verification_profiles: { low: [], standard: [], high: [] },
    evidence: { raw_log_limit_bytes: 5_000_000, version_summaries: true },
    knowledge: { enabled: true, root: "wiki" }
  });
}

function fileEntry(source: string, destination: string, text: string, compatibility: BootstrapCompatibilityKind): BootstrapBundle["files"][number] {
  const bytes = new TextEncoder().encode(text);
  return {
    source,
    destination,
    transform: "copy",
    byteLength: bytes.byteLength,
    sha256: createHash("sha256").update(bytes).digest("hex"),
    existingPolicy: "adopt-compatible",
    compatibility
  };
}

test("BootstrapInstaller installs a missing project file through the workspace seam", async () => {
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });
  const report = await new BootstrapInstaller({ now: () => "2026-08-03" }).install(bundle(), resources, workspace);

  assert.equal(report.ok, true);
  assert.equal(report.complete, true);
  assert.equal(report.status, "initialized");
  assert.ok(report.created.includes(".devweave/project.json"));
  assert.equal(workspace.text(".devweave/project.json"), '{"managed":true}\n');
  console.log("[walkthrough] fresh-install initialized=true partial-state=none");
});

test("BootstrapInstaller fails closed when an existing target conflicts", async () => {
  const workspace = new MemoryBootstrapWorkspace();
  workspace.seedDirectory(".devweave");
  workspace.seedFile(".devweave/project.json", '{"managed":false}\n');
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });

  const report = await new BootstrapInstaller({ now: () => "2026-08-03" }).install(bundle(), resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.status, "partial");
  assert.ok(report.conflicts.some((item) => item.path === ".devweave/project.json"));
  assert.ok(report.created.includes("wiki"));
  assert.equal(workspace.text(".devweave/project.json"), '{"managed":false}\n');
});

test("BootstrapInstaller inspects a partial workspace without writing", async () => {
  const partial = bundle();
  partial.files.push({
    source: "second.json",
    destination: ".devweave/second.json",
    transform: "copy",
    byteLength: 16,
    sha256: "6783a86f115c3d54918b7e911557fb8f4339f76091e4b4d4d11d4086ff41efec"
  });
  const workspace = new MemoryBootstrapWorkspace();
  workspace.seedDirectory(".devweave");
  workspace.seedFile(".devweave/project.json", '{"managed":false}\n');
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n', "second.json": '{"second":true}\n' });

  const inspection = await new BootstrapInstaller().inspect(partial, resources, workspace);

  assert.equal(inspection.complete, false);
  assert.ok(inspection.missing.includes(".devweave/second.json"));
  assert.ok(inspection.conflicts.some((item) => item.path === ".devweave/project.json"));
  assert.equal(await workspace.stat(".devweave/second.json"), "absent");
});

test("BootstrapInstaller repairs non-conflicting files without overwriting a conflict", async () => {
  const partial = bundle();
  partial.files.push({
    source: "second.json",
    destination: ".devweave/second.json",
    transform: "copy",
    byteLength: 16,
    sha256: "6783a86f115c3d54918b7e911557fb8f4339f76091e4b4d4d11d4086ff41efec"
  });
  const workspace = new MemoryBootstrapWorkspace();
  workspace.seedDirectory(".devweave");
  workspace.seedFile(".devweave/project.json", '{"managed":false}\n');
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n', "second.json": '{"second":true}\n' });

  const report = await new BootstrapInstaller().install(partial, resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.complete, false);
  assert.equal(report.status, "partial");
  assert.ok(report.created.includes(".devweave/second.json"));
  assert.ok(report.conflicts.some((item) => item.path === ".devweave/project.json"));
  assert.equal(workspace.text(".devweave/project.json"), '{"managed":false}\n');
  assert.equal(workspace.text(".devweave/second.json"), '{"second":true}\n');
  console.log("[walkthrough] conflict-fail-closed conflict-preserved=true nonconflicting-file=installed");
});

test("BootstrapInstaller is idempotent for compatible existing bytes", async () => {
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });
  const installer = new BootstrapInstaller({ now: () => "2026-08-03" });

  await installer.install(bundle(), resources, workspace);
  const report = await installer.install(bundle(), resources, workspace);

  assert.equal(report.ok, true);
  assert.equal(report.complete, true);
  assert.equal(report.status, "already_initialized");
  assert.deepEqual(report.created, []);
  assert.ok(report.adopted.includes(".devweave/project.json"));
});

test("BootstrapInstaller rejects a bundle integrity mismatch before writing", async () => {
  const invalid = bundle();
  invalid.files[0].sha256 = "0".repeat(64);
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });

  const report = await new BootstrapInstaller({ now: () => "2026-08-03" }).install(invalid, resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.status, "failed");
  assert.equal(report.created.length, 0);
  assert.ok(report.errors.some((item) => item.path === "project.json" && item.reason.includes("integrity")));
  assert.equal(await workspace.stat(".devweave"), "absent");
});

test("BootstrapInstaller rejects traversal destinations before writing", async () => {
  const invalid = bundle();
  invalid.files[0].destination = "../outside.json";
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });

  const report = await new BootstrapInstaller({ now: () => "2026-08-03" }).install(invalid, resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.created.length, 0);
  assert.ok(report.errors.some((item) => item.path === "manifest.json"));
  assert.equal(await workspace.stat("outside.json"), "absent");
});

test("BootstrapInstaller rejects a symlink ancestor before writing", async () => {
  const workspace = new MemoryBootstrapWorkspace();
  workspace.seedSymlink(".devweave");
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });

  const report = await new BootstrapInstaller({ now: () => "2026-08-03" }).install(bundle(), resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.status, "partial");
  assert.ok(report.conflicts.some((item) => item.path === ".devweave"));
  assert.ok(report.created.includes("wiki"));
  assert.equal(await workspace.stat(".devweave/project.json"), "absent");
});

test("BootstrapInstaller rolls back files created before a later write fails", async () => {
  const secondText = '{"second":true}\n';
  const secondBundle = bundle();
  secondBundle.files.push({
    source: "second.json",
    destination: ".devweave/second.json",
    transform: "copy",
    byteLength: 16,
    sha256: "6783a86f115c3d54918b7e911557fb8f4339f76091e4b4d4d11d4086ff41efec"
  });
  const workspace = new MemoryBootstrapWorkspace();
  workspace.failWritePath = ".devweave/second.json";
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n', "second.json": secondText });

  const report = await new BootstrapInstaller({ now: () => "2026-08-03" }).install(secondBundle, resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.status, "failed");
  assert.ok(report.rolledBack.includes(".devweave/project.json"));
  assert.equal(await workspace.stat(".devweave/project.json"), "absent");
  assert.equal(await workspace.stat(".devweave/second.json"), "absent");
  console.log("[walkthrough] write-failure rollback=complete partial-state=none");
});

test("BootstrapInstaller rejects malformed manifest entries without throwing", async () => {
  const malformed = {
    schemaVersion: 1,
    bundleVersion: "test",
    directories: [],
    files: [null]
  } as unknown as BootstrapBundle;
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({});

  const report = await new BootstrapInstaller().install(malformed, resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.status, "failed");
  assert.equal(report.created.length, 0);
});

test("BootstrapInstaller applies only the declared date transform", async () => {
  const datedBundle = bundle();
  datedBundle.files[0] = {
    ...datedBundle.files[0],
    source: "wiki.md",
    destination: "wiki/index.md",
    transform: "date",
    byteLength: 11,
    sha256: "ae144ef1d4b8816e5006600f4ff65063b4756caad4be63ad9eaea296a2ca2b8e"
  };
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "wiki.md": "date {date}" });

  const report = await new BootstrapInstaller({ now: () => "2026-08-03T10:00:00Z" }).install(
    datedBundle,
    resources,
    workspace
  );

  assert.equal(report.ok, true);
  assert.equal(workspace.text("wiki/index.md"), "date 2026-08-03");
});

test("BootstrapInstaller normalizes Windows-style and POSIX-style relative destinations", async () => {
  const windowsBundle = bundle();
  windowsBundle.directories = [".devweave\\nested", "wiki"];
  windowsBundle.files[0] = {
    ...windowsBundle.files[0],
    destination: ".devweave\\nested\\project.json"
  };
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });

  const report = await new BootstrapInstaller().install(windowsBundle, resources, workspace);

  assert.equal(report.ok, true);
  assert.ok(report.created.includes(".devweave/nested/project.json"));
  assert.equal(await workspace.stat(".devweave/nested/project.json"), "file");
});

test("BootstrapInstaller adopts evolved project content through the declared semantic contract", async () => {
  const bundled = compatibleProject();
  const existing = JSON.stringify({ ...JSON.parse(bundled), commands: [], custom_metadata: "kept" }, null, 2);
  const workspace = new MemoryBootstrapWorkspace();
  workspace.seedDirectory(".devweave");
  workspace.seedFile(".devweave/project.json", existing);
  const resources = new MemoryBootstrapResources({ "project.json": bundled });
  const adoptionBundle: BootstrapBundle = {
    schemaVersion: 1,
    bundleVersion: "test",
    directories: [".devweave"],
    files: [fileEntry("project.json", ".devweave/project.json", bundled, "devweave-project-v1")]
  };

  const report = await new BootstrapInstaller().install(adoptionBundle, resources, workspace);

  assert.equal(report.ok, true);
  assert.deepEqual(report.conflicts, []);
  assert.deepEqual(report.created, []);
  assert.deepEqual(report.adopted, [".devweave/project.json"]);
  assert.equal(workspace.text(".devweave/project.json"), existing);
  console.log("[walkthrough] evolved-workspace adopted=true custom-content-preserved=true");
});

test("BootstrapInstaller explains semantic incompatibility instead of adopting identity drift", async () => {
  const bundled = compatibleProject();
  const existing = JSON.stringify({ ...JSON.parse(bundled), managed: false }, null, 2);
  const workspace = new MemoryBootstrapWorkspace();
  workspace.seedDirectory(".devweave");
  workspace.seedFile(".devweave/project.json", existing);
  const resources = new MemoryBootstrapResources({ "project.json": bundled });
  const adoptionBundle: BootstrapBundle = {
    schemaVersion: 1,
    bundleVersion: "test",
    directories: [".devweave"],
    files: [fileEntry("project.json", ".devweave/project.json", bundled, "devweave-project-v1")]
  };

  const report = await new BootstrapInstaller().install(adoptionBundle, resources, workspace);

  assert.equal(report.ok, false);
  assert.ok(report.conflicts.some((item) => item.path === ".devweave/project.json" && /managed/i.test(item.reason)));
  assert.equal(workspace.text(".devweave/project.json"), existing);
});

test("BootstrapInstaller rejects unknown compatibility metadata before any write", async () => {
  const invalid = bundle();
  invalid.files[0] = {
    ...invalid.files[0],
    existingPolicy: "adopt-compatible",
    compatibility: "unknown-contract"
  } as unknown as BootstrapBundle["files"][number];
  const workspace = new MemoryBootstrapWorkspace();
  const resources = new MemoryBootstrapResources({ "project.json": '{"managed":true}\n' });

  const report = await new BootstrapInstaller().install(invalid, resources, workspace);

  assert.equal(report.ok, false);
  assert.equal(report.created.length, 0);
  assert.ok(report.errors.some((item) => item.path === "manifest.json" && /compatibility/i.test(item.reason)));
  assert.equal(await workspace.stat(".devweave"), "absent");
});
