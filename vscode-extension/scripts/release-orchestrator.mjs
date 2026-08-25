import { randomUUID } from "node:crypto";
import { execFile } from "node:child_process";
import { dirname, extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { mkdir, readFile, rename, rm, stat } from "node:fs/promises";

const execFileAsync = promisify(execFile);
const scriptsRoot = fileURLToPath(new URL("./", import.meta.url));
const extensionRoot = fileURLToPath(new URL("../", import.meta.url));

/**
 * Run the candidate -> verify -> promote release transaction.
 *
 * The current and retained artifacts are deliberately outside the cleanup
 * set. Promotion is a same-directory rename so a failed verification cannot
 * modify the current artifact.
 */
export async function runReleaseTransaction({
  extensionRoot: configuredRoot,
  currentArtifact,
  candidatePath = createCandidatePath(currentArtifact),
  buildCandidate,
  verifyCandidate,
  promote = promoteCandidate,
  cleanup = cleanupCandidate
}) {
  if (typeof currentArtifact !== "string" || !currentArtifact) {
    throw new TypeError("currentArtifact is required.");
  }
  if (typeof candidatePath !== "string" || !candidatePath) {
    throw new TypeError("candidatePath is required.");
  }
  if (typeof buildCandidate !== "function" || typeof verifyCandidate !== "function") {
    throw new TypeError("buildCandidate and verifyCandidate are required functions.");
  }

  const root = resolve(configuredRoot || dirname(currentArtifact));
  assertWithinRoot(root, currentArtifact, "current artifact");
  assertWithinRoot(root, candidatePath, "candidate artifact");
  if (resolve(currentArtifact) === resolve(candidatePath)) {
    throw new Error("Candidate and current artifacts must be different paths.");
  }
  if (dirname(resolve(currentArtifact)) !== dirname(resolve(candidatePath))) {
    throw new Error("Candidate and current artifacts must share a directory.");
  }

  let failure = null;
  let promoted = false;
  try {
    await buildCandidate(candidatePath);
    await verifyCandidate(candidatePath);
    await promote(candidatePath, currentArtifact);
    promoted = true;
  } catch (error) {
    failure = error instanceof Error ? error : new Error(String(error));
  }

  try {
    await cleanup(candidatePath);
  } catch (cleanupError) {
    const normalized = cleanupError instanceof Error ? cleanupError : new Error(String(cleanupError));
    if (failure) {
      failure.cleanupError = normalized;
    } else {
      failure = normalized;
    }
  }

  if (failure) {
    if (failure.cleanupError) {
      failure.message = `${failure.message} (candidate cleanup failed: ${failure.cleanupError.message})`;
    }
    throw failure;
  }

  return { currentArtifact, promoted };
}

export function createCandidatePath(currentArtifact) {
  const currentExtension = extname(currentArtifact) || ".vsix";
  const currentName = currentArtifact.slice(0, -currentExtension.length);
  return `${currentName}.candidate-${process.pid}-${randomUUID()}${currentExtension}`;
}

export async function promoteCandidate(candidatePath, currentArtifact) {
  await rename(candidatePath, currentArtifact);
}

export async function cleanupCandidate(candidatePath) {
  await rm(candidatePath, { force: true });
}

async function runProductionRelease() {
  const packageJson = JSON.parse(await readFile(join(extensionRoot, "package.json"), "utf8"));
  const releaseRoot = join(extensionRoot, ".release");
  await mkdir(releaseRoot, { recursive: true });
  const currentArtifact = join(releaseRoot, `devweave-control-center-${packageJson.version}.vsix`);
  const candidatePath = createCandidatePath(currentArtifact);
  const nodeExecutable = process.execPath;

  await runReleaseTransaction({
    extensionRoot,
    currentArtifact,
    candidatePath,
    buildCandidate: (outputPath) => runNodeScript(nodeExecutable, "package-vsix.mjs", ["--output", outputPath]),
    verifyCandidate: (artifactPath) => runNodeScript(nodeExecutable, "verify-package.mjs", ["--artifact", artifactPath])
  });

  const info = await stat(currentArtifact);
  console.log(`Released ${currentArtifact} (${info.size} bytes)`);
}

async function runNodeScript(nodeExecutable, scriptName, args) {
  const result = await execFileAsync(nodeExecutable, [join(scriptsRoot, scriptName), ...args], { cwd: extensionRoot });
  if (result.stdout) process.stdout.write(result.stdout.endsWith("\n") ? result.stdout : `${result.stdout}\n`);
  if (result.stderr) process.stderr.write(result.stderr.endsWith("\n") ? result.stderr : `${result.stderr}\n`);
  return result;
}

function assertWithinRoot(root, target, label) {
  const resolvedRoot = resolve(root);
  const resolvedTarget = resolve(target);
  const suffix = relative(resolvedRoot, resolvedTarget);
  if (suffix === "" || suffix === "." || isAbsolute(suffix) || suffix === ".." || suffix.startsWith(`..${sep}`)) {
    throw new Error(`${label} must be inside the extension root.`);
  }
}

const invokedScript = process.argv[1] ? resolve(process.argv[1]) : "";
if (invokedScript === resolve(fileURLToPath(import.meta.url))) {
  runProductionRelease().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
