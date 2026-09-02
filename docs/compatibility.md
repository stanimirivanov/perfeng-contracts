# Contract compatibility

The current candidate bundle is `0.2.0`. It adds workload/catalogue contracts
to the `0.1.0` migration foundation without changing the four original payload
schemas. Establish the missing phase-1 contracts before a stable `1.0.0` release.

Two versions serve different purposes:

- A path such as `result/v1` identifies a wire-format generation.
- A bundle release such as `0.1.0` identifies the exact set of shipped schemas.

The existing result payload keeps integer `schemaVersion: 1`. The other three
schemas do not declare that property, so consumers must not inject it into
their payloads. Select their version through the API or artifact contract.

Changed schema IDs in this extraction require consumers to update their
schema lookup paths. Payload fields are preserved except that an explicit
`null` metric type is now accepted, matching the schema's existing type and
default declarations. That broadening needs consumer review if a consumer
previously assumed a string whenever the field is present.

Within a stable generation, review compatibility in both directions: can a
new reader read old records, and can an old reader accept new records?
`additionalProperties: false` means even adding an optional property may break
old readers if a new producer emits it. Enum additions and newly accepted nulls
also need producer/consumer coordination. Do not label every additive edit
backward compatible.

For a breaking change, create a new domain major path, document conversion and
rollout, retain old readers during transition, and publish a new bundle major
once the bundle is stable. Preserve immutable raw evidence; conversions produce
new derived artifacts. Documentation-only corrections can use patch releases.

PR validation covers the checked-in compatibility corpus and rejects malformed
identifiers, timestamps, unknown states, unsupported result versions, and
invalid defaults. It does **not** prove compatibility for all possible JSON
documents. Every schema change must also explain reader/writer compatibility
and add positive and negative cases for the affected boundary.

Run lifecycle status, SLO outcome, regression outcome, and measurement quality
remain distinct concepts. Their later contract PRs must preserve the proposal's
separation between failed execution, poor measurements, and performance changes.
