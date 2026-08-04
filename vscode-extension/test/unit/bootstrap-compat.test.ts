import assert from "node:assert/strict";
import test from "node:test";
import {
  normalizeBootstrapCompatibility,
  validateExistingBootstrapContent
} from "../../src/bootstrap-compat";

const project = JSON.stringify({
  schema_version: 1,
  managed: true,
  locale: "zh-TW",
  commands: [],
  verification_profiles: { low: [], standard: [], high: [] },
  evidence: { raw_log_limit_bytes: 5_000_000, version_summaries: true },
  knowledge: { enabled: true, root: "wiki" }
});

const baseline = (title: string, headings: string[]): string => [
  `# ${title}`,
  "",
  ...headings.flatMap((heading) => [`## ${heading}`, "Evolved repository content.", ""])
].join("\n");

test("semantic bootstrap validator accepts all seven reviewed data contracts", () => {
  const cases: Array<[string, Uint8Array]> = [
    ["devweave-project-v1", new TextEncoder().encode(project)],
    ["baseline-product-v1", new TextEncoder().encode(baseline("Product Baseline", ["Vision", "Accepted Capabilities", "Roadmap"]))],
    ["baseline-architecture-v1", new TextEncoder().encode(baseline("Architecture Baseline", ["System Context", "Boundaries and Interfaces", "Accepted Decisions"]))],
    ["baseline-quality-v1", new TextEncoder().encode(baseline("Quality Baseline", ["Quality Attributes", "Verification Commands", "Operational Constraints"]))],
    ["wiki-index-v1", new TextEncoder().encode("---\ntype: index\n---\n# Evolved index\n")],
    ["wiki-overview-v1", new TextEncoder().encode("---\ntype: overview\n---\n# Evolved overview\n")],
    ["wiki-log-v1", new TextEncoder().encode("---\ntype: log\n---\n# Evolved log\n")]
  ];

  for (const [kind, bytes] of cases) {
    const result = validateExistingBootstrapContent(kind as Parameters<typeof validateExistingBootstrapContent>[0], bytes);
    assert.equal(result.compatible, true, `${kind}: ${result.reason ?? "unknown reason"}`);
  }
});

test("semantic bootstrap validator rejects identity drift and malformed bytes", () => {
  const unmanaged = JSON.stringify({ ...JSON.parse(project), managed: false });
  const invalidBaseline = "# Product Baseline\n## Vision\n";
  const invalidWiki = "---\ntype: guide\n---\n# Wrong type\n";

  assert.match(
    validateExistingBootstrapContent("devweave-project-v1", new TextEncoder().encode(unmanaged)).reason ?? "",
    /managed/i
  );
  assert.equal(
    validateExistingBootstrapContent("baseline-product-v1", new TextEncoder().encode(invalidBaseline)).compatible,
    false
  );
  assert.equal(
    validateExistingBootstrapContent("wiki-index-v1", new TextEncoder().encode(invalidWiki)).compatible,
    false
  );
  assert.equal(
    validateExistingBootstrapContent("devweave-project-v1", new Uint8Array([0xff, 0xfe])).compatible,
    false
  );
});

test("manifest compatibility metadata is explicit and fail-closed", () => {
  assert.deepEqual(normalizeBootstrapCompatibility({}), { existingPolicy: "exact" });
  assert.deepEqual(
    normalizeBootstrapCompatibility({ existingPolicy: "adopt-compatible", compatibility: "wiki-index-v1" }),
    { existingPolicy: "adopt-compatible", compatibility: "wiki-index-v1" }
  );
  const unknownPolicy = normalizeBootstrapCompatibility({ existingPolicy: "unknown" });
  assert.match("error" in unknownPolicy ? unknownPolicy.error : "", /policy/i);
  const exactWithKind = normalizeBootstrapCompatibility({ existingPolicy: "exact", compatibility: "wiki-index-v1" });
  assert.match("error" in exactWithKind ? exactWithKind.error : "", /compatibility/i);
});
