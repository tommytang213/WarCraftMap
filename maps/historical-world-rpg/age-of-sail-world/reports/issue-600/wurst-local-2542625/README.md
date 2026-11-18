# Local pinned-interpreter validation, source 2542625

Source: `2542625e9539e43050b61c935581284dc581d603` (local development revision).
Compiler SHA-256: `1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
Grill 1.4.0.0-2c676dd and bundled Temurin 25+36 were extracted from the digest-pinned configured image; this was not a Docker execution.

The official complete run **failed** after 299/829 tests passed: the third 100-test process timed out in `CommandMapTransportTests.commandRemoteSaveRecoveryAndRejectedHomeProjectionRetainOrders` under the unchanged 20-second limit. All five new quest-research synchronization regressions passed. Full failed results and transcript are retained here, not replaced by focused evidence.

A separate diagnostic copy then ran the unexecuted original batches 4–9, preserving their frozen instrumented source hashes and original 100-test process boundaries: **529/529 passed**. Together these observations cover 828 passing tests and one timeout, but they are not a successful complete gate. No release acceptance is inferred. The manifest records raw-byte SHA-256 values; files are deterministically compressed.

Controlled focused comparisons passed with baseline runtime/tests and with the new runtime plus old tests; configurations containing the new test definitions timed out. Moving test packages and changing initial heap did not fix it. A diagnostic profiler (same compiler, different full JDK from the pinned image) found eager constructor AST formatting in disabled interpreter trace logging. One semantics-preserving constructor-factoring experiment also timed out and was rejected. Neither compiler, test deadline, assertions nor production constructors were changed to obtain a pass.

This evidence predates the subsequent recruitment-owner repair. That repair has separate focused checks; these 829 observations cannot be attributed to its later source. Native Austria → Victory → Continue acceptance, complete current-head integration, built-artifact verification, and issues #438/#600 remain unresolved.
