import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("release package is wired through the candidate-first orchestrator", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as { version?: string; scripts?: { package?: string } };
  const packageLock = JSON.parse(readFileSync(resolve(extensionRoot, "package-lock.json"), "utf8")) as { version?: string; packages?: { ""?: { version?: string } } };
  const esbuild = readFileSync(resolve(extensionRoot, "esbuild.mjs"), "utf8");
  const builder = readFileSync(resolve(extensionRoot, "scripts/package-vsix.mjs"), "utf8");
  const verifier = readFileSync(resolve(extensionRoot, "scripts/verify-package.mjs"), "utf8");
  const orchestrator = readFileSync(resolve(extensionRoot, "scripts/release-orchestrator.mjs"), "utf8");

  assert.equal(packageJson.version, "2.0.0");
  assert.equal(packageLock.version, packageJson.version);
  assert.equal(packageLock.packages?.[""]?.version, packageJson.version);
  assert.equal(packageJson.scripts?.package, "node esbuild.mjs --production && node scripts/release-orchestrator.mjs");
  assert.doesNotMatch(esbuild, /bootstrap|companionSkills|skills-lock/);
  assert.match(esbuild, /src\/extension\.ts/);
  assert.match(esbuild, /webview\/main\.ts/);
  assert.match(builder, /--output/);
  assert.match(builder, /Usage: node scripts\/package-vsix\.mjs --output/);
  assert.match(builder, /flag: "wx"/);
  assert.match(builder, /must name a unique candidate artifact/);
  assert.match(builder, /packagedSources/);
  assert.match(builder, /release-provenance\.json/);
  assert.match(builder, /source_tracked_clean/);
  assert.match(builder, /source_status_sha256/);
  assert.match(verifier, /package version must be 2\.0\.0/);
  assert.match(verifier, /--artifact/);
  assert.match(verifier, /Usage: node scripts\/verify-package\.mjs --artifact/);
  assert.match(verifier, /const artifactPath = parseArtifactPath/);
  assert.match(verifier, /stat\(artifactPath\)/);
  assert.match(verifier, /expectedEntries/);
  assert.match(verifier, /release provenance manifest digest mismatch/);
  assert.match(verifier, /source Git HEAD mismatch/);
  assert.match(verifier, /release source must have no tracked modifications/);
  assert.match(verifier, /devweave\.copyNextAction/);
  assert.doesNotMatch(verifier, /native-question-contract|companions\/|retainedVsix/);
  assert.match(orchestrator, /package-vsix\.mjs/);
  assert.match(orchestrator, /--output/);
  assert.match(orchestrator, /verify-package\.mjs/);
  assert.match(orchestrator, /--artifact/);
  assert.match(orchestrator, /join\(extensionRoot, "\.release"\)/);
  assert.match(orchestrator, /rename\(candidatePath, currentArtifact\)/);
  assert.doesNotMatch(verifier, /legacyArtifacts|0\.1\.0|0\.2\.0|0\.2\.1|0\.2\.2|0\.2\.3/);
});

test("package and verifier scripts fail closed without their artifact arguments", () => {
  assert.throws(
    () => execFileSync(process.execPath, [resolve(extensionRoot, "scripts/package-vsix.mjs")], { cwd: extensionRoot, encoding: "utf8", stdio: "pipe" }),
    /--output/
  );
  assert.throws(
    () => execFileSync(process.execPath, [resolve(extensionRoot, "scripts/verify-package.mjs")], { cwd: extensionRoot, encoding: "utf8", stdio: "pipe" }),
    /--artifact/
  );
});
