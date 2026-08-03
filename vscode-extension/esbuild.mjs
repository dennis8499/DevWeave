import { build } from "esbuild";
import { cp, mkdir, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const production = process.argv.includes("--production");
const root = fileURLToPath(new URL("./", import.meta.url));
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
