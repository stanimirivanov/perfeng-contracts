# Perfeng shared language

Terms used at boundaries between the performance platform, its producers, and its consumers.

## Language

### Selection

**Test ID**
Stable identity of the test across Runs. The reviewed registry binding determines which Performance Policy applies.

**Workload**
An immutable versioned profile for a tool, including its configuration, model, phases and dataset selection.

**Test catalogue**
Versioned definitions of the tests, their available workload profiles and their runner provenance.

**Performance Catalog**
A current, principal-scoped view of discoverable performance resources and reviewed combinations. Live admission checks authority separately.

**Performance Policy**
Versioned rules for measurement quality, SLOs and regression evaluation. Its ID, version and exact-byte digest identify the selected policy.

**Resolved Configuration**
The immutable settings selected for one execution, including applicable runtime overrides.

### Execution

**Run**
A durably accepted execution request with a revisioned lifecycle. A completed Run has finished its required stages regardless of its performance verdict.

**Integration Request**
The immutable, issuer-scoped request intent that can map to one native Run.

**Integration Attempt**
An execution intent identified by its own attempt ID and Integration Request. Fresh execution requires fresh request and attempt identities.

**Native Worker Attempt**
One leased execution claim on a Run by a native worker. A later claim on the same Run has a distinct attempt identity.

**Lease**
Expiring authority to perform a specific claimed execution and its allowed writes.

**Retry**
Repeat the same operation within its original identity and applicable authority. Use the operation’s specific name when the retry rules differ.

**Receipt Recovery**
Retrieve previously accepted intent after an uncertain response, without creating execution work.

**Rerun**
Request a distinct Run from a frozen source Run selection, subject to current eligibility and authorization.

**Rerun Receipt**
Immutable acknowledgement that a rerun intent was accepted and associated with its child Run.

### Evidence and decisions

**Measurement Window**
The observed interval that contributes measurements. Warm-up and cooldown are outside it.

**Execution Artifact**
The exact image, source checkout or release archive selected to run a workload.

**Artifact Reference**
Identity and integrity metadata for exact retained bytes. Access to the bytes requires separate authority.

**Raw Result Manifest**
The run, workload, producer and measurement-window record that names the original evidence payloads.

**Normalized Result**
Contract-defined metric statistics plus references to the raw artifacts actually used.

**Baseline Version**
A versioned normalized reference with exact source evidence and an approval history. A new comparison requires eligibility and approval at selection time.

**Analysis Report**
Recorded per-rule measurement quality, SLO and regression results for a candidate and any selected baseline.

**Analysis Publication**
An immutable correlation of an Analysis Report with retained Integration Request and native execution evidence.

**Run Comparison**
An authorized historical view of the exact report-time comparison inputs and results. Available evidence can carry an inconclusive verdict.

### Authority

**Service**
Stable owner of service-scoped Runs, Baselines and related evidence.

**Verified Actor**
Authenticated identity on whose behalf an operation is performed.

**Caller**
Authenticated identity presenting the request to the receiving boundary. A delegated caller may differ from the Verified Actor.

**Service Grant**
Current, revocable authority for a principal to perform specific operations for a Service.
