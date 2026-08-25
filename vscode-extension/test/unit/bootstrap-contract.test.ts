import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("the V2 production build excludes transitional bootstrap inputs", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as { version?: string };
  const buildSource = readFileSync(resolve(extensionRoot, "esbuild.mjs"), "utf8");
  const packageSource = readFileSync(resolve(extensionRoot, "scripts", "package-vsix.mjs"), "utf8");

  assert.equal(packageJson.version, "2.0.0");
  assert.match(buildSource, /src\/extension\.ts/);
  assert.match(buildSource, /webview\/main\.ts/);
  assert.doesNotMatch(buildSource, /bootstrap|skills-lock|companionSkills/);
  assert.match(packageSource, /packagedSources/);
  assert.match(packageSource, /release-provenance\.json/);
  for (const legacy of ["codebase-design", "diagnosing-bugs", "grill-me", "grilling", "tdd"]) {
    assert.doesNotMatch(buildSource, new RegExp(legacy));
    assert.doesNotMatch(packageSource, new RegExp(legacy));
  }
});
