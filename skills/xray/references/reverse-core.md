# Reverse Core

Use this reference only when ordinary source archaeology and safe package inspection cannot establish the requested mechanism. It adds a small specialist reverse route to X-Ray without importing a general security suite.

## Boundary

- Keep X-Ray as the only user-facing workflow. Reverse Core returns evidence; it does not own the final explanation.
- Load one matching adapter. Do not read or reproduce a full reverse-engineering pack when one tool or format can answer the question.
- Use tools already installed and discover their real paths and versions before calling them. Ask before installing or registering a tool or MCP server.
- Default to a user-owned local artifact, an explicitly authorized sample, or supplied offline evidence. When ownership or authorization is unclear, stop before specialist action and ask.
- Safe static inspection may proceed directly on an identified authorized artifact. Ask before execution, debugging, emulation, hook injection, traffic interception or decryption, patching, repackaging, protection bypass, credentials, or interaction with a third-party target.
- Do not extend an explanatory task into exploit development, persistence, stealth, credential recovery, EDR bypass, lateral movement, or vulnerability weaponization.

## Minimal Route

| Evidence gap | Load | First useful observation |
|---|---|---|
| PE, ELF, Mach-O, native library, or compiled CLI | Native adapter | imports, symbols, strings, entry points, xrefs, one reachable function path |
| Android APK or embedded native library | APK adapter | manifest and component entry, DEX call path, JNI boundary, relevant resources |
| Minified or bundled JavaScript, Electron, or browser signing logic | JavaScript adapter | source map or module boundary, AST transformation, call site, request construction |
| Runtime-only branch, unpacked code, or computed value | Dynamic adapter | one authorized breakpoint, hook, trace, or memory observation tied to the hypothesis |
| Unknown wire format or request field | Network adapter | source-defined schema first, then an authorized capture or supplied PCAP if still needed |

If safe static evidence answers the teaching question, stop there. The existence of a deeper tool is not a reason to use it.

## Shared Phases

### 1. Triage

Record the exact path, SHA-256, size, format, architecture, version, signature, and relevant packaging identity. Preserve the original and work read-only unless the user separately authorizes mutation.

Inspect the cheapest high-signal surfaces already available:

- headers, sections or load commands;
- imports, exports, recoverable symbols, and strings;
- manifests, entitlements, permissions, and bundled resources;
- archives, source maps, module tables, and embedded configuration.

Write one hypothesis about the requested mechanism and the observation that would disprove it. Do not turn triage into the final answer.

### 2. Static path

Choose the smallest adapter that can follow one real path from entry or user action to the behavior being explained. Preserve addresses, symbols, call sites, cross-references, constants, and data-flow steps that let another analyst relocate the evidence.

Decompiled output is an interpretation. Corroborate behavior-changing claims with disassembly, xrefs, callers, runtime-owned configuration, or an authorized observation. A string or imported API proves presence, not reachability.

### 3. Dynamic decision

Use dynamic work only when it resolves a named gap that static evidence cannot answer cheaply. Before crossing the boundary, state:

- the unresolved question;
- the exact action and tool;
- expected side effects and target environment;
- why a supplied trace, existing log, or static alternative is insufficient.

After approval, take the smallest observation needed. Do not broaden from one function or request into general monitoring.

### 4. Evidence handoff

Return concise notes to the X-Ray causal model. Use this shape when helpful, without requiring a permanent ledger:

```text
artifact: exact path, version, SHA-256
tool: name and version
anchor: address, symbol, module, request field, or packet range
observation: what was directly seen
reachability: observed | corroborated | inferred | unknown
boundary: static only, or the authorized dynamic action performed
meaning: how this changes the teaching question
```

## Adapters

### Native binary

1. Use platform metadata tools for identity and linkage before opening a decompiler.
2. Prefer an existing IDA integration when exact decompilation, xrefs, callers, or data flow are needed and a licensed environment is already available.
3. Prefer an existing Ghidra integration for open or headless analysis when IDA is unavailable.
4. Prefer radare2 or equivalent CLI tools for fast reconnaissance, strings, imports, sections, and a small disassembly path.
5. Do not run all three for reassurance. Cross-check with a second tool only when a pivotal interpretation is ambiguous.

### APK

1. Inspect the archive, manifest, permissions, components, resources, and signing information.
2. Use an available DEX decompiler to find the user-visible entry, request builder, serializer, crypto call, or JNI dispatch relevant to the question.
3. Route an embedded `.so` through the native adapter and keep the Java/Kotlin-to-JNI handoff visible.
4. Treat Frida, emulator execution, repackaging, certificate changes, and pinning bypass as separate authorized actions.

### JavaScript and packaged desktop apps

1. Recover source maps, module tables, readable bundles, preload scripts, manifests, and configuration before beautifying isolated fragments.
2. Follow the value from its input through transformations to the request, storage write, IPC call, or native boundary.
3. Use AST or runtime instrumentation only when ordinary source search cannot preserve the transformation accurately.
4. For Electron, Bun, or similar packages, treat the container as an entry point and trace into the recoverable implementation payload.

### Dynamic observation

1. Tie every breakpoint, debugger step, Frida hook, trace, or emulation run to one unresolved hypothesis.
2. Use an isolated copy, test device, sandbox, or fixture and record the executed artifact hash.
3. Capture only the relevant arguments, return value, branch, or memory range. Avoid unrelated user data and credentials.
4. If execution integrity is uncertain or the sample may be malicious, stop and require a suitable sandbox rather than weakening the boundary.

### Network and protocol

1. Start with source-defined endpoints, schemas, serializers, protocol descriptors, configuration, and supplied logs.
2. For supplied PCAP or offline traces, identify the flow, framing, fields, ordering, and state transitions without assuming the protocol from port numbers alone.
3. Ask before live capture, request replay, proxy configuration, TLS decryption, certificate installation, or authenticated traffic access.
4. Keep the capture scoped to the authorized target and named request. Redact unrelated tokens or personal data from the explainer.

## Done When

- The artifact and toolchain are identified precisely enough to reproduce the observation.
- At least one reachable path answers the teaching question, or the missing observation is named explicitly.
- Static clues, decompiler interpretation, and dynamic observations are not presented as the same evidence class.
- The work did not silently install tools, execute code, intercept traffic, or expand into offensive operations.
- X-Ray can turn the returned evidence into one simple causal picture and a deeper technical layer without exposing a tool dump.

## Upstream Design Reference

The compact phase and adapter design was informed by the MIT-licensed [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) project, inspected at commit `66cd74c997344d5ed5509fb2561dba0e44be176e`. X-Ray does not vendor its router, installers, offensive modules, case machinery, or specialist Skill tree.
