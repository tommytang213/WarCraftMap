"""Authoritative, scenario-neutral piracy, privateering and free-polity runtime.

Warcraft objects are deliberately absent.  Prize IDs, cargo and territorial IDs
refer to records owned by the naval/economy/settlement layers; this module owns
only the legal decision, rewards, notoriety and world response to those acts.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping

PIRACY_WORLD_STATE_KEY = "piracyState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class PiracyError(ValueError):
    pass


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise PiracyError(f"{label}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PiracyError(f"{label}: must be an integer >= {minimum}")
    return value


def _index(rows: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise PiracyError(f"{label}: must be an array")
    out = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise PiracyError(f"{label}: entries must be objects")
        ident = _id(row.get("id"), f"{label}.id")
        if ident in out:
            raise PiracyError(f"{label}: duplicate ID {ident!r}")
        out[ident] = copy.deepcopy(dict(row))
    return out


@dataclass(frozen=True)
class PiracyResult:
    event: dict[str, Any]
    cargo: tuple[dict[str, Any], ...]
    money_minor: int
    vessel_outcome: str
    lawful_privateering: bool


class PiracyRuntime:
    """Deterministic campaign authority for piracy and privateering.

    Callers validate physical boarding/combat and commit returned cargo/money to
    the economy layer.  A globally unique action ID makes retries idempotent.
    """
    def __init__(self, definitions: Mapping[str, Any]):
        if not isinstance(definitions, Mapping) or definitions.get("schemaVersion") != 1:
            raise PiracyError("piracy definitions schemaVersion must be 1")
        self.definitions = copy.deepcopy(dict(definitions))
        self.havens = _index(definitions.get("havens", []), "havens")
        self.governments = _index(definitions.get("governmentForms", []), "governmentForms")
        self.contracts = _index(definitions.get("contractTypes", []), "contractTypes")
        self.rules = copy.deepcopy(definitions.get("rules", {}))
        for key in ("repeatTargetCooldownTicks", "foundingNotoriety", "foundingWealthMinor", "foundingPrizes"):
            _integer(self.rules.get(key), f"rules.{key}")
        self.players: dict[str, dict[str, Any]] = {}
        self.commissions: dict[str, dict[str, Any]] = {}
        self.polities: dict[str, dict[str, Any]] = {}
        self.pressure: dict[str, dict[str, int]] = {}
        self.processed: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.next_sequence = 1

    def _player(self, player_id: str) -> dict[str, Any]:
        _id(player_id, "playerId")
        return self.players.setdefault(player_id, {"notoriety": 0, "outlaw": False,
            "piracyWealthMinor": 0, "prizesTaken": 0, "bountyMinor": 0,
            "lastTargets": {}, "havenStanding": {}, "activeContracts": {}, "completedContractIds": [], "polityId": None})

    def _emit(self, kind: str, **fields: Any) -> dict[str, Any]:
        event = {"sequence": self.next_sequence, "kind": kind, **copy.deepcopy(fields)}
        self.next_sequence += 1; self.events.append(event)
        return copy.deepcopy(event)

    def issue_commission(self, commission_id: str, *, player_id: str, issuer_polity_id: str,
                         target_polity_ids: list[str], issued_tick: int, expires_tick: int,
                         reward_permille: int = 250) -> dict[str, Any]:
        ident = _id(commission_id, "commissionId")
        if ident in self.commissions: raise PiracyError("duplicate commission")
        _id(issuer_polity_id, "issuerPolityId"); _integer(issued_tick, "issuedTick")
        if _integer(expires_tick, "expiresTick") <= issued_tick: raise PiracyError("commission must expire after issue")
        targets = sorted({_id(x, "targetPolityId") for x in target_polity_ids})
        if not targets or issuer_polity_id in targets: raise PiracyError("commission requires foreign targets")
        row = {"id": ident, "playerId": _id(player_id, "playerId"), "issuerPolityId": issuer_polity_id,
               "targetPolityIds": targets, "issuedTick": issued_tick, "expiresTick": expires_tick,
               "rewardPermille": _integer(reward_permille, "rewardPermille"), "status": "active"}
        self.commissions[ident] = row; self._player(player_id)
        self._emit("commission_issued", commissionId=ident, playerId=player_id, issuerPolityId=issuer_polity_id)
        return copy.deepcopy(row)

    def revoke_commission(self, commission_id: str, tick: int, reason: str = "revoked") -> dict[str, Any]:
        row = self.commissions.get(commission_id)
        if row is None or row["status"] != "active": raise PiracyError("commission is not active")
        row["status"] = "revoked"; row["endedTick"] = _integer(tick, "tick"); row["endReason"] = reason
        return self._emit("commission_revoked", commissionId=commission_id, reason=reason)

    def _commission(self, player_id: str, victim_polity_id: str, tick: int, commission_id: str | None):
        if commission_id is None: return None
        row = self.commissions.get(commission_id)
        if row is None or row["playerId"] != player_id: raise PiracyError("invalid commission")
        if row["status"] != "active" or tick >= row["expiresTick"]:
            if row["status"] == "active": row["status"] = "expired"; row["endedTick"] = tick
            raise PiracyError("commission is expired or revoked")
        if victim_polity_id not in row["targetPolityIds"]: raise PiracyError("target is outside commission")
        return row

    def resolve_prize(self, action: Mapping[str, Any]) -> PiracyResult:
        """Resolve one validated boarding/plunder/coastal raid atomically."""
        action_id = _id(action.get("id"), "action.id")
        if action_id in self.processed:
            saved = self.processed[action_id]
            return PiracyResult(copy.deepcopy(saved["event"]), tuple(copy.deepcopy(saved["cargo"])), saved["moneyMinor"], saved["vesselOutcome"], saved["lawfulPrivateering"])
        player_id = _id(action.get("playerId"), "playerId"); target_id = _id(action.get("targetId"), "targetId")
        victim = _id(action.get("victimPolityId"), "victimPolityId"); region = _id(action.get("regionId"), "regionId")
        tick = _integer(action.get("tick"), "tick"); kind = action.get("targetKind")
        if kind not in {"merchant_ship", "military_ship", "coastal_target"}: raise PiracyError("ineligible piracy target")
        if not action.get("authorityValidated", False): raise PiracyError("war/crime authority was not validated")
        outcome = action.get("vesselOutcome", "release")
        allowed = {"merchant_ship": {"capture", "scuttle", "release"}, "military_ship": {"capture", "scuttle", "release"}, "coastal_target": {"release"}}
        if outcome not in allowed[kind]: raise PiracyError("invalid vessel outcome")
        player = self._player(player_id); cooldown = self.rules["repeatTargetCooldownTicks"]
        if tick < player["lastTargets"].get(target_id, -cooldown) + cooldown: raise PiracyError("target is exhausted; anti-farming cooldown active")
        cargo = []
        for line in action.get("cargo", []):
            gid = _id(line.get("goodId"), "cargo.goodId"); qty = _integer(line.get("quantityUnits"), "cargo.quantityUnits", 1)
            cargo.append({"goodId": gid, "quantityUnits": qty})
        money = _integer(action.get("moneyMinor", 0), "moneyMinor")
        prisoners = _integer(action.get("prisoners", 0), "prisoners")
        commission = self._commission(player_id, victim, tick, action.get("commissionId"))
        lawful = commission is not None
        severity = 2 + (2 if kind == "military_ship" else 0) + (2 if kind == "coastal_target" else 0) + (1 if outcome == "scuttle" else 0)
        reward = money + money * (commission["rewardPermille"] if commission else 0) // 1000
        player["lastTargets"][target_id] = tick; player["piracyWealthMinor"] += reward
        player["prizesTaken"] += 1
        if lawful:
            notoriety_delta = max(1, severity // 3); relation_effect = {victim: -severity * 2, commission["issuerPolityId"]: severity}
        else:
            notoriety_delta = severity; relation_effect = {victim: -severity * 4}; player["outlaw"] = True
            player["bountyMinor"] += severity * self.rules.get("bountyPerNotorietyMinor", 100)
        player["notoriety"] += notoriety_delta
        regional = self.pressure.setdefault(region, {"piracy": 0, "lossesMinor": 0})
        regional["piracy"] += severity; regional["lossesMinor"] += money
        event = self._emit("prize_resolved", actionId=action_id, playerId=player_id, targetId=target_id,
            targetKind=kind, victimPolityId=victim, regionId=region, lawfulPrivateering=lawful,
            commissionId=commission["id"] if commission else None, cargo=copy.deepcopy(cargo), moneyMinor=reward,
            prisoners=prisoners, prisonerOutcome=action.get("prisonerOutcome", "release"), vesselOutcome=outcome,
            notorietyDelta=notoriety_delta, relationEffects=relation_effect)
        stored = {"event": event, "cargo": cargo, "moneyMinor": reward, "vesselOutcome": outcome, "lawfulPrivateering": lawful}
        self.processed[action_id] = copy.deepcopy(stored)
        return PiracyResult(event, tuple(cargo), reward, outcome, lawful)

    def use_haven(self, player_id: str, haven_id: str, service_id: str, *, tick: int, amount_minor: int = 0) -> dict[str, Any]:
        player = self._player(player_id); haven = self.havens.get(haven_id)
        if haven is None or service_id not in haven.get("serviceIds", []): raise PiracyError("haven service is unavailable")
        minimum = int(haven.get("minimumNotoriety", 0))
        if player["notoriety"] < minimum: raise PiracyError("insufficient pirate notoriety")
        if player.get("polityId") and service_id == "fence": pass
        event = self._emit("haven_service_used", playerId=player_id, havenId=haven_id, serviceId=service_id,
                           tick=_integer(tick, "tick"), amountMinor=_integer(amount_minor, "amountMinor"))
        player["havenStanding"][haven_id] = player["havenStanding"].get(haven_id, 0) + 1
        return event

    def accept_contract(self, contract_id: str, *, player_id: str, contract_type_id: str,
                        haven_id: str, target_id: str, expires_tick: int) -> dict[str, Any]:
        player = self._player(player_id); ident = _id(contract_id, "contractId")
        if contract_type_id not in self.contracts or haven_id not in self.havens: raise PiracyError("unknown contract type or haven")
        if ident in player["activeContracts"] or ident in player["completedContractIds"]: raise PiracyError("duplicate contract")
        row = {"id": ident, "contractTypeId": contract_type_id, "havenId": haven_id,
               "targetId": _id(target_id, "targetId"), "expiresTick": _integer(expires_tick, "expiresTick")}
        player["activeContracts"][ident] = row
        self._emit("pirate_contract_accepted", playerId=player_id, contractId=ident, contractTypeId=contract_type_id)
        return copy.deepcopy(row)

    def complete_contract(self, contract_id: str, *, player_id: str, tick: int,
                          reward_minor: int, target_validated: bool) -> dict[str, Any]:
        player = self._player(player_id); row = player["activeContracts"].get(contract_id)
        if row is None: raise PiracyError("contract is not active")
        tick = _integer(tick, "tick")
        if tick >= row["expiresTick"] or not target_validated: raise PiracyError("contract target or expiry is invalid")
        reward = _integer(reward_minor, "rewardMinor"); player["piracyWealthMinor"] += reward
        del player["activeContracts"][contract_id]; player["completedContractIds"].append(contract_id)
        return self._emit("pirate_contract_completed", playerId=player_id, contractId=contract_id, rewardMinor=reward)

    def found_polity(self, polity_id: str, *, player_id: str, government_form_id: str, name: str,
                     title: str, capital_settlement_id: str, territory_ids: list[str], tick: int) -> dict[str, Any]:
        ident = _id(polity_id, "polityId"); player = self._player(player_id)
        if ident in self.polities or player["polityId"] is not None: raise PiracyError("pirate polity already exists")
        if government_form_id not in self.governments: raise PiracyError("unknown government form")
        if player["notoriety"] < self.rules["foundingNotoriety"] or player["piracyWealthMinor"] < self.rules["foundingWealthMinor"] or player["prizesTaken"] < self.rules["foundingPrizes"]:
            raise PiracyError("pirate polity founding conditions are not met")
        territories = sorted({_id(x, "territoryId") for x in territory_ids})
        capital = _id(capital_settlement_id, "capitalSettlementId")
        if not territories or capital not in territories: raise PiracyError("durable controlled capital territory is required")
        if not isinstance(name, str) or not name.strip() or not isinstance(title, str) or not title.strip(): raise PiracyError("polity name and title are required")
        row = {"id": ident, "founderPlayerId": player_id, "governmentFormId": government_form_id,
               "name": name.strip(), "rulerTitle": title.strip(), "capitalSettlementId": capital,
               "territoryIds": territories, "foundedTick": _integer(tick, "tick"), "recognition": {},
               "status": "independent", "ordinarySystemsEnabled": True}
        self.polities[ident] = row; player["polityId"] = ident; player["outlaw"] = False
        self._emit("pirate_polity_founded", polityId=ident, playerId=player_id, capitalSettlementId=capital)
        return copy.deepcopy(row)

    def set_recognition(self, polity_id: str, country_id: str, status: str, *, tick: int) -> dict[str, Any]:
        if status not in {"hostile", "unrecognized", "tolerated", "recognized", "allied", "embargoed", "vassal"}: raise PiracyError("invalid recognition status")
        polity = self.polities.get(polity_id)
        if polity is None: raise PiracyError("unknown pirate polity")
        country = _id(country_id, "countryId"); polity["recognition"][country] = status
        return self._emit("pirate_polity_recognition_changed", polityId=polity_id, countryId=country, status=status, tick=_integer(tick, "tick"))

    def world_response(self, region_id: str, *, naval_strength: int = 0, treaty_pressure: int = 0,
                       relation_hostility: int = 0, current_wars: int = 0) -> dict[str, int]:
        row = self.pressure.get(region_id, {"piracy": 0, "lossesMinor": 0}); p = row["piracy"]
        strength = _integer(naval_strength, "navalStrength"); treaty = _integer(treaty_pressure, "treatyPressure")
        hostility = _integer(relation_hostility, "relationHostility"); wars = _integer(current_wars, "currentWars")
        capacity = max(0, strength - wars * 10)
        return {"shippingRiskPermille": min(900, p * 20), "pricePressurePermille": min(600, p * 12),
                "escortStrength": min(capacity, p * 2), "patrolStrength": min(capacity, p * 3),
                "convoyChancePermille": min(950, p * 25), "portRestrictionLevel": min(3, p // 10),
                "expeditionPressure": min(1000, p * 15 + treaty + hostility + row["lossesMinor"] // 100),
                "questPressure": min(1000, p * 10)}

    def advance(self, tick: int, *, decay: int = 1) -> None:
        tick = _integer(tick, "tick"); decay = _integer(decay, "decay")
        for row in self.commissions.values():
            if row["status"] == "active" and tick >= row["expiresTick"]: row["status"] = "expired"; row["endedTick"] = tick
        for row in self.pressure.values(): row["piracy"] = max(0, row["piracy"] - decay)

    def snapshot(self) -> dict[str, Any]:
        return {"schemaVersion": 1, "nextEventSequence": self.next_sequence, "players": copy.deepcopy(self.players),
                "commissions": [copy.deepcopy(self.commissions[x]) for x in sorted(self.commissions)],
                "piratePolities": [copy.deepcopy(self.polities[x]) for x in sorted(self.polities)],
                "regionalPressure": copy.deepcopy(self.pressure), "processedActions": copy.deepcopy(self.processed),
                "events": copy.deepcopy(self.events)}

    def restore(self, candidate: Mapping[str, Any]) -> None:
        probe = PiracyRuntime(self.definitions)
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != 1: raise PiracyError("piracy state schemaVersion must be 1")
        probe.players = copy.deepcopy(dict(candidate.get("players", {})))
        probe.commissions = _index(candidate.get("commissions", []), "commissions")
        probe.polities = _index(candidate.get("piratePolities", []), "piratePolities")
        probe.pressure = copy.deepcopy(dict(candidate.get("regionalPressure", {})))
        probe.processed = copy.deepcopy(dict(candidate.get("processedActions", {})))
        probe.events = copy.deepcopy(list(candidate.get("events", [])))
        probe.next_sequence = _integer(candidate.get("nextEventSequence"), "nextEventSequence", 1)
        self.players, self.commissions, self.polities, self.pressure = probe.players, probe.commissions, probe.polities, probe.pressure
        self.processed, self.events, self.next_sequence = probe.processed, probe.events, probe.next_sequence


class PiracySaveAdapter:
    def __init__(self, runtime: PiracyRuntime, world_state: Mapping[str, Any]): self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))
    def capture_world(self):
        out = copy.deepcopy(self.world_state); out[PIRACY_WORLD_STATE_KEY] = self.runtime.snapshot(); return out
    def migrate_legacy_world(self, candidate):
        out = copy.deepcopy(dict(candidate)); out.setdefault(PIRACY_WORLD_STATE_KEY, PiracyRuntime(self.runtime.definitions).snapshot()); return out
    def validate_world(self, candidate):
        probe = PiracyRuntime(self.runtime.definitions); probe.restore(candidate[PIRACY_WORLD_STATE_KEY])
    def reconstruct(self, candidate): self.validate_world(candidate); return copy.deepcopy(candidate[PIRACY_WORLD_STATE_KEY])
    def activate(self, candidate, reconstructed): self.runtime.restore(reconstructed); self.world_state = copy.deepcopy(dict(candidate))
