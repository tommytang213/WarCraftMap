# Chemical audit fixture: source-only attribution refresh

Source revision: `21e0bf122defae9cba3d7803a8eecd913ec88810`.
Source tree: `b752250e895a5ad026c449266b89a3d1753ab949515568d2f279af17b36dbcef`.

This records source-only regeneration after correcting the synthetic chemical
binding test's source-identity protocol. It adds no Wurst execution, compiler,
Docker, native, full-gate, story-pilot or release acceptance evidence.

`regeneration-receipt.json` records all three write commands with expected
exit 1 because runtime/release/traceability blockers remain. Completion of this
orchestration does not mean those reports pass. `report-diff.json` lists every
changed JSON leaf compared with the pre-regeneration checked-in reports; changes
are limited to source revision and source-tree attribution. Finding/status data
is unchanged.

`post-regeneration-receipt.json` separately records the subsequent read-only
trace check and report-freshness test. These establish consistency only AFTER
regeneration, never pre-existing freshness. Both receipts verify unchanged
source identity. All prior archives, including previously failed receipts, are
preserved without modification. The manifest binds this archive's files.
