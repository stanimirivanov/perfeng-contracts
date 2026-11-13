# Immutable Run comparison projection

## TL;DR

- Run API 0.6.0 / candidate bundle 0.29.0 defines one exact authenticated read.
- AVAILABLE preserves the report and its historical selection; it never recomputes it.
- INCOMPLETE and INACCESSIBLE carry no evidence or performance verdict.
- Providers must retain and verify the binding before enabling this candidate API.

## Operation and authority

`GET /v1/runs/{runId}/comparison` has no body, query, mutation or redirect.
Authenticate and authorize the exact native Run under the established legacy or
explicitly admitted service mode (`run:read`); no caller field selects an owner.
Unknown and invisible Runs share the existing uniform scoped 404/NOT_FOUND.
Authorize every disclosed report, policy selection, baseline and publication
before returning evidence. A public reference is never a fetch capability.
All responses MUST use `Cache-Control: no-store`. No response claims freshness
or authority beyond its current authorization check; never serve a cached or
sample comparison during an outage.

| HTTP / status | Meaning and permitted body |
|:--|:--|
| 200 / AVAILABLE | Original immutable comparison, with `request` and `evidence` |
| 200 / INCOMPLETE | Authorized Run has no complete retained comparison binding yet; no request/evidence fields |
| 200 / INACCESSIBLE | Complete authorized evidence cannot be disclosed; no request/evidence fields |
| 400, 401, 403 | Existing malformed/authentication/global-operation errors |
| 404 | Uniform unknown or invisible Run; no evidence-existence disclosure |
| 429, 503 | Existing retry headers; operational outage or failed integrity verification is unavailable, never stale evidence |

Determine INCOMPLETE only from authorized Run retention/admission metadata;
never probe a hidden object and turn its absence into a distinguishable result.
Use the same INACCESSIBLE observation for hidden or unknown referenced evidence,
without revealing an object name, owner, selection or why its access failed.
Transport/storage failures and checksum mismatches fail closed with 503.

The serialized UTF-8 response MUST be at most 2 MiB; refuse rather than truncate.
Canonical compact JSON conformance also enforces this bound. Providers must
additionally enforce the actual wire-byte limit. Original report and frozen
policy verification inputs are each bounded to 1 MiB; at most 1,000 rules are
projected. Oversized valid source reports require an explicit later contract
revision or another bounded read design, not partial rule coverage.

## Available fields and provenance

`schemaVersion: 1`, `kind: RunComparison`, `runId` and `status` form the closed
envelope. AVAILABLE adds only:

- `request`: the immutable native CreateRun accepted for this Run. Preserve
  candidate Git SHA and image digest, testSuite/profile, catalogue, environment,
  and policy ID/version/SHA-256. Never re-resolve a current alias or registry.
- `evidence.native`: the retained report-time native run/test/workload/policy
  identity and nullable exact baseline identity/version/normalized artifact.
  The binding must attest the historical approved selection. Current retirement
  or approval is not a new report-time fact or permission to execute again.
- `evidence.report`: the exact `analysis-result/v1` artifact ID, Run, URI, byte
  size and SHA-256, reusing the existing publication artifact schema.
- `evidence.analysis`: the original parsed analysis/v1 report, verified against
  exact report bytes before parsing. Candidate/reference artifacts, per-rule
  selectors, values, units, sample/CV evidence, quality, SLO, regression, method,
  effect and non-blocking mode retain their original semantics. No aggregate
  PASS, new WARN, significance claim, lifecycle transition or numeric default
  is invented. An INCONCLUSIVE analysis is still AVAILABLE evidence.
- `evidence.directions`: one entry per original report evaluation in report order,
  `{ruleId, direction}` from the frozen policy's regression configuration.
  Null means that section has no configured direction, not lower-is-better.
  Full thresholds remain in the exact policy resource, not a parallel rule model.
- `evidence.publication`: the original complete performance-analysis/v1
  publication if correlated in the retained binding; null for a native comparison
  without retained request correlation. Preserve request/attempt/event/provider
  identities and original CI principal, never replace them with the current reader.

References and hashes are necessary but do not independently prove admission,
object authorization or verified bytes. The provider must use independently
retained inputs; a matching echo of projection fields is not proof. Cross-run,
policy, baseline, artifact, unit, direction and publication substitutions fail
conformance. Hash exact bytes before parsing; reject duplicate keys/nonfinite
JSON. Do not fetch URI metadata or reconstruct metrics from raw runner data.

## Immutability, compatibility and rollout

All AVAILABLE content is frozen, including optional correlation. Do not enrich
or replace it silently after a later publication, catalog edit or approval.
Retain the independently bound original report; a correction needs an explicit
future contract/versioned execution path. INCOMPLETE can become AVAILABLE when
real retained evidence arrives. Access loss or retention failure can return a
current availability-only observation; later recovery must restore the same
AVAILABLE comparison, never a cached fallback. No mutable lifecycle revision,
reader identity, current baseline state or read timestamp enters the projection.

The envelope/path is split-authored. ComparisonEvidence is generated directly
from canonical Effect AnalysisV1/PerformanceAnalysisV1 and checked by
`pnpm contracts:check`; do not edit its generated fragment. Existing closed
Run, Integration, analysis schemas and operations remain unchanged. Strict API
consumers must opt into the new reviewed document. The semantic intent record
binds the exact PR base and both digests; it is not human approval.

Shared contract review precedes control-plane PR47's report-time retention,
PR48's guarded serving and Console adoption. An old provider's 404 does not prove
capability readiness. This PR activates no provider, consumer, deployment or
release. Roll back consumer opt-in while retaining historical bindings/bytes.
Offline schema and relationship tests are not live authorization or storage
verification. See [ADR-0017](decisions/0017-project-immutable-run-comparisons.md).
