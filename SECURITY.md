# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | ✅ |
| < 1.0 | ❌ |

## Reporting a vulnerability

Please **do not open a public issue** for a vulnerability. Use GitHub's private
[Security Advisory](https://github.com/Jack91124/ai-extension-manager/security/advisories/new)
form, or contact the maintainer listed in the repository profile. Include:

- what an attacker can achieve, and the preconditions;
- the exact command or file that triggers it;
- a minimal reproduction (a fake AEM home is fine — never include real credentials).

We aim to acknowledge within 72 hours and to publish a fixed release with an advisory.

## What this tool can do to your machine

`aem` reads and writes files in the AI tool directories it detects, plus its own library under
`~/.ai-extension-manager`. It can copy directories, create links, restore backups and rewrite MCP
JSON entries. It does **not** run imported code, and the seven scripts never install plugin code.

## Built-in protections

- **Secret scanner** — API keys, tokens and private keys found in imported resources are refused.
  MCP `env` values can be rewritten to `${ENV_VAR}` placeholders so a shared library never carries
  credentials.
- **Dangerous-pattern scanner** — destructive shell fragments (`rm -rf /`, disk formatting,
  reverse shells, encoded payloads, `curl | sh`) raise the risk level; high risk requires an explicit
  `--allow-risk`.
- **No silent overwrite** — state B/C conflicts write nothing and exit `2`; overwrites happen only
  after an automatic backup, and only when the caller asks for it (`--on-conflict` / `--force`).
- **Git rewrite refusal** — a global or local `url.*.insteadOf` that redirects an official host to
  a mirror is treated as a supply-chain risk and refused before any clone (`--allow-mirror` to opt in).
- **Local only** — no network calls except the git clone you explicitly request; no telemetry.

## Limits (read this)

- A resource you approve with `--allow-risk` or `--allow-secrets` is your responsibility.
- The scanner is regex-based; it reduces risk, it does not prove a resource is safe.
- Resources are hashed and compared, not signed. There is no registry of trusted publishers.
- `--mode link` creates directory junctions/symlinks; anyone who can write the library can change
  every linked copy. Prefer `copy` (the default) for untrusted content.
- The central library contains whatever you import. If it is on a synced cloud folder, that provider
  can read it.