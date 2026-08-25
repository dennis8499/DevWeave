import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { inflateRawSync } from "node:zlib";

const execFileAsync = promisify(execFile);
const extensionRoot = fileURLToPath(new URL("../", import.meta.url));
const repositoryRoot = resolve(extensionRoot, "..");
const releaseRoot = join(extensionRoot, ".release");
const artifactPath = parseArtifactPath(process.argv.slice(2));
const packageJson = JSON.parse(await readFile(join(extensionRoot, "package.json"), "utf8"));
assert.equal(packageJson.version, "2.0.0", "package version must be 2.0.0");

const artifactInfo = await stat(artifactPath);
assert.ok(artifactInfo.isFile() && artifactInfo.size > 0, "candidate VSIX must be a non-empty regular file");
const artifactBytes = await readFile(artifactPath);
const entries = readZipEntries(artifactBytes);
const expectedEntries = new Set([
  "[Content_Types].xml",
  "extension.vsixmanifest",
  "extension/dist/extension.js",
  "extension/dist/webview/main.js",
  "extension/dist/webview/styles.css",
  "extension/media/devweave.svg",
  "extension/package.json",
  "extension/readme.md",
  "extension/release-provenance.json"
]);
assert.deepEqual(new Set(entries.keys()), expectedEntries, "VSIX entry allowlist mismatch");

const packagedMetadata = JSON.parse(requiredEntry(entries, "extension/package.json").toString("utf8"));
assert.equal(packagedMetadata.version, packageJson.version, "VSIX package version mismatch");
assert.equal(packagedMetadata.main, "./dist/extension.js", "VSIX entrypoint mismatch");
assert.equal(packagedMetadata.icon, "./media/devweave.svg", "VSIX icon entry mismatch");
const vsixManifest = requiredEntry(entries, "extension.vsixmanifest").toString("utf8");
assert.match(vsixManifest, new RegExp(`Version="${packageJson.version.replaceAll(".", "\\.")}"`));

const provenance = JSON.parse(requiredEntry(entries, "extension/release-provenance.json").toString("utf8"));
assert.deepEqual(
  Object.keys(provenance).sort(),
  ["files", "manifest_sha256", "product_version", "schema_version", "source_git_head", "source_status_sha256", "source_tracked_clean"],
  "release provenance fields drifted"
);
assert.equal(provenance.schema_version, 1);
assert.equal(provenance.product_version, packageJson.version);
assert.equal(provenance.source_tracked_clean, true, "release source must have no tracked modifications");

const head = (await execFileAsync("git", ["rev-parse", "HEAD"], { cwd: repositoryRoot })).stdout.toString("utf8").trim();
const statusBytes = Buffer.from((await execFileAsync(
  "git",
  ["status", "--porcelain=v1", "-z", "--untracked-files=no"],
  { cwd: repositoryRoot }
)).stdout);
assert.equal(provenance.source_git_head, head, "release source Git HEAD mismatch");
assert.equal(statusBytes.byteLength, 0, "release verification requires a clean tracked tree");
assert.equal(provenance.source_status_sha256, digest(statusBytes), "release source status digest mismatch");

const expectedSources = new Map([
  ["extension/dist/extension.js", "dist/extension.js"],
  ["extension/dist/webview/main.js", "dist/webview/main.js"],
  ["extension/dist/webview/styles.css", "dist/webview/styles.css"],
  ["extension/media/devweave.svg", "media/devweave.svg"],
  ["extension/package.json", "package.json"],
  ["extension/readme.md", "README.md"]
]);
assert.equal(provenance.files.length, expectedSources.size, "release provenance file count mismatch");
for (const record of provenance.files) {
  assert.deepEqual(Object.keys(record).sort(), ["byte_length", "entry", "sha256", "source"]);
  assert.equal(expectedSources.get(record.entry), record.source, `unexpected source for ${record.entry}`);
  const sourceBytes = await readFile(join(extensionRoot, record.source));
  const entryBytes = requiredEntry(entries, record.entry);
  assert.equal(record.byte_length, sourceBytes.byteLength, `source byte length mismatch for ${record.source}`);
  assert.equal(record.sha256, digest(sourceBytes), `source SHA-256 mismatch for ${record.source}`);
  assert.equal(digest(entryBytes), record.sha256, `packaged entry SHA-256 mismatch for ${record.entry}`);
}
const provenancePayload = {
  schema_version: provenance.schema_version,
  product_version: provenance.product_version,
  source_git_head: provenance.source_git_head,
  source_tracked_clean: provenance.source_tracked_clean,
  source_status_sha256: provenance.source_status_sha256,
  files: provenance.files
};
assert.equal(
  provenance.manifest_sha256,
  digest(Buffer.from(JSON.stringify(provenancePayload), "utf8")),
  "release provenance manifest digest mismatch"
);

const extensionBundle = requiredEntry(entries, "extension/dist/extension.js").toString("utf8");
for (const forbidden of [
  "devweave.copyNextAction",
  "devweave.wikiBootstrap",
  "clipboard.writeText",
  "Bootstrap Codebase Wiki",
  "dist/bootstrap"
]) {
  assert.doesNotMatch(extensionBundle, new RegExp(escapeRegExp(forbidden), "i"), `legacy workflow surface found: ${forbidden}`);
}

console.log(JSON.stringify({
  ok: true,
  version: packageJson.version,
  entries: entries.size,
  source_git_head: head,
  provenance_sha256: provenance.manifest_sha256,
  vsix_sha256: digest(artifactBytes)
}));

function parseArtifactPath(args) {
  if (args.length !== 2 || args[0] !== "--artifact" || !args[1]) {
    throw new Error("Usage: node scripts/verify-package.mjs --artifact <candidate.vsix>");
  }
  const resolvedArtifact = resolve(extensionRoot, args[1]);
  const suffix = relative(resolve(releaseRoot), resolvedArtifact);
  if (suffix === "" || suffix === "." || isAbsolute(suffix) || suffix === ".." || suffix.startsWith(`..${sep}`)) {
    throw new Error("--artifact must point to a file inside vscode-extension/.release/.");
  }
  if (extname(resolvedArtifact).toLowerCase() !== ".vsix") {
    throw new Error("--artifact must use the .vsix extension.");
  }
  return resolvedArtifact;
}

function readZipEntries(bytes) {
  const result = new Map();
  let offset = 0;
  while (offset + 4 <= bytes.byteLength && bytes.readUInt32LE(offset) === 0x04034b50) {
    const method = bytes.readUInt16LE(offset + 8);
    const compressedSize = bytes.readUInt32LE(offset + 18);
    const nameLength = bytes.readUInt16LE(offset + 26);
    const extraLength = bytes.readUInt16LE(offset + 28);
    const nameStart = offset + 30;
    const name = bytes.subarray(nameStart, nameStart + nameLength).toString("utf8");
    const dataStart = nameStart + nameLength + extraLength;
    const dataEnd = dataStart + compressedSize;
    assert.ok(dataEnd <= bytes.byteLength, `truncated VSIX entry ${name}`);
    assert.ok(!result.has(name), `duplicate VSIX entry ${name}`);
    const data = bytes.subarray(dataStart, dataEnd);
    result.set(name, method === 8 ? inflateRawSync(data) : Buffer.from(data));
    offset = dataEnd;
  }
  assert.ok(result.size > 0, "VSIX ZIP has no readable local entries");
  return result;
}

function requiredEntry(entries, name) {
  const value = entries.get(name);
  assert.ok(value, `VSIX is missing ${name}`);
  return value;
}

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
