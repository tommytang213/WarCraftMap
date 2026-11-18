# Artifact workflow step-boundary regression

Published PR601 head e0c1ac3c failed the Python suite with one failure among 1335 tests (two skipped), GitHub run44254429617/job134632582234. The upload contract test sliced the whole workflow tail and therefore attributed the following diagnostic notice step's `always()` to the upload. The actual upload retains its readiness gate and implicit success condition.

Local13a20106 replaces that tail split with a peer-step boundary helper and adds regressions: a following diagnostic always-step is allowed, an always-condition inside the actual upload is still rejected, and unnamed peer actions also terminate extraction. No workflow or upload policy changes. Focused tests passed19/19 (artifact12, diagnostic guard4, workflow triggers3). Independent review approved; cherry-picked integrated1a78bf3d additionally reran artifact12 successfully. Full current-head CI remains required.
