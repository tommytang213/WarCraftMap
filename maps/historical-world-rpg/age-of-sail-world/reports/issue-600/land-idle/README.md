# Empty land arsenal interval: focused validation

Final source `2ee66c55562ae62008a68c14716b86efbd7c6a96` was integrated unchanged at `20e6474fb7b3eedcf1980914c5555897189a505d`. Production only advances the cursor when both office and project owners are empty; active daily work, retained fields and final reload refresh remain intact.

Two attempts are retained, not combined into a fabricated pass:
- Initial `cd06acdbe59006316e1c2aaa6eb4de06782108b1`: typecheck succeeded;17/18 passed. Only the new daily-reference test timed out at the unchanged20-second limit. Existing active tests and the new post4000-day activation and retained-field tests passed.
- Corrected `2ee66c55`: typecheck succeeded;18/18 passed, exit0 and no parsed issues. Production unchanged from the initial attempt. The reference test now exercises16 actual daily API deliveries and models remaining empty-state `lastDay++` transitions through+4000. It compares complete military snapshots and refresh counts. Its optimized path uses16+3984 jumps; the separate activation test retains one real4000-day jump followed by funded office/project completion. This does NOT claim4000 real daily API calls passed.

Both attempts have verified unchanged frozen inputs, separate dependency content inventories, raw typecheck/execution logs, unchanged parsed results and actual orchestration. Driver exit is orchestration status; use parsed test returnCode for test success (the runner records failures before breaking). The original bundled runtime/compiler were extracted from the pinned image, not executed in Docker. The result executionImage field records configured provenance, not container execution.

Manifest files hashes cover on-disk bytes, including compressed archives. rawTranscripts hashes/sizes refer exclusively to decompressed original logs. No tests were rerun while archiving.

Focused18/18 does NOT prove the full campaign timeout is fixed or establish complete-current-head, native or release acceptance. Recovery registration variability is separate. No acceptance reports or gameplay source are changed by this archive.
