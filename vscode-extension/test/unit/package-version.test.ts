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
  assert.match(esbuild, /const version = packageJson\.version/);
  assert.match(esbuild, /bundleVersion: version/);
  assert.match(builder, /--output/);
  assert.match(builder, /Usage: node scripts\/package-vsix\.mjs --output/);
  assert.match(builder, /flag: "wx"/);
  assert.match(builder, /must name a unique candidate artifact/);
  assert.match(verifier, /package version must be 2\.0\.0/);
  assert.match(verifier, /--artifact/);
  assert.match(verifier, /Usage: node scripts\/verify-package\.mjs --artifact/);
  assert.match(verifier, /join\(extensionRoot, "\.\.", "\.codex", "hooks\.json"\)/);
  assert.match(verifier, /commandWindows/);
  assert.match(verifier, /\^\(Bash\|apply_patch\|Edit\|Write\)\$/);
  assert.match(verifier, /python3 -X utf8 -B/);
  assert.match(verifier, /powershell\\\.exe -NoLogo -NoProfile -NonInteractive -Command/);
  assert.match(verifier, /py -3 -X utf8 -B/);
  assert.match(verifier, /const artifactPath = parseArtifactPath/);
  assert.match(verifier, /stat\(artifactPath\)/);
  assert.match(verifier, /createHash\("sha256"\)\.update\(vsixBytes\)/);
  assert.match(verifier, /assert\.equal\(manifest\.files\.length, 58/);
  assert.match(verifier, /assert\.equal\(vsixEntries\.size, 119/);
  assert.match(verifier, /native-question-contract\.md/);
  assert.match(verifier, /VSIX SHA-256/);
  assert.match(orchestrator, /package-vsix\.mjs/);
  assert.match(orchestrator, /--output/);
  assert.match(orchestrator, /verify-package\.mjs/);
  assert.match(orchestrator, /--artifact/);
  assert.match(orchestrator, /rename\(candidatePath, currentArtifact\)/);
  assert.doesNotMatch(verifier, /legacyArtifacts|0\.1\.0|0\.2\.0/);
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
