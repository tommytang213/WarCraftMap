"""Scenario-neutral player-use item, merchant, comparison, and ownership rules.

Bulk commodities, warehouses and ship refits intentionally do not enter this module.
All random-looking choices are hashes of authoritative context and refresh epoch.
"""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class PlayerItemError(ValueError): pass


RESEARCH_ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
EQUIPMENT_RESEARCH_CAPACITY = 512


@dataclass(frozen=True)
class StockEntry:
    item_type_id: str
    quantity: int
    price_minor: int


def _ids(rows, domain):
    out = {}
    for row in rows:
        ident = row.get("id")
        if not isinstance(ident, str) or not ident or ident in out:
            raise PlayerItemError(f"{domain}: invalid or duplicate id {ident!r}")
        out[ident] = row
    return out


def validate_catalog(data: Mapping[str, Any], *, bulk_good_ids=()) -> None:
    if data.get("schemaVersion") != 1: raise PlayerItemError("player item schemaVersion must be 1")
    rarities = _ids(data.get("rarities", []), "rarities")
    if sorted(x["rank"] for x in rarities.values()) != list(range(len(rarities))):
        raise PlayerItemError("rarity ranks must be contiguous from zero")
    effects = _ids(data.get("effects", []), "effects")
    sets = _ids(data.get("equipmentSets", []), "equipmentSets")
    merchants = _ids(data.get("merchantArchetypes", []), "merchantArchetypes")
    evidence = _ids(data.get("historicalEvidence", []), "historicalEvidence")
    items = _ids(data.get("items", []), "items")
    bulk_goods = set(bulk_good_ids)
    stat_signatures = {}
    allowed_provenance = {"generic","regional","cultural","polity","profession","quest","set_piece","historical","legendary"}
    allowed_categories = {"equipment","consumable","tool","book_map","artifact"}
    unique_identities = set()
    for item_id, item in items.items():
        required = ("name","category","itemLevel","rarityId","provenance","unique","requirements","enhancement","merchant","comparison")
        if any(k not in item for k in required): raise PlayerItemError(f"item {item_id}: missing release-scale field")
        if item["category"] not in allowed_categories: raise PlayerItemError(f"item {item_id}: invalid player-use category")
        if not isinstance(item["itemLevel"], int) or not 1 <= item["itemLevel"] <= 300: raise PlayerItemError(f"item {item_id}: itemLevel outside 1..300")
        if item["rarityId"] not in rarities: raise PlayerItemError(f"item {item_id}: unknown rarity")
        if item["provenance"].get("kind") not in allowed_provenance: raise PlayerItemError(f"item {item_id}: invalid provenance")
        if not isinstance(item["unique"], bool): raise PlayerItemError(f"item {item_id}: unique must be boolean")
        if item["unique"] and not item["provenance"].get("identityId"): raise PlayerItemError(f"item {item_id}: unique item needs identityId")
        if item["unique"]:
            identity = item["provenance"]["identityId"]
            if identity in unique_identities: raise PlayerItemError(f"item {item_id}: duplicate unique identity {identity}")
            unique_identities.add(identity)
        req=item["requirements"]
        for field in ("technologyIds", "institutionIds"):
            ids = req.get(field, [])
            if (not isinstance(ids, list) or len(ids) > EQUIPMENT_RESEARCH_CAPACITY or
                    any(not isinstance(ident, str) or not RESEARCH_ID.fullmatch(ident) for ident in ids)):
                raise PlayerItemError(f"item {item_id}: {field} must be a bounded array of stable research IDs")
            if len(ids) != len(set(ids)):
                raise PlayerItemError(f"item {item_id}: duplicate {field}")
        if req.get("startYear",1)>req.get("endYear",9999): raise PlayerItemError(f"item {item_id}: invalid era")
        enh=item["enhancement"]
        if not (isinstance(enh.get("maxRank"),int) and 0 <= enh["maxRank"] <= 10): raise PlayerItemError(f"item {item_id}: invalid enhancement bound")
        if not (isinstance(enh.get("maxRestoration"),int) and 0 <= enh["maxRestoration"] <= 5): raise PlayerItemError(f"item {item_id}: invalid restoration bound")
        merchant=item["merchant"]
        if merchant.get("eligible") and not merchant.get("archetypeIds"): raise PlayerItemError(f"item {item_id}: merchant eligible without pool")
        unknown=set(merchant.get("archetypeIds",[]))-set(merchants)
        if unknown: raise PlayerItemError(f"item {item_id}: unknown merchant archetypes {sorted(unknown)}")
        comparison=item["comparison"]
        slots=comparison.get("slotIds",[])
        if item["category"] == "equipment" and not slots: raise PlayerItemError(f"item {item_id}: equipment has no slot")
        if item["category"] != "equipment" and slots and item["category"] != "artifact": raise PlayerItemError(f"item {item_id}: non-equipment uses equipment slot")
        if item_id in bulk_goods or item["name"].lower() in bulk_goods: raise PlayerItemError(f"item {item_id}: bulk good leaked into player catalogue")
        signature=(item["itemLevel"],item["rarityId"],item["category"],tuple(slots),tuple(sorted(comparison.get("majorStats",{}).items())),tuple(sorted(comparison.get("effectIds",[]))))
        if signature in stat_signatures and item["name"] != items[stat_signatures[signature]]["name"]:
            raise PlayerItemError(f"item {item_id}: stat clone of {stat_signatures[signature]}")
        stat_signatures[signature]=item_id
        for effect_id in comparison.get("effectIds",[]):
            if effect_id not in effects: raise PlayerItemError(f"item {item_id}: unknown effect {effect_id}")
        for conditional in comparison.get("conditionalEffects",[]):
            if conditional.get("id") not in effects: raise PlayerItemError(f"item {item_id}: unknown conditional effect")
        set_id=comparison.get("setId")
        if set_id and set_id not in sets: raise PlayerItemError(f"item {item_id}: unknown set {set_id}")
        for evidence_id in item.get("evidenceIds",[]):
            if evidence_id not in evidence: raise PlayerItemError(f"item {item_id}: unknown evidence {evidence_id}")
        if item["provenance"]["kind"] in {"historical","legendary"} and not item.get("evidenceIds"):
            raise PlayerItemError(f"item {item_id}: historical identity lacks evidence")
    for set_id, row in sets.items():
        piece_ids=row.get("itemTypeIds",[])
        if not piece_ids or set(piece_ids)-set(items): raise PlayerItemError(f"set {set_id}: invalid pieces")
        counts=[x["pieceCount"] for x in row.get("thresholds",[])]
        if not counts or counts != sorted(set(counts)) or max(counts)>len(piece_ids): raise PlayerItemError(f"set {set_id}: invalid thresholds")
        for threshold in row["thresholds"]:
            if set(threshold.get("effectIds",[]))-set(effects): raise PlayerItemError(f"set {set_id}: unknown threshold effect")


def validate_equipment_research(data: Mapping[str, Any], technologies, institutions) -> None:
    """Resolve equipment references against the correct authored research kind.

    Call after validate_catalog so malformed/duplicate lists cannot become sets.
    Kept separate from merchant availability for reuse by the live generator.
    """
    for item in data["items"]:
        for field, targets in (("technologyIds", technologies), ("institutionIds", institutions)):
            unknown = set(item["requirements"].get(field, [])) - set(targets)
            if unknown:
                raise PlayerItemError(f"item {item['id']}: unknown {field} {sorted(unknown)}")


def validate_catalog_references(data: Mapping[str,Any], references: Mapping[str,set[str]]) -> None:
    """Validate scenario-owned availability references without coupling the engine to files."""
    validate_catalog(data, bulk_good_ids=references.get("goods", ()))
    mapping=(("regionIds","regions"),("cultureIds","cultures"),("controllerIds","controllers"),
             ("technologyIds","technologies"),("institutionIds","institutions"),
             ("questFlagIds","quests"),("eventFlagIds","events"))
    for item in data["items"]:
        for field,domain in mapping:
            unknown=set(item["requirements"].get(field,[]))-references.get(domain,set())
            if unknown: raise PlayerItemError(f"item {item['id']}: unknown {domain} {sorted(unknown)}")
        unknown=set(item["merchant"].get("settlementIds",[]))-references.get("settlements",set())
        if unknown: raise PlayerItemError(f"item {item['id']}: unknown settlements {sorted(unknown)}")
        if not item["merchant"]["eligible"] and not item["unique"]:
            raise PlayerItemError(f"item {item['id']}: unreachable non-unique item")
        if item["unique"] and not (item["merchant"]["eligible"] or item["requirements"].get("questFlagIds") or item["requirements"].get("eventFlagIds") or item["evidenceIds"]):
            raise PlayerItemError(f"item {item['id']}: unreachable unique item")


def _available(item, archetype_id, context):
    if not item["merchant"]["eligible"] or archetype_id not in item["merchant"]["archetypeIds"]: return False
    req=item["requirements"]; year=context["year"]
    if not req.get("startYear",1)<=year<=req.get("endYear",9999): return False
    for key,ctx in (("technologyIds","technologyIds"),("institutionIds","institutionIds"),("eventFlagIds","eventFlagIds"),("questFlagIds","questFlagIds")):
        if not set(req.get(key,[])) <= set(context.get(ctx,[])): return False
    for key,ctx in (("regionIds","regionId"),("cultureIds","cultureId"),("controllerIds","controllerId"),("settlementIds","settlementId")):
        if req.get(key) and context.get(ctx) not in req[key]: return False
    local=item["merchant"].get("localProductionAny",[])
    if local and not set(local)&set(context.get("localProductionIds",[])): return False
    if item["merchant"].get("requiresTradeAccess") and not context.get("tradeAccess",False): return False
    if context.get("wealth",0)<item["merchant"].get("minimumWealth",0): return False
    settlements=item["merchant"].get("settlementIds",[])
    if settlements and context.get("settlementId") not in settlements: return False
    if item["id"] in set(context.get("scarceItemTypeIds",[])): return False
    return True


def resolve_stock(data: Mapping[str,Any], archetype_id: str, context: Mapping[str,Any], unique_owners: Mapping[str,str]|None=None) -> tuple[StockEntry,...]:
    """Resolve stable stock; refreshEpoch must itself be saved, never wall-clock based."""
    validate_catalog(data); archetypes=_ids(data["merchantArchetypes"],"merchantArchetypes")
    if archetype_id not in archetypes: raise PlayerItemError("unknown merchant archetype")
    for key in ("settlementId","regionId","controllerId","year","refreshEpoch"):
        if key not in context: raise PlayerItemError(f"merchant context missing {key}")
    owned=set((unique_owners or {}).keys()); candidates=[]
    for item in data["items"]:
        identity=item["provenance"].get("identityId")
        if _available(item,archetype_id,context) and not (item["unique"] and identity in owned): candidates.append(item)
    seed="|".join(str(context.get(k,"")) for k in ("campaignSeed","settlementId","controllerId","year","refreshEpoch", "regionId"))+"|"+archetype_id
    def score(item): return hashlib.sha256((seed+"|"+item["id"]).encode()).hexdigest()
    candidates.sort(key=lambda x:(score(x),x["id"]))
    limit=archetypes[archetype_id].get("stockLimit",8); wealth=max(0,int(context.get("wealth",0)))
    result=[]
    for item in candidates[:limit]:
        rarity=_ids(data["rarities"],"rarities")[item["rarityId"]]
        base=item["merchant"]["basePriceMinor"]
        # Small seeded market movement makes a persisted refresh epoch meaningful
        # without introducing save/load rerolls or overwhelming authored prices.
        market_shift=int(score(item)[2:4],16)%5-2
        price=max(1,base*(100+rarity["rank"]*8- min(20,wealth//5)+market_shift)//100)
        quantity=1 if item["unique"] or item["category"]=="equipment" else 1+int(score(item)[:2],16)%3
        result.append(StockEntry(item["id"],quantity,price))
    return tuple(sorted(result,key=lambda x:x.item_type_id))


def compare(data, candidate_id, equipped_id=None, *, enhancement_rank=0, restoration_rank=0, equipped_set_counts=None):
    validate_catalog(data); items=_ids(data["items"],"items"); rarities=_ids(data["rarities"],"rarities")
    candidate=items[candidate_id]; equipped=items.get(equipped_id) if equipped_id else None
    def stats(row): return row["comparison"].get("majorStats",{}) if row else {}
    keys=sorted(set(stats(candidate))|set(stats(equipped)))
    enh=candidate["enhancement"]
    if not 0<=enhancement_rank<=enh["maxRank"] or not 0<=restoration_rank<=enh["maxRestoration"]: raise PlayerItemError("instance improvement exceeds authored bound")
    set_id=candidate["comparison"].get("setId"); count=(equipped_set_counts or {}).get(set_id,0)+(1 if set_id else 0)
    set_row=_ids(data["equipmentSets"],"equipmentSets").get(set_id)
    return {"itemTypeId":candidate_id,"itemLevel":candidate["itemLevel"],"rarity":{"id":candidate["rarityId"],"rank":rarities[candidate["rarityId"]]["rank"]},
      "enhancement":{"rank":enhancement_rank,"maxRank":enh["maxRank"],"restorationRank":restoration_rank,"maxRestoration":enh["maxRestoration"]},
      "majorStats":stats(candidate),"deltas":{k:stats(candidate).get(k,0)-stats(equipped).get(k,0) for k in keys},
      "effectIds":candidate["comparison"].get("effectIds",[]),"conditionalEffects":candidate["comparison"].get("conditionalEffects",[]),
      "set":{"id":set_id,"equippedPieceCount":count,"thresholds":set_row["thresholds"] if set_row else []},"requirements":candidate["requirements"]}


def claim_unique(unique_owners, item, owner_id):
    result=dict(unique_owners); identity=item["provenance"].get("identityId")
    if item["unique"]:
        if identity in result: raise PlayerItemError(f"unique identity already owned: {identity}")
        result[identity]=owner_id
    return result


def migrate_state(state: Mapping[str,Any]) -> dict[str,Any]:
    """Upgrade the player-item authority envelope without persisting derived bonuses."""
    version=state.get("schemaVersion",1)
    if version not in (1,2): raise PlayerItemError(f"unsupported player item state version {version}")
    result=copy.deepcopy(dict(state))
    if version==1:
        for instance in result.get("instances",[]):
            instance.setdefault("enhancementRank",0); instance.setdefault("restorationRank",0)
        result.setdefault("uniqueOwners",{})
        result.setdefault("merchantRefreshEpochs",{})
        result["schemaVersion"]=2
    return result


def validate_state(data: Mapping[str,Any], state: Mapping[str,Any]) -> None:
    validate_catalog(data)
    if state.get("schemaVersion") != 2: raise PlayerItemError("player item state must be migrated to version 2")
    items=_ids(data["items"],"items"); seen=set(); identities={}
    for instance in state.get("instances",[]):
        if instance.get("instanceId") in seen: raise PlayerItemError("duplicate player item instance")
        seen.add(instance.get("instanceId")); item=items.get(instance.get("itemTypeId"))
        if not item: raise PlayerItemError("unknown player item type")
        if not 0<=instance.get("enhancementRank",0)<=item["enhancement"]["maxRank"]: raise PlayerItemError("enhancement exceeds bound")
        if not 0<=instance.get("restorationRank",0)<=item["enhancement"]["maxRestoration"]: raise PlayerItemError("restoration exceeds bound")
        identity=item["provenance"].get("identityId")
        if item["unique"]:
            if identity in identities: raise PlayerItemError("duplicate unique identity")
            identities[identity]=instance.get("ownerId")
    if identities != dict(state.get("uniqueOwners",{})): raise PlayerItemError("unique ownership registry disagrees with instances")


def transact_purchase(stock, inventory, unique_owners, data, *, item_type_id, owner_id, funds_minor, capacity):
    """Atomic pure transaction: failures cannot mutate stock, inventory, or registry."""
    entries={x.item_type_id:x for x in stock}; entry=entries.get(item_type_id)
    if not entry or entry.quantity<1: raise PlayerItemError("item is not in stock")
    if funds_minor<entry.price_minor: raise PlayerItemError("insufficient funds")
    if len(inventory)>=capacity: raise PlayerItemError("personal inventory overflow")
    item=_ids(data["items"],"items")[item_type_id]
    owners=claim_unique(unique_owners,item,owner_id)
    new_stock=tuple(StockEntry(x.item_type_id,x.quantity-1,x.price_minor) if x.item_type_id==item_type_id else x for x in stock if x.item_type_id!=item_type_id or x.quantity>1)
    return {"stock":new_stock,"inventory":tuple(inventory)+(item_type_id,),"uniqueOwners":owners,"fundsMinor":funds_minor-entry.price_minor}


def transact_sale(stock, inventory, unique_owners, data, *, item_type_id, owner_id, funds_minor, price_minor):
    """Atomically sell one personal item; unique identity remains singular in stock."""
    if item_type_id not in inventory: raise PlayerItemError("seller does not own item")
    item=_ids(data["items"],"items")[item_type_id]; new_inventory=list(inventory); new_inventory.remove(item_type_id)
    new_stock=list(stock)
    for index,entry in enumerate(new_stock):
        if entry.item_type_id==item_type_id:
            new_stock[index]=StockEntry(item_type_id,entry.quantity+1,entry.price_minor); break
    else: new_stock.append(StockEntry(item_type_id,1,max(1,price_minor*2)))
    owners=dict(unique_owners)
    if item["unique"]: owners[item["provenance"]["identityId"]]=f"merchant:{owner_id}"
    return {"stock":tuple(sorted(new_stock,key=lambda x:x.item_type_id)),"inventory":tuple(new_inventory),"uniqueOwners":owners,"fundsMinor":funds_minor+price_minor}


def transact_consume(inventory, data, *, item_type_id):
    """Atomically consume one player-use item and expose its authored effects."""
    items=_ids(data["items"],"items"); item=items.get(item_type_id)
    if not item or item["category"] != "consumable": raise PlayerItemError("item is not consumable")
    if item_type_id not in inventory: raise PlayerItemError("consumer does not own item")
    result=list(inventory); result.remove(item_type_id)
    return {"inventory":tuple(result),"effectIds":tuple(item["comparison"].get("effectIds",[])),
            "majorStats":dict(item["comparison"].get("majorStats",{}))}
