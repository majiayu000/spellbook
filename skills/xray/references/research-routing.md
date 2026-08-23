# Research Routing

Choose enough investigation to establish the mechanism, not the maximum amount of research available.

## Research Modes

| Mode | Use when | Typical evidence |
|---|---|---|
| Supplied | The user supplied a trustworthy document, trace, or dataset and asks for explanation | Supplied material plus spot checks of pivotal claims |
| Grounded | A stable topic is reasonably known but needs exact explanation | A primary source and current local evidence where applicable |
| Deep | The topic is current, niche, disputed, unfamiliar, or failure-sensitive | Primary sources plus current implementation or runtime evidence sufficient to resolve the mechanism |

## Target Decision Table

| Target | Start here | Add only when needed |
|---|---|---|
| Concept, protocol, or algorithm | Original paper, standard, official documentation | High-quality secondary explanation for pedagogy |
| Repository or module | Exact worktree, nearest instructions, entry point, tests, schema/config | Git history, issue or PR for rationale |
| Application behavior | User-visible action, exact app version, reachable client code | Network contract or observed request, server path, persistence, jobs, platform-specific behavior |
| Incident | Persisted state, logs, metrics, request IDs, deployed revision | Source trace and documentation |
| Supplied document | Document claims and cited sources | External verification of material/current claims |
| Clearly identified local app, CLI, or compiled artifact | Identify the exact artifact, version, and hash; perform safe read-only static inspection | Ask only when deeper work requires execution, debugging, interception, patching, new tooling, credentials, or protection bypass |

## Scope and Cost Controls

- Do not call paid services, external AI systems, or multiple agents unless the user explicitly asks or another binding workflow requires them.
- Do not scan an entire repository when an entry point and its reachable path can answer the question.
- Do not collect redundant sources after a material claim is already corroborated.
- Do not require every evidence type. Add web, history, network observation, runtime experiments, or artifact inspection only when it can resolve a real gap.
- Begin broad enough to locate the authoritative source, then use targeted queries for unresolved gaps.
- Ask one minimal clarifying question only when different answers would materially change the target, authorization, or output.

## Stop Condition

Stop research when:

- the input, key decision or transformation, state change, output, and important failure boundary are supported or labeled unknown;
- no unresolved contradiction changes the central explanation;
- a new reader can follow the causal chain without relying on the researcher's private context; and
- additional sources would add detail rather than change the model.
