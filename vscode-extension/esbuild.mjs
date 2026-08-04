import { build } from "esbuild";
import { createHash } from "node:crypto";
import { cp, mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const production = process.argv.includes("--production");
const root = fileURLToPath(new URL("./", import.meta.url));
const repositoryRoot = join(root, "..");
const outdir = join(root, "dist");
const esbuildPath = (value) => value.replaceAll("\\", "/");
const esbuildRoot = esbuildPath(root);
const extensionEntry = esbuildPath(join(root, "src", "extension.ts"));
const webviewEntry = esbuildPath(join(root, "webview", "main.ts"));

await rm(outdir, { recursive: true, force: true });
await mkdir(outdir, { recursive: true });
await mkdir(join(outdir, "webview"), { recursive: true });
await mkdir(join(outdir, "media"), { recursive: true });

const shared = {
  bundle: true,
  absWorkingDir: esbuildRoot,
  sourcemap: production ? false : "linked",
  minify: production,
  logLevel: "info"
};

await build({
  ...shared,
  entryPoints: [extensionEntry],
  outfile: join(outdir, "extension.js"),
  platform: "node",
  format: "cjs",
  external: ["vscode"]
});

await build({
  ...shared,
  entryPoints: [webviewEntry],
  outfile: join(outdir, "webview", "main.js"),
  platform: "browser",
  format: "iife"
});

await cp(join(root, "webview", "styles.css"), join(outdir, "webview", "styles.css"));
await cp(join(root, "media", "devweave.svg"), join(outdir, "media", "devweave.svg"));

await createBootstrapBundle(repositoryRoot, outdir);

async function createBootstrapBundle(repo, outputRoot) {
  const bootstrapRoot = join(outputRoot, "bootstrap");
  const skillSource = join(repo, ".agents", "skills", "devweave");
  const companionSkills = ["codebase-design", "diagnosing-bugs", "grill-me", "grilling", "tdd"];
  const hooksSource = join(repo, ".codex", "hooks.json");
  const agentsSource = join(root, "assets", "bootstrap", "AGENTS.md");
  const skillsLockSource = join(repo, "skills-lock.json");
  const assetsRoot = join(skillSource, "assets");
  const templatesRoot = join(bootstrapRoot, "templates");

  await mkdir(templatesRoot, { recursive: true });
  await cp(skillSource, join(bootstrapRoot, "skill"), { recursive: true });
  for (const skill of companionSkills) {
    await cp(join(repo, ".agents", "skills", skill), join(bootstrapRoot, "companions", skill), { recursive: true });
  }
  await cp(agentsSource, join(bootstrapRoot, "AGENTS.md"));
  await cp(skillsLockSource, join(bootstrapRoot, "skills-lock.json"));
  await cp(hooksSource, join(bootstrapRoot, "hooks.json"));
  await cp(join(assetsRoot, "baseline-product.md.tmpl"), join(templatesRoot, "baseline-product.md"));
  await cp(join(assetsRoot, "baseline-architecture.md.tmpl"), join(templatesRoot, "baseline-architecture.md"));
  await cp(join(assetsRoot, "baseline-quality.md.tmpl"), join(templatesRoot, "baseline-quality.md"));
  await cp(join(assetsRoot, "wiki", "starter", "index.md.tmpl"), join(templatesRoot, "wiki-index.md"));
  await cp(join(assetsRoot, "wiki", "starter", "overview.md.tmpl"), join(templatesRoot, "wiki-overview.md"));
  await cp(join(assetsRoot, "wiki", "starter", "log.md.tmpl"), join(templatesRoot, "wiki-log.md"));
  await writeFile(join(templatesRoot, "project.json"), `${JSON.stringify(defaultProject(), null, 2)}\n`, "utf8");

  const directories = [
    ".devweave",
    ".devweave/cache",
    ".devweave/cache/sessions",
    ".devweave/work-items",
    ".devweave/baseline",
    ".devweave/baseline/capabilities",
    "wiki",
    "wiki/architecture",
    "wiki/modules",
    "wiki/entities",
    "wiki/patterns",
    "wiki/decisions",
    "wiki/dependencies",
    "wiki/guides",
    "wiki/synthesis"
  ];
  const fileMappings = [
    { source: "AGENTS.md", destination: "AGENTS.md", transform: "copy", existingPolicy: "exact" },
    { source: "skills-lock.json", destination: "skills-lock.json", transform: "copy", existingPolicy: "exact" },
    { source: "hooks.json", destination: ".codex/hooks.json", transform: "copy", existingPolicy: "exact" },
    { source: "templates/project.json", destination: ".devweave/project.json", transform: "copy", existingPolicy: "adopt-compatible", compatibility: "devweave-project-v1" },
    { source: "templates/baseline-product.md", destination: ".devweave/baseline/product.md", transform: "copy", existingPolicy: "adopt-compatible", compatibility: "baseline-product-v1" },
    { source: "templates/baseline-architecture.md", destination: ".devweave/baseline/architecture.md", transform: "copy", existingPolicy: "adopt-compatible", compatibility: "baseline-architecture-v1" },
    { source: "templates/baseline-quality.md", destination: ".devweave/baseline/quality.md", transform: "copy", existingPolicy: "adopt-compatible", compatibility: "baseline-quality-v1" },
    { source: "templates/wiki-index.md", destination: "wiki/index.md", transform: "date", existingPolicy: "adopt-compatible", compatibility: "wiki-index-v1" },
    { source: "templates/wiki-overview.md", destination: "wiki/overview.md", transform: "date", existingPolicy: "adopt-compatible", compatibility: "wiki-overview-v1" },
    { source: "templates/wiki-log.md", destination: "wiki/log.md", transform: "date", existingPolicy: "adopt-compatible", compatibility: "wiki-log-v1" }
  ];
  const skillFiles = await collectFiles(join(bootstrapRoot, "skill"));
  for (const source of skillFiles) {
      fileMappings.push({
        source: `skill/${source}`,
        destination: `.agents/skills/devweave/${source.replaceAll("\\", "/")}`,
        transform: "copy",
        existingPolicy: "exact"
      });
  }
  for (const skill of companionSkills) {
    const companionFiles = await collectFiles(join(bootstrapRoot, "companions", skill));
    for (const source of companionFiles) {
      fileMappings.push({
        source: `companions/${skill}/${source}`,
        destination: `.agents/skills/${skill}/${source.replaceAll("\\", "/")}`,
        transform: "copy",
        existingPolicy: "exact"
      });
    }
  }

  const files = [];
  for (const mapping of fileMappings) {
    const bytes = await readFile(join(bootstrapRoot, mapping.source));
    files.push({
      source: mapping.source.replaceAll("\\", "/"),
      destination: mapping.destination,
      transform: mapping.transform,
      existingPolicy: mapping.existingPolicy ?? "exact",
      ...(mapping.compatibility ? { compatibility: mapping.compatibility } : {}),
      byteLength: bytes.byteLength,
      sha256: createHash("sha256").update(bytes).digest("hex")
    });
  }
  await writeFile(join(bootstrapRoot, "manifest.json"), `${JSON.stringify({
    schemaVersion: 1,
    bundleVersion: "0.2.0",
    directories,
    files
  }, null, 2)}\n`, "utf8");
}

async function collectFiles(directory, prefix = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const relative = prefix ? join(prefix, entry.name) : entry.name;
    if (entry.isDirectory()) {
      files.push(...await collectFiles(join(directory, entry.name), relative));
    } else if (entry.isFile()) {
      files.push(relative);
    }
  }
  return files;
}

function defaultProject() {
  return {
    schema_version: 1,
    managed: true,
    locale: "zh-TW",
    commands: [],
    verification_profiles: { low: [], standard: [], high: [] },
    protected_mutations: ["product-code", "tests", "schema", "dependencies", "build", "ci"],
    evidence: { raw_log_limit_bytes: 5000000, version_summaries: true },
    knowledge: { enabled: true, root: "wiki" }
  };
}
