# Security policy

## TL;DR

- Do not disclose suspected vulnerabilities in public issues or pull requests.
- Use GitHub private vulnerability reporting when available.
- If no private channel exists, request one without sensitive details.
- The project is pre-release; only the current default branch is supported.
- Test only systems, repositories, accounts and data you are authorized to use.

## Supported versions

The performance engineering platform has no supported production release.
Security fixes target the current default branch. Replace this section with an
explicit version table and disclosure policy when stable releases begin.

## Reporting a vulnerability

Use the repository Security page's **Report a vulnerability** action when it is
available. If private reporting is unavailable, do not publish the report.
Create a minimal issue asking the owner for a private security channel without
naming the affected contract, exploit, data or reproduction details.

Include the affected revision and contract generation, impact and conditions,
minimal reproduction, sanitized evidence, known mitigations, and prior
disclosure where applicable. Do not retain, alter or disclose accessed data
beyond what is necessary to demonstrate the issue safely.

## Triage and disclosure

Maintainers SHOULD acknowledge a private report, validate severity and scope,
and agree on communication before disclosure. Response times are best-effort
until a staffed process exists. Coordinate disclosure after a fix or effective
mitigation is available. Good-faith reports SHOULD be handled respectfully.

## Security expectations for contributions

Contributors MUST follow the untrusted-input, reference-resolution,
secret-handling, dependency and verification requirements in
[CONTRIBUTING.md](CONTRIBUTING.md) and the
[engineering standards](docs/development/engineering-standards.md). Changes
affecting schema resolution, authentication shapes, credentials, sensitive data,
artifact locations or external references MUST document their threat and
failure model and receive focused security review.
