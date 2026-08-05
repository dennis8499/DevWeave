import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("release package derives and verifies only the current 0.2.2 artifact", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as { version?: string };
  const packageLock = JSON.parse(readFileSync(resolve(extensionRoot, "package-lock.json"), "utf8")) as { version?: string; packages?: { ""?: { version?: string } } };
  const esbuild = readFileSync(resolve(extensionRoot, "esbuild.mjs"), "utf8");
  const verifier = readFileSync(resolve(extensionRoot, "scripts/verify-package.mjs"), "utf8");

  assert.equal(packageJson.version, "0.2.2");
  assert.equal(packageLock.version, packageJson.version);
  assert.equal(packageLock.packages?.[""]?.version, packageJson.version);
  assert.match(esbuild, /const version = packageJson\.version/);
  assert.match(esbuild, /bundleVersion: version/);
  assert.match(verifier, /package version must be 0\.2\.2/);
  assert.match(verifier, /const vsixPath = join\(extensionRoot, `devweave-control-center-\$\{version\}\.vsix`\)/);
  assert.match(verifier, /const vsixInfo = await stat\(vsixPath\)/);
  assert.match(verifier, /createHash\("sha256"\)\.update\(vsixBytes\)/);
  assert.match(verifier, /assert\.equal\(manifest\.files\.length, 58/);
  assert.match(verifier, /assert\.equal\(vsixEntries\.size, 119/);
  assert.match(verifier, /native-question-contract\.md/);
  assert.match(verifier, /VSIX SHA-256/);
  assert.doesNotMatch(verifier, /legacyArtifacts|0\.1\.0|0\.2\.0/);
});
