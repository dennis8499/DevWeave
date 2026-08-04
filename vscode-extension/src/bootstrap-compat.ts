export type BootstrapExistingPolicy = "exact" | "adopt-compatible";

export type BootstrapCompatibilityKind =
  | "devweave-project-v1"
  | "baseline-product-v1"
  | "baseline-architecture-v1"
  | "baseline-quality-v1"
  | "wiki-index-v1"
  | "wiki-overview-v1"
  | "wiki-log-v1";

export interface BootstrapCompatibilityMetadata {
  existingPolicy: BootstrapExistingPolicy;
  compatibility?: BootstrapCompatibilityKind;
}

export interface ExistingContentValidation {
  compatible: boolean;
  reason?: string;
}

const COMPATIBILITY_KINDS = new Set<BootstrapCompatibilityKind>([
  "devweave-project-v1",
  "baseline-product-v1",
  "baseline-architecture-v1",
  "baseline-quality-v1",
  "wiki-index-v1",
  "wiki-overview-v1",
  "wiki-log-v1"
]);

const BASELINE_CONTRACTS: Record<
  "baseline-product-v1" | "baseline-architecture-v1" | "baseline-quality-v1",
  { title: string; headings: string[] }
> = {
  "baseline-product-v1": {
    title: "Product Baseline",
    headings: ["Vision", "Accepted Capabilities", "Roadmap"]
  },
  "baseline-architecture-v1": {
    title: "Architecture Baseline",
    headings: ["System Context", "Boundaries and Interfaces", "Accepted Decisions"]
  },
  "baseline-quality-v1": {
    title: "Quality Baseline",
    headings: ["Quality Attributes", "Verification Commands", "Operational Constraints"]
  }
};

const WIKI_TYPES: Record<"wiki-index-v1" | "wiki-overview-v1" | "wiki-log-v1", string> = {
  "wiki-index-v1": "index",
  "wiki-overview-v1": "overview",
  "wiki-log-v1": "log"
};

export function normalizeBootstrapCompatibility(value: {
  existingPolicy?: unknown;
  compatibility?: unknown;
}): BootstrapCompatibilityMetadata | { error: string } {
  const policy = value.existingPolicy;
  const compatibility = value.compatibility;
  if (policy === undefined) {
    return compatibility === undefined
      ? { existingPolicy: "exact" }
      : { error: "Compatibility kind requires existingPolicy adopt-compatible." };
  }
  if (policy !== "exact" && policy !== "adopt-compatible") {
    return { error: `Unknown existingPolicy: ${String(policy)}.` };
  }
  if (policy === "exact") {
    return compatibility === undefined
      ? { existingPolicy: "exact" }
      : { error: "Exact existingPolicy cannot declare a compatibility kind." };
  }
  if (typeof compatibility !== "string" || !COMPATIBILITY_KINDS.has(compatibility as BootstrapCompatibilityKind)) {
    return { error: `Unknown or missing compatibility kind: ${String(compatibility)}.` };
  }
  return {
    existingPolicy: "adopt-compatible",
    compatibility: compatibility as BootstrapCompatibilityKind
  };
}

export function validateExistingBootstrapContent(
  kind: BootstrapCompatibilityKind,
  bytes: Uint8Array
): ExistingContentValidation {
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return incompatible("Content is not valid UTF-8.");
  }

  if (kind === "devweave-project-v1") return validateProject(text);
  if (kind in BASELINE_CONTRACTS) {
    return validateBaseline(kind as keyof typeof BASELINE_CONTRACTS, text);
  }
  return validateWiki(kind as keyof typeof WIKI_TYPES, text);
}

function validateProject(text: string): ExistingContentValidation {
  let project: unknown;
  try {
    project = JSON.parse(text) as unknown;
  } catch {
    return incompatible("Project JSON is malformed.");
  }
  if (!isRecord(project)) return incompatible("Project JSON must be an object.");
  if (project.schema_version !== 1) return incompatible("schema_version must be 1.");
  if (project.managed !== true) return incompatible("managed must be true.");
  if (typeof project.locale !== "string" || !project.locale.trim()) {
    return incompatible("locale must be a non-empty string.");
  }
  if (!Array.isArray(project.commands)) return incompatible("commands must be an array.");
  for (const command of project.commands) {
    if (!isRecord(command)) return incompatible("commands entries must be objects.");
    if (typeof command.id !== "string" || !command.id) return incompatible("command id is invalid.");
    if (!Array.isArray(command.argv) || command.argv.length === 0 || !command.argv.every(isNonEmptyString)) {
      return incompatible("command argv must be a non-empty string array.");
    }
    if (typeof command.cwd !== "string" || !command.cwd) return incompatible("command cwd is invalid.");
    if (typeof command.timeout_seconds !== "number" || !Number.isInteger(command.timeout_seconds) || command.timeout_seconds <= 0) {
      return incompatible("command timeout_seconds must be a positive integer.");
    }
    if (!Array.isArray(command.required_for) || !command.required_for.every(isRiskLevel)) {
      return incompatible("command required_for contains invalid risk levels.");
    }
  }
  const profiles = project.verification_profiles;
  if (!isRecord(profiles)) return incompatible("verification_profiles must be an object.");
  for (const level of ["low", "standard", "high"]) {
    if (!Array.isArray(profiles[level]) || !profiles[level].every(isNonEmptyString)) {
      return incompatible(`verification_profiles.${level} must be a string array.`);
    }
  }
  const evidence = project.evidence;
  if (!isRecord(evidence)
    || typeof evidence.raw_log_limit_bytes !== "number"
    || !Number.isInteger(evidence.raw_log_limit_bytes)
    || evidence.raw_log_limit_bytes <= 0) {
    return incompatible("evidence.raw_log_limit_bytes must be a positive integer.");
  }
  const knowledge = project.knowledge;
  if (!isRecord(knowledge) || knowledge.enabled !== true || knowledge.root !== "wiki") {
    return incompatible("knowledge must enable the wiki root.");
  }
  return compatible();
}

function validateBaseline(
  kind: keyof typeof BASELINE_CONTRACTS,
  text: string
): ExistingContentValidation {
  const contract = BASELINE_CONTRACTS[kind];
  const lines = new Set(text.split(/\r?\n/).map((line) => line.trim()));
  if (!lines.has(`# ${contract.title}`)) return incompatible(`Missing heading: # ${contract.title}.`);
  const missing = contract.headings.find((heading) => !lines.has(`## ${heading}`));
  return missing ? incompatible(`Missing heading: ## ${missing}.`) : compatible();
}

function validateWiki(
  kind: keyof typeof WIKI_TYPES,
  text: string
): ExistingContentValidation {
  const match = text.match(/^---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/);
  if (!match) return incompatible("Wiki starter is missing YAML frontmatter.");
  const typeLines = match[1].split(/\r?\n/).filter((line) => /^type\s*:/.test(line));
  if (typeLines.length !== 1) return incompatible("Wiki starter frontmatter type is missing or duplicated.");
  const type = typeLines[0].slice(typeLines[0].indexOf(":") + 1).trim().replace(/^['"]|['"]$/g, "");
  return type === WIKI_TYPES[kind]
    ? compatible()
    : incompatible(`Wiki starter requires type ${WIKI_TYPES[kind]}.`);
}

function compatible(): ExistingContentValidation {
  return { compatible: true };
}

function incompatible(reason: string): ExistingContentValidation {
  return { compatible: false, reason };
}

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isRiskLevel(value: unknown): value is "low" | "standard" | "high" {
  return value === "low" || value === "standard" || value === "high";
}
