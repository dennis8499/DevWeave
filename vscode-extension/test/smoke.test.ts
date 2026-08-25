import { runTests } from "@vscode/test-electron";
import { access, mkdir, rm } from "node:fs/promises";
import { constants } from "node:fs";
import { createServer } from "node:net";
import { join, resolve } from "node:path";

const ACCEPTED_VSCODE_VERSION = "1.131.0";

async function cachedExecutable(): Promise<string> {
  const platform = process.platform === "win32" ? "win32-x64-archive" : process.platform;
  const executable = process.platform === "win32" ? "Code.exe" : "code";
  const path = join(process.cwd(), ".vscode-test", `vscode-${platform}-${ACCEPTED_VSCODE_VERSION}`, executable);
  try {
    await access(path, constants.X_OK);
    return path;
  } catch {
    throw new Error(`Accepted VS Code ${ACCEPTED_VSCODE_VERSION} runtime is not cached at ${path}; smoke is cache-only and will not download or fallback.`);
  }
}

async function main(): Promise<void> {
  const debugPort = await availablePort();
  const screenshot = resolve(process.cwd(), ".test-results", "control-center.png");
  await mkdir(resolve(process.cwd(), ".test-results"), { recursive: true });
  await rm(screenshot, { force: true });
  process.env.DEVWEAVE_SMOKE_DEBUG_PORT = String(debugPort);
  process.env.DEVWEAVE_SMOKE_SCREENSHOT = screenshot;
  const inheritedKeys = [
    "ELECTRON_RUN_AS_NODE",
    "VSCODE_IPC_HOOK",
    "VSCODE_ESM_ENTRYPOINT",
    "VSCODE_CRASH_REPORTER_PROCESS_TYPE",
    "VSCODE_HANDLES_UNCAUGHT_ERRORS",
    "VSCODE_CWD",
    "VSCODE_PID",
    "VSCODE_CODE_CACHE_PATH",
    "VSCODE_NLS_CONFIG"
  ];
  const inheritedValues = new Map<string, string | undefined>();
  for (const key of inheritedKeys) {
    inheritedValues.set(key, process.env[key]);
    delete process.env[key];
  }

  try {
    const vscodeExecutablePath = await cachedExecutable();
    await runTests({
      extensionDevelopmentPath: resolve(process.cwd()),
      extensionTestsPath: resolve(process.cwd(), "test", "suite", "index.js"),
      vscodeExecutablePath,
      reuseMachineInstall: false,
      launchArgs: [resolve(process.cwd(), ".."), "--disable-gpu", `--remote-debugging-port=${debugPort}`]
    });
    await access(screenshot, constants.R_OK);
    process.stdout.write(`${JSON.stringify({ screenshot, debugTransport: "local-cdp" })}\n`);
  } finally {
    delete process.env.DEVWEAVE_SMOKE_DEBUG_PORT;
    delete process.env.DEVWEAVE_SMOKE_SCREENSHOT;
    for (const key of inheritedKeys) {
      const value = inheritedValues.get(key);
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
}

async function availablePort(): Promise<number> {
  return new Promise((resolvePort, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        reject(new Error("Could not allocate a local CDP port."));
        return;
      }
      server.close((error) => error ? reject(error) : resolvePort(address.port));
    });
  });
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
