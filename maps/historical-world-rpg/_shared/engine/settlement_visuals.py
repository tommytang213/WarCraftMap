"""Transient settlement visuals derived from stable authoritative state."""
from __future__ import annotations
import copy

class SettlementVisualRuntimeError(ValueError): pass

class SettlementVisualRuntime:
    """Headless resolver; Warcraft objects are replaceable representations only."""
    def __init__(self, document):
        self.document=copy.deepcopy(document)
        self.sets={x["id"]:x for x in document["visualSets"]}
        self.assignments={x["settlementId"]:x for x in document["settlementAssignments"]}
        self.active={}

    def resolve(self, settlement_id, *, controller_id, year=None, growth="city", destroyed_roles=()):
        row=self.assignments.get(settlement_id)
        if row is None: raise SettlementVisualRuntimeError("unknown settlement")
        visual_set=self.sets[row["visualSetId"]]
        if year is None:
            year = min(x["fromYear"] for x in visual_set["periodVariants"])
        periods=[x for x in visual_set["periodVariants"] if x["fromYear"] <= year <= x["toYear"]]
        if not periods: raise SettlementVisualRuntimeError("unsupported visual period")
        if growth not in visual_set["densityVariants"]: raise SettlementVisualRuntimeError("unknown growth variant")
        omitted=set(destroyed_roles); objects=[]
        for role in row["requiredVisualRoles"]:
            if role in omitted: continue
            visual=next(x for x in visual_set["roleVisuals"] if x["role"]==role)
            objects.append({"stableObjectId":f"{settlement_id}__{role}", "role":role,
                "assetId":visual["assetId"], "scale":visual["scale"], "tintProfile":visual["tintProfile"],
                "teamColor":controller_id if role in {"city_core","defense"} else "neutral_civilian",
                "destructible":visual["destructible"], "invulnerable":visual["invulnerable"]})
        return {"settlementId":settlement_id,"controllerId":controller_id,"periodVariantId":periods[0]["id"],
            "growthVariant":growth,"density":visual_set["densityVariants"][growth],"objects":objects}

    def reconstruct(self, settlement_id, **state):
        representation=self.resolve(settlement_id,**state)
        self.active[settlement_id]=copy.deepcopy(representation)
        return representation

    def lose_representation(self, settlement_id): self.active.pop(settlement_id,None)
