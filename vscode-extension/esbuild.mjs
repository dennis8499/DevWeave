import { build } from "esbuild";
import { copyFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const production = process.argv.includes("--production");
const extensionRoot = fileURLToPath(new URL("./", import.meta.url));
const outputRoot = join(extensionRoot, "dist");

await mkdir(join(outputRoot, "webview"), { recursive: true });

const shared = {
  absWorkingDir: extensionRoot,
  bundle: true,
  logLevel: "info",
  minify: production,
  sourcemap: production ? false : "linked"
};

await build({
  ...shared,
  entryPoints: ["./src/extension.ts"],
  external: ["vscode"],
  format: "cjs",
  outfile: join(outputRoot, "extension.js"),
  platform: "node"
});

await build({
  ...shared,
  entryPoints: ["./webview/main.ts"],
  format: "iife",
  outfile: join(outputRoot, "webview", "main.js"),
  platform: "browser"
});

await copyFile(
  join(extensionRoot, "webview", "styles.css"),
  join(outputRoot, "webview", "styles.css")
);
