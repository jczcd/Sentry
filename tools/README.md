# Tools

## Active use with review

- `isaac/cad_import`: historical CAD import helper. It requires an external STEP source and must not overwrite the canonical source.
- `isaac/stage5d_builder`: historical Stage5D builder/test helper. It requires a valid, newly accepted Stage5C and prerequisite reports; it is not proof that those inputs exist.
- `migration/4090` and `migration/5090`: pack/verify/restore tooling. Review absolute-path detection and target-host assumptions before use.

All tools default to evidence-preserving behavior. Large generated output belongs outside Git or in an approved artifact store.
