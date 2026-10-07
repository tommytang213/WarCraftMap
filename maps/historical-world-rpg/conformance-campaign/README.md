# Reed and Stone: framework conformance

This tiny invented campaign proves that the gameplay framework accepts different
content. It has two polities, two towns, two commodities, one recruitable courier,
one equipment item, one quest and one dated event. A selector hands the party to
one of two connected 64-by-64 physical maps. The two maps have different terrain
inputs and use the common materializer and boundary-arrival resolver.

All mechanisms come from `_shared/`. This directory contains configuration,
scenario data and a neutral folder-map container, with no gameplay code. Stock
Warcraft rawcodes are resolved by the common adapters. A stock UI confirmation is the only audio asset; the presentation profile has
no music or ambience. This fixture needs no custom assets or World Editor work.

With the repository's pinned Wurst toolchain available:

```sh
python3 ../_shared/tooling/validate_framework_fixture.py .
```

The command builds and inspects `_build/release/ReedConformance.w3n`, then changes
the authored ID namespaces and triples commodity base prices according to
`mutation.json`. It rebuilds and reruns the identical conformance contract without
editing framework code. Both campaigns use the same production registrations,
origin/travel handoffs, RPG interaction, trade, control change, clock, save codec
and reconstruction adapters. See the [layer contract](../_shared/README.md) for
scope, boundary checks and validation limits.
