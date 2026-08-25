import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { inflateRawSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const extensionRoot = fileURLToPath(new URL("../", import.meta.url));
const artifactPath = parseArtifactPath(process.argv.slice(2));
const packageJson = JSON.parse(await readFile(join(extensionRoot, "package.json"), "utf8"));
const version = packageJson.version;
const execFileAsync = promisify(execFile);
assert.equal(version, "2.0.0", "package version must be 2.0.0");

const bootstrapRoot = join(extensionRoot, "dist", "bootstrap");
const manifest = JSON.parse(await readFile(join(bootstrapRoot, "manifest.json"), "utf8"));
assert.equal(manifest.bundleVersion, version, "bundle and Extension versions must match");
assert.equal(manifest.packageVersion, version, "manifest package version must match Extension version");
assert.equal(manifest.files.length, 58, "bootstrap manifest must contain the certified 58 files");
assert.equal(manifest.bootstrapFileCount, manifest.files.length, "manifest bootstrap file count must match entries");
const sourceGitHead = (await execFileAsync("git", ["rev-parse", "HEAD"], { cwd: join(extensionRoot, ".."), encoding: "utf8" })).stdout.trim();
assert.equal(manifest.sourceGitHead, sourceGitHead, "manifest source Git HEAD must match the current source");
const manifestPayload = { schemaVersion: manifest.schemaVersion, bundleVersion: manifest.bundleVersion, directories: manifest.directories, files: manifest.files };
assert.equal(createHash("sha256").update(JSON.stringify(manifestPayload), "utf8").digest("hex"), manifest.manifestSha256, "manifest canonical hash mismatch");
const bootstrapHook = JSON.parse(await readFile(join(bootstrapRoot, "hooks.json"), "utf8"));
const repositoryHook = JSON.parse(await readFile(join(extensionRoot, "..", ".codex", "hooks.json"), "utf8"));
assert.deepEqual(bootstrapHook, repositoryHook, "bootstrap hook must be source-derived from repository .codex/hooks.json");
const hookGroups = repositoryHook.hooks?.PreToolUse;
assert.ok(Array.isArray(hookGroups) && hookGroups.length === 1, "repository must contain one PreToolUse group");
assert.equal(hookGroups[0].matcher, "^(Bash|apply_patch|Edit|Write)$", "PreToolUse matcher must stay exact");
const hookHandlers = hookGroups[0].hooks;
assert.ok(Array.isArray(hookHandlers) && hookHandlers.length === 1, "repository must contain one PreToolUse handler");
const hookCommand = hookHandlers[0];
assert.equal(hookCommand.type, "command", "PreToolUse handler must be a command hook");
assert.equal(hookCommand.timeout, 30, "PreToolUse timeout must remain bounded");
assert.equal(hookCommand.statusMessage, "Checking DevWeave gates");
assert.match(hookCommand.command, /python3 -X utf8 -B/);
assert.match(hookCommand.command, /\$\(git rev-parse --show-toplevel\)/);
assert.match(hookCommand.commandWindows, /powershell\.exe -NoLogo -NoProfile -NonInteractive -Command/);
assert.match(hookCommand.commandWindows, /py -3 -X utf8 -B/);
assert.match(hookCommand.commandWindows, /Join-Path \(git rev-parse --show-toplevel\)/);
assert.match(hookCommand.commandWindows, /\[Console\]::InputEncoding = \[System\.Text\.UTF8Encoding\]::new\(0\)/);
assert.match(hookCommand.commandWindows, /\[Console\]::OutputEncoding = \[System\.Text\.UTF8Encoding\]::new\(0\)/);
assert.doesNotMatch(hookCommand.commandWindows, /\$repo/);
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

const vsixInfo = await stat(artifactPath);
assert.ok(vsixInfo.isFile(), "the candidate VSIX must be a regular file");
assert.ok(vsixInfo.size > 0, "the candidate VSIX must be non-empty");
const retainedVsixInfo = await stat(join(extensionRoot, "devweave-control-center-0.2.2.vsix"));
assert.ok(retainedVsixInfo.isFile(), "the previous 0.2.2 VSIX must remain available");
const vsixBytes = await readFile(artifactPath);
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
console.log(`Verified ${artifactPath}: ${version}, ${manifest.files.length} bootstrap files and ${vsixEntries.size} VSIX entries. Manifest SHA-256: ${manifest.manifestSha256}. VSIX SHA-256: ${vsixSha256}`);

function parseArtifactPath(args) {
  if (args.length !== 2 || args[0] !== "--artifact" || !args[1]) {
    throw new Error("Usage: node scripts/verify-package.mjs --artifact <candidate.vsix>");
  }

  const resolvedArtifact = resolve(extensionRoot, args[1]);
  const suffix = relative(extensionRoot, resolvedArtifact);
  if (suffix === "" || suffix === "." || isAbsolute(suffix) || suffix === ".." || suffix.startsWith(`..${sep}`)) {
    throw new Error("--artifact must point to a file inside the extension root.");
  }
  if (extname(resolvedArtifact).toLowerCase() !== ".vsix") {
    throw new Error("--artifact must use the .vsix extension.");
  }
  return resolvedArtifact;
}

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
