import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { deflateRawSync } from "node:zlib";

const execFileAsync = promisify(execFile);
const extensionRoot = fileURLToPath(new URL("../", import.meta.url));
const repositoryRoot = resolve(extensionRoot, "..");
const releaseRoot = join(extensionRoot, ".release");
const packageJson = JSON.parse(await readFile(join(extensionRoot, "package.json"), "utf8"));
const outputPath = parseOutputPath(process.argv.slice(2));

const packagedSources = [
  ["README.md", "readme.md"],
  ["dist/extension.js", "dist/extension.js"],
  ["dist/webview/main.js", "dist/webview/main.js"],
  ["dist/webview/styles.css", "dist/webview/styles.css"],
  ["media/devweave.svg", "media/devweave.svg"],
  ["package.json", "package.json"]
];

const files = [];
for (const [source, destination] of packagedSources) {
  const bytes = await readFile(join(extensionRoot, source));
  files.push({
    source,
    entry: `extension/${destination}`,
    byte_length: bytes.byteLength,
    sha256: digest(bytes),
    bytes
  });
}
files.sort((left, right) => left.entry.localeCompare(right.entry));

const gitHeadResult = await execFileAsync("git", ["rev-parse", "HEAD"], { cwd: repositoryRoot });
const gitStatusResult = await execFileAsync(
  "git",
  ["status", "--porcelain=v1", "-z", "--untracked-files=no"],
  { cwd: repositoryRoot }
);
const sourceGitHead = gitHeadResult.stdout.toString("utf8").trim();
const statusBytes = Buffer.from(gitStatusResult.stdout);
if (!/^[a-f0-9]{40,64}$/i.test(sourceGitHead)) {
  throw new Error("Unable to resolve the source Git HEAD.");
}

const provenancePayload = {
  schema_version: 1,
  product_version: packageJson.version,
  source_git_head: sourceGitHead,
  source_tracked_clean: statusBytes.byteLength === 0,
  source_status_sha256: digest(statusBytes),
  files: files.map(({ bytes: _bytes, ...record }) => record)
};
const provenance = {
  ...provenancePayload,
  manifest_sha256: digest(Buffer.from(JSON.stringify(provenancePayload), "utf8"))
};

const entries = [
  { name: "[Content_Types].xml", bytes: Buffer.from(contentTypesXml(), "utf8") },
  { name: "extension.vsixmanifest", bytes: Buffer.from(manifestXml(packageJson), "utf8") },
  ...files.map((file) => ({ name: file.entry, bytes: file.bytes })),
  {
    name: "extension/release-provenance.json",
    bytes: Buffer.from(`${JSON.stringify(provenance, null, 2)}\n`, "utf8")
  }
].sort((left, right) => left.name.localeCompare(right.name));

await mkdir(releaseRoot, { recursive: true });
const archive = createZip(entries);
await writeFile(outputPath, archive, { flag: "wx" });
console.log(`Created ${outputPath} (${archive.byteLength} bytes, ${entries.length} entries)`);

function parseOutputPath(args) {
  if (args.length !== 2 || args[0] !== "--output" || !args[1]) {
    throw new Error("Usage: node scripts/package-vsix.mjs --output <candidate.vsix>");
  }
  const resolvedOutput = resolve(extensionRoot, args[1]);
  assertWithin(releaseRoot, resolvedOutput, "--output");
  if (extname(resolvedOutput).toLowerCase() !== ".vsix") {
    throw new Error("--output must use the .vsix extension.");
  }
  if (!resolvedOutput.includes(".candidate-")) {
    throw new Error("--output must name a unique candidate artifact.");
  }
  return resolvedOutput;
}

function assertWithin(root, target, label) {
  const suffix = relative(resolve(root), resolve(target));
  if (suffix === "" || suffix === "." || isAbsolute(suffix) || suffix === ".." || suffix.startsWith(`..${sep}`)) {
    throw new Error(`${label} must point to a file inside vscode-extension/.release/.`);
  }
}

function manifestXml(value) {
  const publisher = xmlEscape(value.publisher);
  const id = xmlEscape(value.name.replace(`${value.publisher}-`, ""));
  return `<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="${publisher}-${id}" Version="${xmlEscape(value.version)}" Publisher="${publisher}" />
    <DisplayName>${xmlEscape(value.displayName)}</DisplayName>
    <Description xml:space="preserve">${xmlEscape(value.description)}</Description>
    <Tags>${(value.keywords ?? []).map(xmlEscape).join(",")}</Tags>
    <Categories>${(value.categories ?? []).map(xmlEscape).join(",")}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="${xmlEscape(value.engines?.vscode ?? "*")}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
      <Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true" />
    </Properties>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code" /></Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/readme.md" Addressable="true" />
  </Assets>
</PackageManifest>
`;
}

function contentTypesXml() {
  return `<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="js" ContentType="application/javascript" />
  <Default Extension="md" ContentType="text/markdown" />
  <Default Extension="css" ContentType="text/css" />
  <Default Extension="svg" ContentType="image/svg+xml" />
  <Default Extension="xml" ContentType="application/xml" />
</Types>
`;
}

function createZip(zipEntries) {
  const crcTable = crc32Table();
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const entry of zipEntries) {
    const name = Buffer.from(entry.name, "utf8");
    const raw = Buffer.from(entry.bytes);
    const compressed = deflateRawSync(raw, { level: 9 });
    const method = compressed.byteLength < raw.byteLength ? 8 : 0;
    const payload = method === 8 ? compressed : raw;
    const checksum = crc32(raw, crcTable);
    const local = Buffer.alloc(30 + name.byteLength);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(method, 8);
    local.writeUInt32LE(checksum, 14);
    local.writeUInt32LE(payload.byteLength, 18);
    local.writeUInt32LE(raw.byteLength, 22);
    local.writeUInt16LE(name.byteLength, 26);
    name.copy(local, 30);
    localParts.push(local, payload);

    const central = Buffer.alloc(46 + name.byteLength);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(method, 10);
    central.writeUInt32LE(checksum, 16);
    central.writeUInt32LE(payload.byteLength, 20);
    central.writeUInt32LE(raw.byteLength, 24);
    central.writeUInt16LE(name.byteLength, 28);
    central.writeUInt32LE(offset, 42);
    name.copy(central, 46);
    centralParts.push(central);
    offset += local.byteLength + payload.byteLength;
  }
  const centralDirectory = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(zipEntries.length, 8);
  end.writeUInt16LE(zipEntries.length, 10);
  end.writeUInt32LE(centralDirectory.byteLength, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...localParts, centralDirectory, end]);
}

function crc32Table() {
  return Array.from({ length: 256 }, (_, index) => {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) value = (value & 1) ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    return value >>> 0;
  });
}

function crc32(bytes, table) {
  let value = 0xffffffff;
  for (const byte of bytes) value = table[(value ^ byte) & 0xff] ^ (value >>> 8);
  return (value ^ 0xffffffff) >>> 0;
}

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function xmlEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}
