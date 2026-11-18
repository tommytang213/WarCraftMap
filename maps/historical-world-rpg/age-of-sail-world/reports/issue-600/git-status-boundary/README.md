# Git status boundary exception

Published `cdf7bbc7` failed the reusable-boundary audit because the standard Git
`--porcelain` flag was mistaken for the authored porcelain commodity.

Local repair `3fda4e96c09c335ab9e296f9d83df99375b224e3` adds one existing-format,
exact-path/exact-token exception for that flag in the focused replay tool.
Neither the scanner nor the Git clean-check command changed. Independent static
review passed. The direct framework audit passed, and the dedicated regression
passed its clean baseline plus three negative assertions: actual porcelain and
grain literals in the same file, and the Git flag in another file, still fail.

The contract is part of source identity, so prior 6b6a/9d13 Wurst evidence remains
historical, not a new exact-source execution pass. No compiler test was rerun for
this audit-only patch. Runtime/release reports were refreshed without execution
evidence and remain blocked; traceability and report freshness passed. The
receipt binds the new source identity and verifies it stayed unchanged.

No live story-service enablement, native acceptance, complete passing Wurst gate,
merge, release, schema change, timeout change or upload-guard weakening.
