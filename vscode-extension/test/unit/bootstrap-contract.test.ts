import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("the release bundle contract names every approved DevWeave control input", () => {
  const packageJson = JSON.parse(readFileSync(resolve(extensionRoot, "package.json"), "utf8")) as { version?: string };
  const buildSource = readFileSync(resolve(extensionRoot, "esbuild.mjs"), "utf8");

  assert.equal(packageJson.version, "0.2.2");
  assert.match(buildSource, /const version = packageJson\.version/);
  assert.match(buildSource, /bundleVersion:\s*version/);
  assert.match(buildSource, /AGENTS\.md/);
  assert.match(buildSource, /skills-lock\.json/);
  for (const skill of ["devweave", "codebase-design", "diagnosing-bugs", "grill-me", "grilling", "tdd"]) {
    assert.match(buildSource, new RegExp(skill));
  }
});
