# Cross-App Flows

End-to-end data flows that span multiple Django apps. Each flow doc traces the full path of an operation across apps with sequence diagrams, step-by-step breakdowns, failure modes, and references back to the feature specs of the apps involved.

**Naming:** `<verb>-to-<noun>.md` or `<resource>-<action>.md` — e.g. `solicitud-create-to-pdf.md`, `transition-with-notification.md`.

**Structure (template):**

```markdown
# <Flow Name>

## Trigger
What initiates this flow (user action, scheduled job, signal).

## Path
1. App A: receives the request, validates, calls Service A.
2. Service A: performs work, calls Service B (across apps via interface).
3. Service B: ...

## Sequence Diagram
[mermaid or ASCII diagram]

## Failure Modes
- What if step N fails? Where does the user end up?
- Idempotency / retry behavior.

## References
- → `apps/A/<feature>` — A's role in this flow
- → `apps/B/<feature>` — B's role
- → `_shared/...` — any shared infra used
```

Create a flow doc when an initiative introduces a new cross-app path or modifies an existing one. Update it when the path changes.
