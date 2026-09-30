"""Scenario-neutral deterministic audio selection and bounded channel ownership."""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib


class AudioPlaybackError(ValueError):
    pass


@dataclass(frozen=True)
class AudioContext:
    physical_map_id: str
    region_id: str | None = None
    settlement_type: str | None = None
    travel: str | None = None
    combat: str | None = None
    modal: str | None = None
    event: str | None = None
    discovered_ids: tuple[str, ...] = ()


class AudioDirector:
    """Presentation state only. Callers must never serialize this as campaign authority."""
    def __init__(self, manifest, profiles):
        self.manifest = copy.deepcopy(manifest)
        self.profiles = copy.deepcopy(profiles)
        self.assets = {x["id"]: x for x in manifest["assets"]}
        self.categories = {x["id"]: x for x in manifest["categories"]}
        self.active = {}
        self.transient = []
        self.last_played_ms = {}

    def _profile(self, context):
        candidates = []
        precedence = {"event": 60, "modal": 50, "combat": 40, "settlement_type": 30, "travel": 20, "region_id": 10, "physical_map_id": 5}
        for row in self.profiles["profiles"]:
            match = row["match"]
            if any(getattr(context, key) != value for key, value in match.items()):
                continue
            hidden = set(row.get("requiresDiscoveryIds", ())) - set(context.discovered_ids)
            if not hidden:
                candidates.append((sum(precedence.get(key, 1) for key in match), len(match), row["id"], row))
        return max(candidates, default=(0, 0, "", self.profiles["fallbackProfile"]))[3]

    @staticmethod
    def _pick(options, seed):
        if not options:
            return None
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return options[int.from_bytes(digest[:8], "big") % len(options)]

    def plan(self, context, transition_serial=0):
        profile = self._profile(context)
        seed = "|".join((context.physical_map_id, context.region_id or "", profile["id"], str(transition_serial)))
        result = []
        for category_id in sorted(profile["layers"]):
            asset_id = self._pick(profile["layers"][category_id], seed + "|" + category_id)
            if asset_id is None or asset_id not in self.assets:
                asset_id = self.manifest["fallbacks"].get(category_id)
            if asset_id:
                result.append({"categoryId": category_id, "assetId": asset_id, "profileId": profile["id"]})
        return result

    def transition(self, context, now_ms, transition_serial=0):
        planned = self.plan(context, transition_serial)
        desired = {
            x["categoryId"]: x for x in planned
            if self.categories[x["categoryId"]]["kind"] in {"music", "ambience", "loop"}
        }
        commands = []
        for category_id, active in sorted(tuple(self.active.items())):
            if category_id not in desired or desired[category_id]["assetId"] != active["assetId"]:
                commands.append({"op": "fade_out", "assetId": active["assetId"], "durationMs": self.categories[category_id]["fadeOutMs"]})
                del self.active[category_id]
        for category_id, item in sorted(desired.items()):
            if category_id not in self.active:
                self.active[category_id] = item
                commands.append({"op": "fade_in", "assetId": item["assetId"], "durationMs": self.categories[category_id]["fadeInMs"]})
        # Profiles may also request bounded spatial/UI/event cues. They are
        # transients, never loop owners, and use the same cooldown/concurrency
        # path as direct gameplay feedback.
        for item in planned:
            if item["categoryId"] not in desired:
                command = self.one_shot(item["assetId"], now_ms)
                if command["op"] != "suppressed":
                    commands.append(command)
        return commands

    def one_shot(self, asset_id, now_ms):
        asset = self.assets.get(asset_id)
        if not asset:
            return {"op": "fallback", "assetId": None}
        category = self.categories[asset["categoryId"]]
        if now_ms - self.last_played_ms.get(asset_id, -10**12) < category["cooldownMs"]:
            return {"op": "suppressed", "reason": "cooldown"}
        self.transient = [x for x in self.transient if x["endsAtMs"] > now_ms]
        same = [x for x in self.transient if x["categoryId"] == asset["categoryId"]]
        if len(same) >= category["maximumConcurrent"]:
            return {"op": "suppressed", "reason": "concurrency"}
        maximum = self.manifest["budgets"]["maximumActiveChannels"]
        if len(self.active) + len(self.transient) >= maximum:
            lower = [x for x in self.transient if self.categories[x["categoryId"]]["priority"] < category["priority"]]
            if not lower or category["interrupt"] == "never":
                return {"op": "suppressed", "reason": "channel_budget"}
            victim = min(lower, key=lambda x: (self.categories[x["categoryId"]]["priority"], x["startedAtMs"], x["assetId"]))
            self.transient.remove(victim)
        self.last_played_ms[asset_id] = now_ms
        self.transient.append({"assetId": asset_id, "categoryId": asset["categoryId"], "startedAtMs": now_ms, "endsAtMs": now_ms + asset["technical"]["durationMs"]})
        return {"op": "play", "assetId": asset_id}

    def reconstruct(self, context, now_ms, transition_serial=0):
        self.active = {}
        self.transient = []
        self.last_played_ms = {}
        return self.transition(context, now_ms, transition_serial)

    def presentation_snapshot(self):
        return {"active": copy.deepcopy(self.active), "transient": copy.deepcopy(self.transient), "lastPlayedMs": dict(self.last_played_ms)}
