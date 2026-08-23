# Security Policy

## Supported Versions

Only the latest `master` branch is supported for security fixes.

## Reporting a Vulnerability

This is a free-stack, zero-dependency tool.  There are **no API keys, no
secrets, and no third-party dependencies** in the dependency tree (pure Python
standard library), which minimizes the attack surface.

If you believe you have found a security vulnerability, **do not open a public
issue**.  Instead, open a private security advisory on GitHub.  Please include:

- A description of the vulnerability and the impact.
- Steps to reproduce or a proof of concept.
- The version/commit you are running.

We will acknowledge receipt within 72 hours and aim to ship a fix within
7 days for confirmed, non-trivial issues.

## Hardening Notes

- **No secrets in repo.** The codebase contains no credentials, tokens, or
  email addresses.  All configuration is in-tree constants only.
- **No command execution from untrusted input.** legal-clause-finder never
  invokes a shell or subprocess — it is a pure file- and regex-based linter.
  There is no `shell=True`, `os.system`, `subprocess.*`, `eval`, or `exec`
  anywhere in the package source.
- **Bounded regex.** The curated clause library uses only bounded character
  classes and optional single quantifiers — no nested quantifiers or
  backreferences — to eliminate the regular-expression denial-of-service
  (ReDoS) surface.  Every pattern is compile-tested in CI.
- **Path & size safety.** File inputs are validated against an allow-list of
  suffixes (`.txt`, `.md`, `.text`) and a 5 MB size cap
  (`MAX_FILE_BYTES`) to prevent memory exhaustion.  Paths are resolved and
  de-duplicated to prevent symlink / duplicate traversal.
- **No network.** The scanner reads only local files; it never opens a socket.
- **Stateless.** No on-disk state is persisted between runs, so there is no
  stored-data attack surface.
