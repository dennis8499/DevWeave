import { runTests } from "@vscode/test-electron";
import { resolve } from "node:path";

async function main(): Promise<void> {
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
    await runTests({
      extensionDevelopmentPath: resolve(process.cwd()),
      extensionTestsPath: resolve(process.cwd(), "test", "suite", "index.js"),
      launchArgs: ["--disable-gpu"]
    });
  } finally {
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

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
