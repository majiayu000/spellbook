# Code and Artifact Archaeology

Use this route for repositories, modules, APIs, incidents, and local compiled artifacts.

## Establish the Exact Target

1. Resolve the repository root, worktree, branch or revision, and nearest instruction file.
2. Record dirty state before changing anything. X-Ray investigation is read-only unless the user separately asks for implementation.
3. Identify the user-visible entry point or externally observable symptom.
4. Search for exact route names, symbols, configuration keys, error strings, and persisted fields.

## Trace the Hot Path

Follow reachable code in this order:

1. Input and parsing.
2. Validation and authorization boundaries.
3. Routing or dispatch decision.
4. State reads and writes.
5. External calls and side-effect boundary.
6. Output transformation and presentation.
7. Error propagation, recovery, and terminal failure.

Inspect configuration, schemas, registries, persistence, startup wiring, and tests that can change this path. A matching filename or symbol is a lead, not proof that code is reachable.

For an application feature, continue across process and network boundaries when they are part of the behavior:

```text
user action -> client state -> request construction -> transport -> server handler -> persistence or job -> response or later result
```

Check platform-specific implementations when mobile, desktop, extension, or background execution can differ. Prefer source-defined endpoints and schemas first. Use runtime traffic capture only when it is authorized, does not expose unrelated secrets, and answers something the source cannot establish cheaply.

Use Git history, issues, and pull requests only when the question includes “why,” a tradeoff, or behavioral change. Current code remains the source of truth for current behavior.

## Code Evidence Notes

For central or disputed steps, retain enough context to relocate the evidence:

```text
path: exact/relative/path.ext
symbol: function, type, route, or field
revision: branch or commit when relevant
observation: what the code actually does
confidence: observed | corroborated | inferred | unknown
```

This note shape is optional. Render short exact snippets only when syntax itself teaches the mechanism. Prefer a diagram plus clickable anchors over a wall of code.

## Incident Trace

Order evidence by the actual event sequence:

```text
request -> validation -> routing -> state transition -> side effect -> response
```

Place logs and persisted records beside the step they prove. Separate the initiating defect, propagation mechanism, user-visible symptom, and recovery boundary.

## Compiled Artifact Route

When the user asks how a clearly identified local app, CLI, or compiled artifact works, safe read-only static inspection is part of the default investigation. Do not stall solely because the target lacks source code.

1. Resolve the exact installed path and version, then record its cryptographic hash, architecture, file format, signature, and entitlements where available.
2. Inspect load commands, linked libraries, imports, recoverable symbols, strings, embedded assets, manifests, and packaging metadata with tools already present on the machine.
3. Treat the container format as an entry point, not the answer. When an official or independently verifiable format description makes safe extraction possible, recover the embedded module table or implementation payload and trace at least one reachable hot path from its real entry point. Do not headline file size, packer name, or section layout when recoverable code can answer the teaching question.
4. Group clues by the teaching question. A long string dump is not an explanation; retain only evidence that changes the causal model.
5. Corroborate important clues against public source, official documentation, runtime-owned state, or multiple independent static observations before presenting them as behavior.
6. Mark unreachable code, dormant feature names, endpoint literals, and decompiled fragments as clues or inference unless reachability is established.

Ask separately before installing tooling, executing an unknown artifact, attaching a debugger, intercepting or decrypting traffic, patching the binary, bypassing protection, or accessing credentials. When authorized specialist evidence is necessary, read [reverse-core.md](reverse-core.md), load only the matching adapter, and return its findings to this causal trace rather than expanding X-Ray into a general security suite.

Refuse credential theft, access-control bypass, persistence, stealth, exploitation of third-party targets, or other harmful goals. A legitimate explanatory goal does not expand authorization.
