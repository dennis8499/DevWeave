import assert from "node:assert/strict";
import { readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("release package derives 0.2.1 bundle metadata and preserves rollback artifacts", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as { version?: string };
  const packageLock = JSON.parse(readFileSync(resolve(extensionRoot, "package-lock.json"), "utf8")) as { version?: string; packages?: { ""?: { version?: string } } };
  const esbuild = readFileSync(resolve(extensionRoot, "esbuild.mjs"), "utf8");
  const verifier = readFileSync(resolve(extensionRoot, "scripts/verify-package.mjs"), "utf8");

  assert.equal(packageJson.version, "0.2.1");
  assert.equal(packageLock.version, packageJson.version);
  assert.equal(packageLock.packages?.[""]?.version, packageJson.version);
  assert.match(esbuild, /const version = packageJson\.version/);
  assert.match(esbuild, /bundleVersion: version/);
  assert.match(verifier, /package version must be 0\.2\.1/);
  for (const version of ["0.1.0", "0.2.0", "0.2.1"]) {
    assert.ok(statSync(resolve(extensionRoot, `devweave-control-center-${version}.vsix`)).size > 0, `${version} artifact is missing`);
  }
});
