# Quest-scoped synchronization of already-earned research

Source repair: `f56fa6e7589d21068e7fdd96e250d2077d935449`.

A valid domain receipt or physical visit can automatically enter a subsequent
`research_unlocked` objective. Previously only new research, explicit acceptance
and explicit stage advancement synchronized persisted research, leaving this
path incomplete even when the player already owned the technology.

The repair checks the affected quest after successful receipt delivery, physical
acceptance or physical visit. Explicit acceptance and stage advancement now use
the same quest-scoped helper. A genuinely new technology unlock retains its
all-active-quest sweep. No other action sweeps unrelated quests.

The original action proves only its original objective. Any research completion
independently verifies persisted player technology ownership, the explicit
`research_unlocked` binding and the technology entity reference. A domain-receipt
objective cannot be substituted. Each synchronization checks its entry stage
only, not a fixed-point cascade; consecutive preowned-research chains remain a
separate behavior limitation. Physical acceptance does not also turn in rewards.

Five production-runtime regressions cover receipt and physical advancement,
physical acceptance, unrelated quests and bounded stage transitions, duplicate or
forged receipts, and knowledge-only interaction. Existing tests additionally
cover foreign-controller research and unbound domain-receipt objectives.

Independent static review approved the exact repair commit. The five new
regressions subsequently passed with the digest-pinned compiler and original
bundled runtime. The complete 829-test gate nevertheless failed on an existing
transport test's 20-second deadline. See `wurst-local-2542625/README.md` for the
failed complete run and separately labeled remaining-shard diagnostics. Python
checks do not replace this failed integration gate. The recording receipt
authority in these developer tests is not a live consultation adapter. No native
playability, content-completeness or release claim is made; #438/#600 remain open.
