# Explore Entry Patterns

Consult these patterns only when the right conversational move is unclear. Adapt them to the user's actual codebase and question; they are examples, not a script.

## Vague idea

Map the idea's meaningful spectrum, name the dimensions that drive complexity, and ask which point matches the user's intent.

```text
Awareness -------- Coordination -------- Shared state
presence            cursors              conflict handling
```

## Specific problem

Inspect the relevant code, sketch the current flow, identify the few concrete tangles, and ask which one is causing the immediate pain.

```text
entry points -> shared mechanism -> downstream policy
```

## Mid-implementation discovery

Read the selected change's artifacts and current task, trace the newly discovered complexity, compare viable responses, then offer to capture the decision in the appropriate artifact.

## Option comparison

Ground the comparison in project constraints before recommending. A small table works when the options repeat across several exact criteria; end with the assumption that could reverse the recommendation.
