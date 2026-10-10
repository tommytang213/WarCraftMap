# Issue #451: physical remote command transport

The registered region command resolves current holdings and mobile forces onto
physical chapter maps, writes an independent durable command request, and loads
through the production physical loader. Destination registration and transactional
reconstruction preserve the home party, including an entirely wounded party.
The return action restores home terrain and coordinates while retaining orders.
See [the runtime contract](../../docs/REMOTE_COMMAND_MAPS.md).

Campaign schema 9 adds command context and migrates schemas 1–8. Permission is
revalidated separately from saved discovery; no grant, UI token or native handle
is saved. The old logical projection-only coordinator remains available to
single-map consumers. Source and destination tests use recording native boundaries
with real campaign registration, codec, command dispatch and military callbacks.

Reproduce the diagnostic after a complete pinned execution run:

```sh
python3 reports/issue-451/build-diagnostic.py --grill /path/to/pinned/grill
python3 reports/issue-451/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --output-dir _build/issue451-evidence
```

The build helper verifies source identity and every pinned test before reusing
execution evidence. It still typechecks and compiles every physical chapter.
The verifier checks chapter paths, compiled transport calls, source identity and
44 executed receipts across 11 scoped obligations. The broader inactive-world
simulation obligation (REQ-0302.02) and native-launch gate remain separate.
This artifact is diagnostic; it is not release approval or player gameplay QA.

`validation.json` records the final local checks and their limits. Generated maps
stay under ignored `_build`; compressed transcripts and scoped evidence are
retained here. No commits, pushes, GitHub writes, services or global tooling changes
are part of this work. The cached pinned compiler was copied out of a stopped,
unmounted container and run locally. The outer worker performs authoritative
repository validation.
