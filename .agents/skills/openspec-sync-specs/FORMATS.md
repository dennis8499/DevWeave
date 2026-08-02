# OpenSpec Spec Merge Reference

Read this reference before merging a selected delta spec into a main spec.

## Delta operations

A delta may contain these sections:

- `## ADDED Requirements`: add a missing requirement. If it already exists, update it as an implicit modification.
- `## MODIFIED Requirements`: apply only the named description or scenario changes and preserve unmentioned content.
- `## REMOVED Requirements`: remove the entire named requirement block.
- `## RENAMED Requirements`: rename the `FROM` requirement to `TO`.

For an existing main spec, its `## Purpose` is authoritative and remains unchanged. For a new capability, copy the delta's Purpose body verbatim; when absent, write a brief `TBD` placeholder and report it in the summary.

## Delta shape

```markdown
## Purpose

Only needed when introducing a capability.

## ADDED Requirements

### Requirement: New Feature
The system SHALL do something new.

#### Scenario: Basic case
- **WHEN** the user does X
- **THEN** the system does Y

## MODIFIED Requirements

### Requirement: Existing Feature
#### Scenario: Added case
- **WHEN** the user does A
- **THEN** the system does B

## REMOVED Requirements

### Requirement: Deprecated Feature

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
```

## Main spec shape

Main specs contain one `## Requirements` section and no delta operation headers.

```markdown
# <capability> Specification

## Purpose
What this capability does and why it exists.

## Requirements

### Requirement: New Feature
The system SHALL do something new.

#### Scenario: Basic case
- **WHEN** the user does X
- **THEN** the system does Y
```

The delta expresses merge intent, not wholesale replacement. Preserve every requirement, scenario, description, and Purpose passage that the delta does not target.
