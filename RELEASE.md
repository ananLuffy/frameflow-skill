# v0.1 initial source release

Status: initial source published at https://github.com/ananLuffy/frameflow-skill.
The initial public source commit is `ac2c6f29dd1a4fe2a20be9565dea8f43ff7f8c7a`.
This is not a package-index release, a Git tag announcement or an application
submission. This initial workflow skill and evidence CLI uses the MIT license
in LICENSE for its original code and prose. No third-party media, private
production assets or inherited repository history are included. The copyright
notice uses a collective project attribution, not a claim to third-party rights.
Future third-party contributions and assets require their own provenance review.

The project is a small prototype, not a video-generation service or a quality
certification. Provider adapters are proposed contracts, not implemented
integrations. No adoption scale, program eligibility or acceptance is claimed.

A portability follow-up canonicalizes the caller-selected verification root
before containment comparisons. Operating-system root aliases no longer cause
false escape errors in direct helper use; symlinks beneath the root remain
forbidden. The CLI already canonicalized its root. Added regression tests cover
alias access and rejection of internal/escaping symlinks.

Reproduce tests from the project root:

```sh
python -m unittest discover -s tests -v
python -m frameflow verify examples/demo/manifest.json
python -m frameflow verify examples/review/manifest.json
python scripts/package.py
```

The packaging script uses an explicit source allowlist and includes a SHA-256
inventory. The inventory excludes itself and does not establish provenance,
security or artistic quality. Do not include private review inputs or caches.
