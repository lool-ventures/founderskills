# Security Policy

## Reporting Vulnerabilities

**Do not open a public issue for security vulnerabilities.**

Please report vulnerabilities through [GitHub's private vulnerability reporting](https://github.com/lool-ventures/founder-skills/security/advisories/new).

## Response Timeline

- **Acknowledge** within 48 hours
- **Fix or workaround** within 7 days for critical issues

## Scope

Security-relevant code in this project includes scripts that process user input:

- `founder-skills/skills/market-sizing/scripts/` — market sizing calculators and validators
- `founder-skills/skills/deck-review/scripts/` — deck review scoring and report assembly
- `founder-skills/skills/ic-sim/scripts/` — IC simulation scoring and conflict detection

All scripts accept structured input (JSON/CLI arguments) and produce structured output. The primary risk surface is malformed input leading to unexpected behavior.

## Out of Scope

- The Claude platform itself (report to [Anthropic](https://www.anthropic.com/responsible-disclosure-policy))
- Third-party dependencies (report upstream)
