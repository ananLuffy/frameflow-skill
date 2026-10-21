# Evidence model and limits

Schema version 1 uses exact keys; unknown fields are errors. See the synthetic
example for canonical JSON. Identifiers are 1–80 ASCII letters/digits/._- (first
character alphanumeric); hashes are lowercase SHA-256; paths are relative POSIX
paths under the manifest directory. Duplicate JSON keys/IDs/references, dependency
cycles, parent traversal and symbolic-link files/components beneath the chosen
root are rejected. The caller-selected root is canonicalized first so operating-
system root aliases work consistently; this does not permit symlinks inside it.

An artifact is `{id,path,sha256,dependencies}`. Dependencies are artifact IDs.
An action is `{id,kind,artifact_ids,status,evidence,scope_sha256}`. Kinds equal
workflow stages. Status is `pending` or `done`. A review substitutes `reviewer_id`
for `kind`, and status is `pending`, `pass` or `fail`. Pending records require
null evidence/binding. Nonpending records require evidence `{path,sha256}` and
a valid scope binding. Reviewer must differ from the manifest's author label.

The scope SHA-256 uses UTF-8 canonical JSON (`sort_keys=True`, compact separators)
of project ID, mode, author ID, obligation fields (including status) except evidence/scope,
and the sorted transitive artifact closure including all dependency lists, paths
and byte hashes. `frameflow.__main__.scope(doc,row)` computes it. Thus changed
artifacts/dependencies, reviewer/obligation identities or mode invalidate bindings.
Represent the brief, rubric, approved intent and rights/use contract as versioned
artifacts and include them in each affected artifact dependency closure; otherwise
the CLI cannot notice a change to those external requirements.
Hash the actual review report separately as evidence; never regenerate bindings
as a substitute for a fresh affected-scope review. Historical reports should be
preserved outside the active manifest with immutable version names.

`next` gives failed reviews priority (`REVIEW_FAILED` in review/plan modes,
`REPAIR_REQUIRED` only in revise/production), then pending stage actions, then outstanding
reviews. This is a simple advisory order, not an execution scheduler: review ready
assets early in the real workflow rather than waiting for this order. All modes
remain read-only. There is no command to render, approve, upload, charge, retry a
provider call, mutate manifest state or claim actual listening/visual perception.

The workflow document holds richer requirements (audience, rights, review count,
budget, quality dimensions, approvals). This prototype CLI cannot prove that all
of those were faithfully projected into a manifest, nor authenticate evidence,
reviewers, intent or signatures. It does not inspect media codecs or parse review
report assertions. It is not safe against a malicious local process racing file
reads or rewriting the manifest; use a trusted immutable checkout for validation.
Limits: 4 MiB manifest; 10,000 rows per collection. Large media are streamed for
hashing, not loaded into RAM. No third-party runtime dependencies.
