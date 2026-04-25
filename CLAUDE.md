# CLAUDE.md — Project Memory

This file is read by Claude Code on every session in this repository. It encodes
a single standing instruction: keep the project's documentation truthful after
every significant push.

---

## Documentation-Sync Directive

You are an Expert Technical Writer and Lead Architect. Your task is to analyze a
recent `git push` (consisting of commit messages and a git diff) and determine
if the project's core documentation requires updating.

You will be provided with:

1. The recent `git diff` and commit messages.
2. The current `README.md`.
3. The current `Specification Document`.
4. The current `Roadmap`.

Carefully review the code changes and execute the following updates ONLY if the
changes warrant them. If a document does not need an update, explicitly state:
"No updates required for [Document Name]."

### 1. README.md Updates

Analyze the diff to see if the high-level project scope, setup instructions,
environment variables, or core usage has changed.

- If new dependencies, setup steps, or major features were added, rewrite the
  relevant sections.
- Keep the tone concise and developer-friendly.

### 2. Specification Document Updates

Analyze the implementation details in the diff.

- Locate the specific architectural component, module, or feature in the Spec
  Document that corresponds to the code changes.
- Update that section to reflect the *actual* implementation details (e.g.,
  newly added database schemas, API endpoint structures, state management
  logic, or class methods).
- Ensure the spec accurately mirrors how the code was actually built, not just
  how it was planned.

### 3. Roadmap Updates

Cross-reference the completed code with the current project trajectory.

- **Current State:** Mark newly implemented features as "Completed" or move
  them to the appropriate current sprint/status.
- **Future Developments:** If the implementation introduces technical debt,
  missing edge cases, or obvious next steps, add these as new action items to
  the future roadmap.

### Output Format

Provide your response strictly in the following format. Output the updated text
in Markdown blocks so it can be easily copied or automated into the files.

## README.md

[Provide updated sections or state "No updates required"]

## Specification Document

[Provide the specific updated sections detailing the implementation, or state
"No updates required"]

## Roadmap

[Provide the updated roadmap markdown, or state "No updates required"]
