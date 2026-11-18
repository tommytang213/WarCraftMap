# E474 review: source-only attribution refresh

Source revision: `8ecaa772d8e240c2fdadc603404b689150221cfb`.
Source tree: `4583a032d29fe3a05033aef24c8a7f9ceb12e23c6ef8d3c22e20b06b12b6202e`.

This records source-only regeneration after the merged diagnostic, replay and
science input safeguards. It adds no Wurst execution, compiler, Docker, native,
full-gate, story-pilot or release acceptance evidence.

All command arrays include the actual Python executable. Their working directory
is `maps/historical-world-rpg/age-of-sail-world` within the checkout of the source
revision above. This archive was produced in an isolated attribution worktree.

`regeneration-receipt.json` records the three write commands with expected exit 1
because runtime/release/traceability blockers remain. Orchestration completion
does not mean those reports pass. `report-diff.json` lists every changed JSON leaf
against the pre-regeneration checked-in reports: only source revision and tree
attribution changed, with finding/status data preserved.

`post-regeneration-receipt.json` separately records the subsequent read-only
trace check and report-freshness test. These establish consistency only AFTER
regeneration, never pre-existing freshness. Both receipts verify unchanged
source identity. All earlier archives and failed receipts remain unmodified.
The manifest binds the new archive files, excluding itself.
