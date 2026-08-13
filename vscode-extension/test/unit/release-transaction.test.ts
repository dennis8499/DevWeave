import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

async function loadReleaseTransaction() {
  // @ts-ignore The production release seam is a JavaScript CLI module with a runtime-tested contract.
  const module = await import("../../scripts/release-orchestrator.mjs");
  return module.runReleaseTransaction as (options: Record<string, unknown>) => Promise<unknown>;
}

async function withReleaseFiles(run: (paths: { root: string; current: string; candidate: string }) => Promise<void>) {
  const root = await mkdtemp(join(tmpdir(), "devweave-release-"));
  const paths = {
    root,
    current: join(root, "current.vsix"),
    candidate: join(root, "candidate.vsix")
  };
  try {
    await writeFile(paths.current, "known-good-current", "utf8");
    await run(paths);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

test("verification failure preserves current artifact and cleans candidate", async () => {
  await withReleaseFiles(async ({ root, current, candidate }) => {
    const runReleaseTransaction = await loadReleaseTransaction();
    await writeFile(candidate, "invalid-candidate", "utf8");
    await assert.rejects(
      runReleaseTransaction({
        extensionRoot: root,
        currentArtifact: current,
        candidatePath: candidate,
        buildCandidate: async () => undefined,
        verifyCandidate: async () => { throw new Error("provenance mismatch"); }
      }),
      /provenance mismatch/
    );
    assert.equal(await readFile(current, "utf8"), "known-good-current");
    await assert.rejects(readFile(candidate, "utf8"), { code: "ENOENT" });
  });
});

test("verified candidate is atomically promoted and then cleaned", async () => {
  await withReleaseFiles(async ({ root, current, candidate }) => {
    const runReleaseTransaction = await loadReleaseTransaction();
    await runReleaseTransaction({
      extensionRoot: root,
      currentArtifact: current,
      candidatePath: candidate,
      buildCandidate: async (path: string) => { await writeFile(path, "verified-candidate", "utf8"); },
      verifyCandidate: async (path: string) => { assert.equal(await readFile(path, "utf8"), "verified-candidate"); }
    });
    assert.equal(await readFile(current, "utf8"), "verified-candidate");
    await assert.rejects(readFile(candidate, "utf8"), { code: "ENOENT" });
  });
});

test("promotion failure preserves current artifact and cleans candidate", async () => {
  await withReleaseFiles(async ({ root, current, candidate }) => {
    const runReleaseTransaction = await loadReleaseTransaction();
    await assert.rejects(
      runReleaseTransaction({
        extensionRoot: root,
        currentArtifact: current,
        candidatePath: candidate,
        buildCandidate: async (path: string) => { await writeFile(path, "verified-candidate", "utf8"); },
        verifyCandidate: async () => undefined,
        promote: async () => { throw new Error("rename blocked"); }
      }),
      /rename blocked/
    );
    assert.equal(await readFile(current, "utf8"), "known-good-current");
    await assert.rejects(readFile(candidate, "utf8"), { code: "ENOENT" });
  });
});
