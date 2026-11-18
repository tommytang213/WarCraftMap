# Campaign-owner recruitment guard

Local source revision: `c79d2d898d0dcbe91efae4a2f0a0b68c4e24bfb0`.

The chat registry accepts every player slot, but `/recruit` and its `/hire` alias previously mutated the single campaign roster without the ownership check already used by allocation/navigation. The production handler now rejects non-`Player(0)` senders before invoking roster authority. Existing eligibility dates, duplicate checks, starting progression and save formats are unchanged.

Negative production-command tests cover another player and a missing sender through both aliases. Authority/RPG snapshots, resource effects, saved bytes and save-write counts remain unchanged; the owner can then recruit, receive the starting profile and save/load it. Existing fixtures explicitly identify the owner instead of using null as a stand-in.

Independent static review approved the exact source diff. Original pinned compiler/runtime execution passed all 12 recruitment-window tests and all 5 starting-profile tests. Five recruitment-generation and five starting-profile Python tests also passed. These are focused checks only, not a full current-head gate or native Warcraft acceptance. Earlier complete-gate failure and partial diagnostics are recorded separately and remain failed/incomplete. No release, merge or issue closure is authorized by this receipt.
