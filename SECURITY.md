# Security boundaries

This is a local, single-owner CLI for trusted workstations. It is not a hosted service or a multi-tenant sandbox.

- Semantic operations send selected source/page/draft text to OpenRouter and its provider. Only process material authorized for that service. Deterministic `lint`, `init`, and `status` do not make network requests.
- Keys are read at runtime and placed only in the HTTPS Authorization header. Env files are parsed, not executed. Authenticated redirects are rejected. Raw provider error bodies are never logged.
- No key is embedded in source files or example data. Keep vaults and captured CLI output private; selected evidence appears in JSON output. Do not put credentials inside source documents.
- All model inputs are untrusted as instructions. Jev's instruction-risk score supplements host-agent permission controls; it is not a proof of safety or a secret scanner.
- Pages are written only after deterministic path/link/source checks, a grounding gate, and revision validation. Lint never automatically deletes or merges content.
- Vault paths reject internal symlinks and invalid page IDs. Atomic writes and an advisory lock protect cooperating processes. A hostile process running as the same OS user can still modify files or race checks.
- Network failures are not retried. Unknown charge outcomes retain a local reservation. Provider-side limits are the final billing boundary.

Report vulnerabilities privately to the repository owner. Include a minimal synthetic reproduction, never a real API key or confidential vault.
