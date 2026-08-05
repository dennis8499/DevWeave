import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { inflateRawSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const extensionRoot = fileURLToPath(new URL("../", import.meta.url));
const packageJson = JSON.parse(await readFile(join(extensionRoot, "package.json"), "utf8"));
const version = packageJson.version;
assert.equal(version, "0.2.2", "package version must be 0.2.2");

const bootstrapRoot = join(extensionRoot, "dist", "bootstrap");
const manifest = JSON.parse(await readFile(join(bootstrapRoot, "manifest.json"), "utf8"));
assert.equal(manifest.bundleVersion, version, "bundle and Extension versions must match");
assert.equal(manifest.files.length, 58, "bootstrap manifest must contain the certified 58 files");
const bootstrapHook = JSON.parse(await readFile(join(bootstrapRoot, "hooks.json"), "utf8"));
const bootstrapHookCommand = bootstrapHook.hooks?.PreToolUse?.[0]?.hooks?.[0];
assert.ok(bootstrapHookCommand, "bootstrap must contain the PreToolUse command hook");
assert.match(bootstrapHookCommand.command, /powershell\.exe -NoLogo -NoProfile -NonInteractive -Command/);
assert.match(bootstrapHookCommand.command, /python\.exe -X utf8 -B/);
assert.match(bootstrapHookCommand.command, /Join-Path \(git rev-parse --show-toplevel\)/);
assert.doesNotMatch(bootstrapHookCommand.command, /\$repo/);
assert.equal(Object.hasOwn(bootstrapHookCommand, "commandWindows"), false, "bootstrap must not rely on commandWindows");
const destinations = new Set(manifest.files.map((file) => file.destination));
const compatibleContracts = new Map([
  [".devweave/project.json", "devweave-project-v1"],
  [".devweave/baseline/product.md", "baseline-product-v1"],
  [".devweave/baseline/architecture.md", "baseline-architecture-v1"],
  [".devweave/baseline/quality.md", "baseline-quality-v1"],
  ["wiki/index.md", "wiki-index-v1"],
  ["wiki/overview.md", "wiki-overview-v1"],
  ["wiki/log.md", "wiki-log-v1"]
]);
for (const required of [
  "AGENTS.md",
  "skills-lock.json",
  ".codex/hooks.json",
  ".devweave/project.json",
  ".devweave/baseline/product.md",
  ".devweave/baseline/architecture.md",
  ".devweave/baseline/quality.md",
  "wiki/index.md",
  "wiki/overview.md",
  ".agents/skills/devweave/SKILL.md",
  ".agents/skills/devweave/references/native-question-contract.md",
  ".agents/skills/codebase-design/SKILL.md",
  ".agents/skills/diagnosing-bugs/SKILL.md",
  ".agents/skills/grill-me/SKILL.md",
  ".agents/skills/grilling/SKILL.md",
  ".agents/skills/tdd/SKILL.md"
]) {
  assert.ok(destinations.has(required), `manifest is missing ${required}`);
}
for (const file of manifest.files) {
  assert.ok(file.existingPolicy === "exact" || file.existingPolicy === "adopt-compatible", `invalid existing policy for ${file.destination}`);
  if (compatibleContracts.has(file.destination)) {
    assert.equal(file.existingPolicy, "adopt-compatible", `compatible policy missing for ${file.destination}`);
    assert.equal(file.compatibility, compatibleContracts.get(file.destination), `compatibility kind mismatch for ${file.destination}`);
  } else {
    assert.equal(file.existingPolicy, "exact", `non-data bootstrap path must remain exact: ${file.destination}`);
    assert.equal(file.compatibility, undefined, `exact bootstrap path must not declare compatibility: ${file.destination}`);
  }
  assert.doesNotMatch(file.destination, /(?:^|\/)(?:README|docs|tests?|fixtures|work-items|history)(?:\/|$)/i, `forbidden bootstrap destination ${file.destination}`);
  const sourceBytes = await readFile(join(bootstrapRoot, file.source));
  assert.equal(sourceBytes.byteLength, file.byteLength, `byte length mismatch for ${file.source}`);
  assert.equal(createHash("sha256").update(sourceBytes).digest("hex"), file.sha256, `hash mismatch for ${file.source}`);
}

const vsixPath = join(extensionRoot, `devweave-control-center-${version}.vsix`);
const vsixInfo = await stat(vsixPath);
assert.ok(vsixInfo.isFile(), "the current VSIX must be a regular file");
assert.ok(vsixInfo.size > 0, "the current VSIX must be non-empty");
const vsixBytes = await readFile(vsixPath);
const vsixSha256 = createHash("sha256").update(vsixBytes).digest("hex");
const vsixEntries = readZipEntries(vsixBytes);
assert.equal(vsixEntries.size, 119, "VSIX must contain the certified 119 entries");
const packageEntry = JSON.parse(vsixEntries.get("extension/package.json").toString("utf8"));
assert.equal(packageEntry.version, version, "VSIX package metadata version mismatch");
const vsixManifest = vsixEntries.get("extension.vsixmanifest").toString("utf8");
assert.match(vsixManifest, new RegExp(`Version="${version.replaceAll(".", "\\.")}"`));
for (const required of [
  "extension/dist/bootstrap/manifest.json",
  "extension/dist/bootstrap/AGENTS.md",
  "extension/dist/bootstrap/skills-lock.json",
  "extension/dist/bootstrap/skill/SKILL.md",
  "extension/dist/bootstrap/skill/references/native-question-contract.md",
  "extension/dist/bootstrap/companions/codebase-design/SKILL.md",
  "extension/dist/bootstrap/companions/diagnosing-bugs/SKILL.md",
  "extension/dist/bootstrap/companions/grill-me/SKILL.md",
  "extension/dist/bootstrap/companions/grilling/SKILL.md",
  "extension/dist/bootstrap/companions/tdd/SKILL.md"
]) {
  assert.ok(vsixEntries.has(required), `VSIX is missing ${required}`);
}
console.log(`Verified ${version}: ${manifest.files.length} bootstrap files and ${vsixEntries.size} VSIX entries. VSIX SHA-256: ${vsixSha256}`);

function readZipEntries(bytes) {
  const entries = new Map();
  let offset = 0;
  while (offset + 4 <= bytes.byteLength && bytes.readUInt32LE(offset) === 0x04034b50) {
    const method = bytes.readUInt16LE(offset + 8);
    const compressedSize = bytes.readUInt32LE(offset + 18);
    const nameLength = bytes.readUInt16LE(offset + 26);
    const extraLength = bytes.readUInt16LE(offset + 28);
    const nameStart = offset + 30;
    const name = bytes.subarray(nameStart, nameStart + nameLength).toString("utf8");
    const dataStart = nameStart + nameLength + extraLength;
    const data = bytes.subarray(dataStart, dataStart + compressedSize);
    entries.set(name, method === 8 ? inflateRawSync(data) : Buffer.from(data));
    offset = dataStart + compressedSize;
  }
  assert.ok(entries.size > 0, "VSIX ZIP has no readable local entries");
  return entries;
}
