"""Player-facing country interaction and negotiated-peace authority.

The runtime deliberately stores stable IDs and scalar campaign facts only.  UI and
Warcraft handles are projections, so diplomacy survives map transitions.
"""
from __future__ import annotations

import copy
import re
from collections.abc import Mapping

PLAYER_DIPLOMACY_WORLD_STATE_KEY = "playerDiplomacyState"
PLAYER_DIPLOMACY_STATE_SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_IRREVERSIBLE = frozenset({"territory", "independence", "vassalage", "payment"})


class PlayerDiplomacyError(ValueError):
    pass


def _id(value, context):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise PlayerDiplomacyError(f"{context}: invalid stable ID {value!r}")
    return value


def _integer(value, context, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int) or (minimum is not None and value < minimum):
        raise PlayerDiplomacyError(f"{context}: invalid integer {value!r}")
    return value


DEFAULT_CLAUSES = {
    "territory": {"duration": False}, "payment": {"duration": False},
    "tribute": {"duration": True}, "independence": {"duration": False},
    "vassalage": {"duration": False}, "trade_access": {"duration": True},
    "military_access": {"duration": True}, "ceasefire": {"duration": True},
    "non_aggression": {"duration": True}, "alliance": {"duration": True},
}


class PlayerDiplomacyRuntime:
    """Discovery-safe country views, government actions, and peace offers."""

    def __init__(self, polities, diplomacy, provinces=None, settlements=None, *,
                 clause_definitions=None, government_capabilities=None):
        self.polities, self.diplomacy = polities, diplomacy
        self.provinces, self.settlements = provinces, settlements
        self.clauses = copy.deepcopy(dict(clause_definitions or DEFAULT_CLAUSES))
        if not self.clauses or any(not _ID.fullmatch(k) or not isinstance(v, Mapping) for k, v in self.clauses.items()):
            raise PlayerDiplomacyError("treaty clause definitions must be stable-ID objects")
        self.capabilities = copy.deepcopy(dict(government_capabilities or {}))
        self.known = set(); self.standing = {}; self.history = []
        self.offers = {}; self.treaties = []; self.cooldowns = {}
        self.rights = {}; self.allegiances = {}; self.next_sequence = 1

    def _polity(self, polity_id):
        view = self.polities.lookup(polity_id)
        if view is None or not view.active:
            raise PlayerDiplomacyError(f"unknown or inactive polity {polity_id!r}")
        return view

    def discover(self, polity_id, *, source="encounter"):
        self._polity(polity_id); _id(source, "discovery source")
        if polity_id not in self.known:
            self.known.add(polity_id)
            self.history.append({"sequence": self.next_sequence, "kind": "polity_discovered",
                                 "polityId": polity_id, "source": source})
            self.next_sequence += 1

    def set_standing(self, polity_id, *, reputation=0, favor=0, service=0):
        self._polity(polity_id)
        self.standing[polity_id] = {"reputation": _integer(reputation, "reputation"),
                                    "favor": _integer(favor, "favor"),
                                    "service": _integer(service, "service", 0)}

    def country_view(self, polity_id, player_state, *, rulers=None, partners=None,
                     history_relevance=None, government_interactions=()):
        """Return only legitimately discovered information for a country screen."""
        self._polity(polity_id)
        if polity_id not in self.known:
            raise PlayerDiplomacyError("country has not been discovered")
        allegiance = player_state.get("currentAllegiancePolityId") or player_state.get("allegiancePolityId")
        origin = player_state.get("originPolityId")
        conflicts = [c for c in self.diplomacy.snapshot()["conflicts"]
                     if c["status"] == "active" and polity_id in c["sides"]["attacker"] + c["sides"]["defender"]]
        known_partners = sorted(p for p in (partners or ()) if p in self.known)
        occupations = [o for o in self.diplomacy.occupations()
                       if o["legalOwnerPolityId"] == polity_id or o["controllerPolityId"] == polity_id]
        relation = "self" if allegiance == polity_id else (self.diplomacy.relation(allegiance, polity_id)
                    if allegiance and self.polities.lookup(allegiance) else "neutral")
        view = self._polity(polity_id)
        return {"polityId": polity_id, "name": view.definition.name, "relation": relation,
                "atWar": relation == "war", "currentAllegiance": allegiance == polity_id,
                "originRelevance": "origin" if origin == polity_id else (history_relevance or {}).get(polity_id),
                "standing": copy.deepcopy(self.standing.get(polity_id, {"reputation": 0, "favor": 0, "service": 0})),
                "government": copy.deepcopy((rulers or {}).get(polity_id)),
                "wars": copy.deepcopy(conflicts), "knownPartners": known_partners,
                "occupations": copy.deepcopy(occupations),
                "availableInteractions": sorted(set(government_interactions))}

    def government_action(self, action, polity_id, player_state, *, eligible=False, reward=None):
        """Validate common government interactions; domain systems commit rewards."""
        allowed = {"serve", "change_allegiance", "request_reward", "request_access", "negotiate"}
        if action not in allowed: raise PlayerDiplomacyError("unsupported government interaction")
        self._polity(polity_id)
        if polity_id not in self.known: raise PlayerDiplomacyError("country has not been discovered")
        if action in {"serve", "change_allegiance", "request_reward", "request_access"} and not eligible:
            raise PlayerDiplomacyError("government requirements are not met")
        result = copy.deepcopy(dict(player_state))
        if action == "change_allegiance": result["currentAllegiancePolityId"] = polity_id
        if action == "request_access": self.rights.setdefault(polity_id, set()).add("government_access")
        event = {"sequence": self.next_sequence, "kind": action, "polityId": polity_id}
        if reward is not None: event["reward"] = copy.deepcopy(reward)
        self.history.append(event); self.next_sequence += 1
        return result

    def _territory(self, kind, ident):
        runtime = self.provinces if kind == "province" else self.settlements if kind == "settlement" else None
        entity = runtime.lookup(ident) if runtime else None
        if entity is None: raise PlayerDiplomacyError(f"unknown treaty territory {ident!r}")
        return entity

    def _validate_terms(self, conflict, terms, authority):
        if not isinstance(terms, list) or not terms: raise PlayerDiplomacyError("peace offer needs explicit terms")
        result=[]; seen=set(); participants=set(conflict["sides"]["attacker"] + conflict["sides"]["defender"])
        for raw in terms:
            if not isinstance(raw, Mapping): raise PlayerDiplomacyError("treaty terms must be objects")
            term=copy.deepcopy(dict(raw)); kind=term.get("kind")
            if kind not in self.clauses: raise PlayerDiplomacyError(f"unsupported treaty clause {kind!r}")
            grantor=_id(term.get("grantorPolityId"), "grantor"); beneficiary=_id(term.get("beneficiaryPolityId"), "beneficiary")
            if grantor == beneficiary or grantor not in participants or beneficiary not in participants:
                raise PlayerDiplomacyError("treaty parties must be opposing conflict participants")
            opposite = any(grantor in conflict["sides"][s] and beneficiary in conflict["sides"]["defender" if s=="attacker" else "attacker"] for s in ("attacker","defender"))
            if not opposite: raise PlayerDiplomacyError("treaty parties must be on opposing sides")
            key=(kind, grantor, beneficiary, term.get("entityKind"), term.get("entityId"))
            if key in seen: raise PlayerDiplomacyError("duplicate treaty term")
            seen.add(key)
            if kind == "territory":
                entity=self._territory(term.get("entityKind"), term.get("entityId"))
                occupied = entity.controller_polity_id == beneficiary
                if entity.legal_owner_polity_id != grantor or not (occupied or entity.controller_polity_id == grantor):
                    raise PlayerDiplomacyError("grantor neither owns nor controls ceded territory")
            elif kind in {"payment", "tribute"}:
                amount=_integer(term.get("amount"), "payment amount", 1)
                if amount > authority.get("treasuries", {}).get(grantor, 0):
                    raise PlayerDiplomacyError("grantor cannot fund treaty payment")
            if self.clauses[kind].get("duration"):
                _integer(term.get("durationDays"), "clause duration", 1)
            if kind in {"trade_access", "military_access", "vassalage", "alliance", "independence"}:
                if kind not in set(authority.get("capabilities", {}).get(grantor, self.capabilities.get(grantor, ()))):
                    raise PlayerDiplomacyError("government cannot grant requested right")
            result.append(term)
        return result

    def propose_peace(self, offer_id, conflict_id, proposer, recipient, terms, *, day, authority,
                      expires_after=30, initiated_by="player"):
        _id(offer_id,"offer id"); self._polity(proposer); self._polity(recipient)
        if offer_id in self.offers: raise PlayerDiplomacyError("duplicate peace offer")
        if day < self.cooldowns.get((proposer,recipient), -1): raise PlayerDiplomacyError("peace negotiation is on cooldown")
        conflict=self.diplomacy.conflict(conflict_id)
        if not conflict or conflict["status"] != "active": raise PlayerDiplomacyError("peace requires an active conflict")
        validated=self._validate_terms(conflict, terms, authority)
        offer={"id":offer_id,"conflictId":conflict_id,"proposerPolityId":proposer,
               "recipientPolityId":recipient,"initiatedBy":initiated_by,"createdDay":_integer(day,"day",0),
               "expiresDay":day+_integer(expires_after,"expiry",1),"status":"pending","terms":validated}
        self.offers[offer_id]=offer
        self.history.append({"sequence":self.next_sequence,"kind":"peace_offered","offerId":offer_id})
        self.next_sequence+=1; return copy.deepcopy(offer)

    def evaluate_offer(self, offer_id, campaign):
        """Deterministic bounded explanation; historical pressure is only a small bias."""
        offer=self.offers.get(offer_id)
        if not offer or offer["status"] != "pending": raise PlayerDiplomacyError("offer is not pending")
        r=offer["recipientPolityId"]; p=offer["proposerPolityId"]
        state=campaign.get("polities",{}).get(r,{})
        score = (state.get("warExhaustion",0) + state.get("casualtyPressure",0) + state.get("economicCost",0))
        score += max(-50,min(50,campaign.get("relativeStrength",{}).get(p,0)))
        score += campaign.get("occupiedValue",{}).get(p,0) - campaign.get("occupiedValue",{}).get(r,0)
        score -= state.get("continuingThreat",0) + state.get("strategicRisk",0)
        score += campaign.get("alliancePressure",{}).get(r,0) + campaign.get("diplomaticHistory",{}).get(r,0)
        score += campaign.get("warGoalPressure",{}).get(r,0) + campaign.get("reputation",{}).get(p,0) // 4
        # Positive is value received by the deciding government; negative is cost.
        for term in offer["terms"]:
            value=campaign.get("termValues",{}).get(term["kind"], term.get("amount",0)//10)
            score += value if term["beneficiaryPolityId"]==r else -value
        score += max(-10,min(10,campaign.get("historicalPressure",{}).get(r,0)))
        reasons=[]
        if state.get("warExhaustion",0)>=50: reasons.append("Our country is exhausted by the war.")
        if campaign.get("occupiedValue",{}).get(p,0)>campaign.get("occupiedValue",{}).get(r,0): reasons.append("The current occupations favor peace.")
        if state.get("continuingThreat",0)>=40: reasons.append("The proposal leaves a serious continuing threat.")
        if state.get("treasury",0)<state.get("economicCost",0): reasons.append("Continuing the war is becoming unaffordable.")
        if not reasons: reasons.append("The balance of the war does not justify these terms." if score < 50 else "The terms reflect the present balance of the war.")
        return {"acceptable":score>=50,"reasons":reasons[:3]}

    def respond(self, offer_id, accept, *, day, authority, confirmed=False):
        offer=self.offers.get(offer_id)
        if not offer or offer["status"]!="pending": raise PlayerDiplomacyError("offer is not pending")
        if day > offer["expiresDay"]: offer["status"]="expired"; raise PlayerDiplomacyError("peace offer has expired")
        conflict=self.diplomacy.conflict(offer["conflictId"])
        terms=self._validate_terms(conflict, offer["terms"], authority)
        if accept and any(t["kind"] in _IRREVERSIBLE for t in terms) and not confirmed:
            raise PlayerDiplomacyError("confirmation required for irreversible treaty terms")
        if not accept:
            offer["status"]="rejected"; self.cooldowns[(offer["proposerPolityId"],offer["recipientPolityId"])]=day+7
            self.history.append({"sequence":self.next_sequence,"kind":"peace_rejected","offerId":offer_id});self.next_sequence+=1
            return copy.deepcopy(offer)
        territorial=[]
        for occupation in self.diplomacy.occupations(offer["conflictId"]):
            matching=next((t for t in terms if t["kind"]=="territory" and t.get("entityKind")==occupation["entityKind"] and t.get("entityId")==occupation["entityId"]),None)
            owner=matching["beneficiaryPolityId"] if matching else occupation["legalOwnerPolityId"]
            territorial.append({"entityKind":occupation["entityKind"],"entityId":occupation["entityId"],"legalOwnerPolityId":owner,"controllerPolityId":owner})
        self.diplomacy.conclude_peace(offer["conflictId"],territorial_outcomes=territorial)
        for term in terms:
            if term["kind"]=="payment":
                treasuries=authority["treasuries"];amount=term["amount"]
                treasuries[term["grantorPolityId"]]-=amount
                treasuries[term["beneficiaryPolityId"]]=treasuries.get(term["beneficiaryPolityId"],0)+amount
        offer["status"]="accepted"; treaty={"id":"treaty_"+offer_id,"offerId":offer_id,"acceptedDay":day,"terms":copy.deepcopy(terms)}
        self.treaties.append(treaty); self.history.append({"sequence":self.next_sequence,"kind":"peace_accepted","offerId":offer_id})
        self.next_sequence+=1; return copy.deepcopy(treaty)

    def snapshot(self):
        return {"schemaVersion":1,"nextSequence":self.next_sequence,"knownPolityIds":sorted(self.known),
                "standing":[{"polityId":p,**self.standing[p]} for p in sorted(self.standing)],
                "offers":[copy.deepcopy(self.offers[x]) for x in sorted(self.offers)],"treaties":copy.deepcopy(self.treaties),
                "cooldowns":[{"firstPolityId":a,"secondPolityId":b,"untilDay":d} for (a,b),d in sorted(self.cooldowns.items())],
                "rights":[{"polityId":p,"rights":sorted(v)} for p,v in sorted(self.rights.items())],"history":copy.deepcopy(self.history)}

    def restore(self, candidate):
        if not isinstance(candidate,Mapping) or candidate.get("schemaVersion")!=1: raise PlayerDiplomacyError("player diplomacy state schemaVersion must be 1")
        required=("knownPolityIds","standing","offers","treaties","cooldowns","rights","history")
        if any(not isinstance(candidate.get(k),list) for k in required): raise PlayerDiplomacyError("invalid player diplomacy state arrays")
        known=set(candidate["knownPolityIds"])
        for p in known:self._polity(p)
        offers={o.get("id"):copy.deepcopy(dict(o)) for o in candidate["offers"] if isinstance(o,Mapping)}
        if len(offers)!=len(candidate["offers"]): raise PlayerDiplomacyError("duplicate or malformed offers")
        standing={r["polityId"]:{k:_integer(r[k],k,0 if k=="service" else None) for k in ("reputation","favor","service")} for r in candidate["standing"]}
        cooldowns={(r["firstPolityId"],r["secondPolityId"]):_integer(r["untilDay"],"cooldown",0) for r in candidate["cooldowns"]}
        rights={r["polityId"]:set(r["rights"]) for r in candidate["rights"]}
        next_sequence=_integer(candidate.get("nextSequence"),"next sequence",1)
        if any(x.get("sequence")!=i+1 for i,x in enumerate(candidate["history"])) or next_sequence!=len(candidate["history"])+1:
            raise PlayerDiplomacyError("invalid diplomacy history ordering")
        self.known,self.offers,self.standing,self.cooldowns,self.rights=known,offers,standing,cooldowns,rights
        self.treaties=copy.deepcopy(candidate["treaties"]);self.history=copy.deepcopy(candidate["history"]);self.next_sequence=next_sequence


class PlayerDiplomacySaveAdapter:
    def __init__(self,runtime,world_state): self.runtime,self.world_state=runtime,copy.deepcopy(dict(world_state))
    def capture_world(self):
        result=copy.deepcopy(self.world_state);result[PLAYER_DIPLOMACY_WORLD_STATE_KEY]=self.runtime.snapshot();return result
    def migrate_legacy_world(self,candidate):
        result=copy.deepcopy(dict(candidate));result.setdefault(PLAYER_DIPLOMACY_WORLD_STATE_KEY,self.runtime.snapshot());return result
    def validate_world(self,candidate):
        probe=copy.deepcopy(self.runtime.snapshot());self.runtime.restore(candidate[PLAYER_DIPLOMACY_WORLD_STATE_KEY]);self.runtime.restore(probe)
    def reconstruct(self,candidate):self.validate_world(candidate);return copy.deepcopy(candidate[PLAYER_DIPLOMACY_WORLD_STATE_KEY])
    def activate(self,candidate,reconstructed):self.runtime.restore(reconstructed);self.world_state=copy.deepcopy(dict(candidate))
