# Execution context erratum: review-followup-freshness

The historical `review-followup-freshness/receipt.json` and
`review-followup-freshness/post-regeneration-receipt.json` command arrays record
Python arguments, not standalone executable command vectors. Their omitted
interpreter was Python, and their working directory was
`maps/historical-world-rpg/age-of-sail-world` in the source checkout identified by
the receipt. Reproduction therefore requires prepending the Python executable
(for example `python3`) to each array and using that project directory as cwd.
This applies to both `tooling/*.py` arrays and the `-m unittest ...` array.

This clarifies the records, not a new execution. It supplies no claim that the
historical receipt captured an exact interpreter binary or environment. The
original receipts, logs and manifest are unchanged; the initial orchestration's
failed status and the separate post-regeneration consistency scope remain valid
as recorded. No pre-existing freshness, full execution or release acceptance is
introduced by this clarification.
