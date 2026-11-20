# Isolated continuation CI policy

The unique `fix/dot-wc3-continuation-20261118` branch is a continuation of draft #536, not a second writer to that branch. It may run standard public-repository Ubuntu validation, but artifact allowance is unverified. All six workflow artifact uploads are therefore excluded for this PR head and branch ref; no cache-upload action is configured. Existing validation, failures, release-readiness conditions and other branches' behavior remain intact. The campaign job explicitly states that earlier artifact-download references do not apply to this logs-only run.

Independent review approved the guard and notice. The complete automation suite passed 219 tests at local revision `3297a08cac4f8baabbd4dba3dc4caf2d8845e78f`. Three prior failures came from a stale main-only assertion despite the already-existing #536 scoped fallback in three workflows; its replacement permits exactly those existing branches, not arbitrary pushes. No event trigger was widened.

There are no workflow artifact/cache uploads for this diagnostic branch, not a guarantee of zero GitHub storage: repository evidence, normal logs and job summaries remain. These CI results do not authorize merge, deployment, native acceptance, issue closure or a release. Any API-published equivalent tree receives a different commit identity and still requires its own remote-head validation/review.
