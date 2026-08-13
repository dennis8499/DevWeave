import { readFile, readdir, writeFile } from "node:fs/promises";
import { deflateRawSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { extname, isAbsolute, join, relative, resolve, sep } from "node:path";

const extensionRoot = fileURLToPath(new URL("../", import.meta.url));
const packageJson = JSON.parse(await readFile(join(extensionRoot, "package.json"), "utf8"));
const version = packageJson.version;
const outputPath = parseOutputPath(process.argv.slice(2));
const crcTable = Array.from({ length: 256 }, (_, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) value = (value & 1) ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  return value >>> 0;
});

const files = await collectFiles(extensionRoot);
const entries = [
  { name: "extension.vsixmanifest", bytes: Buffer.from(manifestXml(packageJson), "utf8") },
  { name: "[Content_Types].xml", bytes: Buffer.from(contentTypesXml(), "utf8") },
  ...files.map(({ name, bytes }) => ({ name: `extension/${name}`, bytes }))
];

const archive = createZip(entries);
await writeFile(outputPath, archive, { flag: "wx" });
console.log(`Created ${outputPath} (${archive.byteLength} bytes, ${entries.length} entries)`);

function parseOutputPath(args) {
  if (args.length !== 2 || args[0] !== "--output" || !args[1]) {
    throw new Error("Usage: node scripts/package-vsix.mjs --output <candidate.vsix>");
  }

  const resolvedOutput = resolve(extensionRoot, args[1]);
  const suffix = relative(extensionRoot, resolvedOutput);
  if (suffix === "" || suffix === "." || isAbsolute(suffix) || suffix === ".." || suffix.startsWith(`..${sep}`)) {
    throw new Error("--output must point to a file inside the extension root.");
  }
  if (extname(resolvedOutput).toLowerCase() !== ".vsix") {
    throw new Error("--output must use the .vsix extension.");
  }
  if (!resolvedOutput.includes(".candidate-")) {
    throw new Error("--output must name a unique candidate artifact.");
  }
  const currentArtifact = resolve(extensionRoot, `devweave-control-center-${version}.vsix`);
  if (resolvedOutput === currentArtifact) {
    throw new Error("--output cannot overwrite the current VSIX artifact.");
  }
  return resolvedOutput;
}

async function collectFiles(directory) {
  const entries = [];
  const excludedFiles = new Set(["scripts/release-orchestrator.mjs", "test/unit/release-transaction.test.ts"]);
  for (const entry of (await readdir(directory, { withFileTypes: true })).sort((left, right) => left.name.localeCompare(right.name))) {
    if (["node_modules", ".vscode-test", ".git"].includes(entry.name)) continue;
    const absolute = join(directory, entry.name);
    if (entry.isDirectory()) {
      entries.push(...await collectFiles(absolute));
      continue;
    }
    if (!entry.isFile() || entry.name.endsWith(".vsix")) continue;
    const name = relative(extensionRoot, absolute).replaceAll("\\", "/");
    if (excludedFiles.has(name)) continue;
    if (name === "README.md") {
      entries.push({ name: "readme.md", bytes: await readFile(absolute) });
    } else {
      entries.push({ name, bytes: await readFile(absolute) });
    }
  }
  return entries.sort((left, right) => left.name.localeCompare(right.name));
}

function manifestXml(packageJson) {
  const publisher = xmlEscape(packageJson.publisher);
  const id = xmlEscape(packageJson.name.replace(`${packageJson.publisher}-`, ""));
  return `<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="${publisher}-${id}" Version="${xmlEscape(packageJson.version)}" Publisher="${publisher}" />
    <DisplayName>${xmlEscape(packageJson.displayName)}</DisplayName>
    <Description xml:space="preserve">${xmlEscape(packageJson.description)}</Description>
    <Tags>${(packageJson.keywords ?? []).map(xmlEscape).join(",")}</Tags>
    <Categories>${(packageJson.categories ?? []).map(xmlEscape).join(",")}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="${xmlEscape(packageJson.engines?.vscode ?? "*")}" />
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
  <Default Extension="ts" ContentType="text/plain" />
  <Default Extension="md" ContentType="text/markdown" />
  <Default Extension="css" ContentType="text/css" />
  <Default Extension="svg" ContentType="image/svg+xml" />
  <Default Extension="xml" ContentType="application/xml" />
  <Default Extension="map" ContentType="application/json" />
  <Default Extension="yaml" ContentType="text/plain" />
  <Default Extension="txt" ContentType="text/plain" />
  <Default Extension="tmpl" ContentType="text/plain" />
</Types>
`;
}

function createZip(entries) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const entry of entries) {
    const name = Buffer.from(entry.name, "utf8");
    const raw = Buffer.from(entry.bytes);
    const compressed = deflateRawSync(raw, { level: 9 });
    const method = compressed.byteLength < raw.byteLength ? 8 : 0;
    const payload = method === 8 ? compressed : raw;
    const checksum = crc32(raw);
    const local = Buffer.alloc(30 + name.byteLength);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(method, 8);
    local.writeUInt16LE(0, 10);
    local.writeUInt16LE(0, 12);
    local.writeUInt32LE(checksum, 14);
    local.writeUInt32LE(payload.byteLength, 18);
    local.writeUInt32LE(raw.byteLength, 22);
    local.writeUInt16LE(name.byteLength, 26);
    local.writeUInt16LE(0, 28);
    name.copy(local, 30);
    localParts.push(local, payload);

    const central = Buffer.alloc(46 + name.byteLength);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(method, 10);
    central.writeUInt16LE(0, 12);
    central.writeUInt16LE(0, 14);
    central.writeUInt32LE(checksum, 16);
    central.writeUInt32LE(payload.byteLength, 20);
    central.writeUInt32LE(raw.byteLength, 24);
    central.writeUInt16LE(name.byteLength, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(0, 38);
    central.writeUInt32LE(offset, 42);
    name.copy(central, 46);
    centralParts.push(central);
    offset += local.byteLength + payload.byteLength;
  }
  const centralDirectory = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralDirectory.byteLength, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);
  return Buffer.concat([...localParts, centralDirectory, end]);
}

function crc32(bytes) {
  let value = 0xffffffff;
  for (const byte of bytes) value = crcTable[(value ^ byte) & 0xff] ^ (value >>> 8);
  return (value ^ 0xffffffff) >>> 0;
}

function xmlEscape(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}
