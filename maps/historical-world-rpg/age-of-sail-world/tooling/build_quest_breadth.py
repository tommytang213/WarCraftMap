#!/usr/bin/env python3
"""One-shot deterministic authoring helper for the Phase 8 quest catalogues.

The checked-in JSON is authoritative at runtime. This helper keeps the large,
explicit catalogues reproducible and reviewable; it is not invoked by gameplay.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGIONS={
 "europe":("European","lisbon"), "africa":("African","timbuktu"),
 "middle_east_india":("Middle Eastern and Indian","calicut"),
 "southeast_asia":("Southeast Asian","malacca"), "east_asia":("East Asian","hangzhou"),
 "americas_caribbean":("American and Caribbean","cusco"), "pacific":("Pacific","honolulu_anchorage"),
}
THEMES=[
 ("harbor_charters","Harbor Charters","Reconcile old harbor privileges with the authority that now keeps the waterfront.","Inspect the surviving charter seals","Hear merchants and waterfront households","Record a settlement that remains usable after control changes","administration"),
 ("grain_measure","The Honest Measure","Trace unequal grain measures before shortage turns bargaining into unrest.","Compare market weights","Follow the disputed consignments","Publish a bounded remedy with the current magistrate","event_linked"),
 ("pilots_memory","The Pilots' Memory","Preserve route knowledge held by pilots whose familiar coast is changing.","Gather independent sailing accounts","Test the disputed bearing without revealing unknown waters","Deposit a corrected route record","regional"),
 ("border_witnesses","Witnesses at the Border","Establish what happened at a frontier crossing without presuming either claimant is truthful.","Interview travelers separately","Inspect the crossing and supply traces","Broker testimony acceptable to successor authorities","polity"),
 ("mint_and_market","Mint and Market","Keep trusted exchange possible while clipped coin and rival standards circulate.","Sample coins from distinct trades","Identify the source of the false standard","Agree a temporary market reckoning","polity"),
 ("river_soundings","Soundings After Flood","Restore a river approach after floodwater moved channels and stranded trade.","Take safe soundings","Mark hazards at earned precision","Deliver a revised approach to local pilots","regional"),
 ("archive_in_exile","The Archive in Exile","Recover civic records dispersed when their custodians fled or changed allegiance.","Locate two independent record caches","Authenticate the civic copies","Return them to a lawful or community custodian","event_linked"),
 ("caravan_compact","Compact of the Road","Repair a caravan compact after tolls, escorts, and wells ceased to match its promises.","Audit the route obligations","Negotiate with current road keepers","Escort the first journey under revised terms","regional"),
 ("garrison_accounts","The Garrison Accounts","Separate missing military stores from losses honestly incurred defending the town.","Inventory stores and muster rolls","Investigate contradictory receipts","Resolve restitution or exoneration","polity"),
 ("healers_exchange","The Healers' Exchange","Bring practitioners together around an outbreak without erasing their distinct knowledge.","Collect local observations","Secure scarce clean supplies","Establish a temporary treatment station","personal"),
 ("shipwreck_claims","Claims of the Wreck","Judge competing claims to wreckage while rescuing survivors and preserving evidence.","Search the reported shore","Recover survivors and marked cargo","Settle salvage under current law","regional"),
 ("forest_boundary","The Living Boundary","Resolve a woodland boundary whose markers and customary uses no longer agree.","Walk the claimed limits","Record customary access","Set a reviewable boundary accord","polity"),
 ("translated_oaths","Oaths in Translation","Prevent a diplomatic oath from acquiring incompatible meanings in two languages.","Consult independent interpreters","Identify the disputed obligation","Witness a revised bilingual oath","polity"),
 ("workshop_pattern","A Pattern Worth Keeping","Preserve a useful workshop method without granting one guild an abusive monopoly.","Observe the method in practice","Negotiate credit and access","Fund a public demonstration","personal"),
 ("missing_envoy","The Missing Envoy","Find an envoy overdue between authorities before rumor determines policy.","Reconstruct the envoy's last route","Follow evidence without exposing hidden geography","Return the envoy or verified dispatches","event_linked"),
 ("salt_and_water","Salt and Water","Restore access to salt or fresh water after control of a source becomes disputed.","Measure present supply","Hear users and guards","Open a protected allocation route","regional"),
 ("fisher_boundaries","Waters Without Fences","Settle competing fishing claims after seasons, gear, or settlement control changed.","Map customary grounds approximately","Inspect damaged gear and catches","Broker a seasonal access agreement","regional"),
 ("tax_roll","Names on the Roll","Correct a tax roll that charges absent households and overlooks powerful ones.","Compare household and levy records","Hear protected complaints","Deliver a corrected roll with an appeal path","administration"),
 ("fortress_stone","Stone for the Wall","Find why defensive repairs consume material without restoring readiness.","Inspect quarry and wall deliveries","Test workmanship at the weak section","Complete accountable repairs","polity"),
 ("market_fire","After the Market Fire","Coordinate recovery after a fire without allowing emergency aid to become private spoils.","Assess losses by quarter","Guard and distribute supplies","Reopen essential stalls fairly","event_linked"),
 ("astronomers_table","A Table of Stars","Reconcile celestial observations gathered with different instruments and calendars.","Collect observations","Compare dates and instrument error","Publish a navigable table","personal"),
 ("horse_lines","Remount Lines","Restore transport and cavalry remounts without stripping farmers of breeding stock.","Inspect available animals","Negotiate seasonal requisition","Deliver fit remounts and return unsuitable stock","polity"),
 ("canal_silt","The Silted Channel","Clear a neglected waterway while resolving who owes labor and who benefits.","Survey the obstruction","Agree labor and compensation","Reopen and mark the channel","administration"),
 ("prisoner_exchange","The Exchange Ground","Arrange a bounded prisoner exchange despite altered diplomacy and absent officers.","Verify captives and authority","Secure neutral ground","Complete or safely suspend the exchange","polity"),
 ("weavers_dyes","Colors That Travel","Reconnect dyers, weavers, and traders after a scarce input changes hands.","Trace the missing dye supply","Test substitutes with artisans","Complete a fair production contract","personal"),
 ("temple_store","The Community Store","Account for shared stores protected by a religious or civic institution during crisis.","Inventory sealed stores","Identify legitimate emergency claims","Supervise a witnessed distribution","event_linked"),
 ("coastal_signal","Signals on the Headland","Restore warning signals whose meanings differ between sailors, soldiers, and villagers.","Inspect signal stations","Agree distinct warning patterns","Run a witnessed readiness test","regional"),
 ("inheritance_maps","The Inherited Map","Resolve an estate or office claim supported by a map that no longer matches the land.","Authenticate the map","Survey surviving landmarks","Record a reversible settlement","administration"),
 ("deserters_return","Terms of Return","Decide whether scattered soldiers are deserters, survivors, or coerced recruits.","Take separate testimony","Confirm the unit's last orders","Arrange service, amnesty, or trial","polity"),
 ("scholars_copies","Copies Against Loss","Create distributed copies of a vulnerable work without removing the original from its community.","Locate skilled copyists","Obtain appropriate materials","Verify and place the copies","personal"),
 ("dockyard_timbers","Timbers for the Yard","Secure sound ship timber while preventing fraudulent grading and destructive cutting.","Inspect forest and yard samples","Trace grading marks","Fulfil a bounded sustainable contract","regional"),
 ("festival_truce","The Festival Truce","Keep a public festival safe when rival groups dispute precedence and space.","Hear the rival organizers","Mark shared routes and safeguards","Maintain the agreed truce","event_linked"),
 ("debt_tablets","Debts Remembered","Reconcile debts recorded under incompatible currencies, calendars, or authorities.","Authenticate the records","Convert obligations transparently","Mediate repayment or release","administration"),
 ("island_beacons","Beacons Between Shores","Reconnect isolated communities with a safe sequence of visible maritime signals.","Survey visible stations","Repair materials without exposing secret routes","Demonstrate the signal chain","regional"),
 ("mine_drainage","Water Below","Rescue a flooded working and determine whether neglect or sabotage caused the loss.","Reach the safe workings","Restore drainage and recover evidence","Settle responsibility and safety terms","event_linked"),
 ("courier_relays","The Broken Relay","Restore a courier chain whose stations answer to different local powers.","Audit missing handoffs","Negotiate neutral passage","Carry a test dispatch end to end","polity"),
 ("orchard_bligh","The Failing Orchard","Identify whether weather, disease, or coercive levies are ruining perennial crops.","Compare affected groves","Consult growers and healers","Fund an appropriate recovery trial","personal"),
 ("refugee_quarters","Room Within the Walls","House displaced families without concealing security risks or displacing residents by force.","Register needs and skills","Inspect viable quarters","Broker temporary rights and duties","event_linked"),
 ("powder_damp","The Damp Magazine","Restore a dangerous storehouse while accounting for scarce military powder.","Secure the magazine","Separate salvageable stores","Repair storage and report losses","polity"),
 ("peace_markers","Markers of Peace","Renew local peace markers after expansion, erosion, or conquest made them ambiguous.","Find surviving witnesses","Survey the disputed marker line","Set and record replacement markers","regional"),
]

def story():
 rows=[]
 for region,(adjective,settlement) in REGIONS.items():
  for key,title,summary,a,b,c,kind in THEMES:
   qid=f"{region}_{key}"
   rows.append({"id":qid,"region":region,"category":kind,"title":f"{title}: {adjective} Accounts",
    "summary":summary,"giverSettlementId":settlement,"objectives":[a,b,c],
    "alternateOutcome":"If the named authority is unavailable, a documented community or successor authority may conclude the work.",
    "failureRecovery":"Changed control or a blocked route suspends the affected objective and exposes the authored alternate; it never silently completes it.",
    "guidance":["region","approximate","return_to_giver"],"rewardProfile":"bounded_story_service"})
 return rows

FAMILIES=[
 ("neighbors_in_need","civilian",["civilian"],"Neighbors in Need","households","Deliver agreed aid; verify it reached the named households.","settlement_reputation"),
 ("market_shortfall","shortage_supply",["shortage","trade"],"Market Shortfall","staple stores","Source a scarce staple; inspect quality before delivery.","trade_throughput"),
 ("sealed_dispatch","delivery",["delivery","administration"],"A Sealed Dispatch","the current civic authority","Carry a sealed dispatch; obtain a valid receipt or return it intact.","polity_favor"),
 ("road_companions","escort",["escort","trade"],"Road Companions","a vulnerable traveling party","Meet the party; escort it through the declared danger and account for losses.","settlement_reputation"),
 ("marks_in_dust","investigation",["investigation"],"Marks in Dust","contradictory local witnesses","Gather separate testimony; recover physical evidence and report without accusation by rumor.","reduced_unrest"),
 ("tools_recovered","recovery",["recovery","civilian"],"Tools Recovered","a working household","Locate the lost tools; establish ownership and return or compensate them.","profession_reputation"),
 ("edge_of_the_chart","exploration",["exploration","frontier"],"Edge of the Chart","local guides","Survey the bounded area; return observations without revealing unearned locations.","discovery"),
 ("master_and_apprentice","profession",["profession"],"Master and Apprentice","a local craft","Obtain suitable materials; complete a supervised piece to the stated standard.","mastery_progress"),
 ("quiet_watch","criminal_security",["security"],"The Quiet Watch","the night watch","Observe the named approach; identify the network and choose arrest or warning.","reduced_crime"),
 ("stores_for_watch","military_support",["military"],"Stores for the Watch","the local defenders","Audit the request; deliver serviceable supplies and witness their issue.","garrison_readiness"),
 ("tide_and_rigging","maritime",["maritime","port"],"Tide and Rigging","waterfront crews","Inspect the vessel or beacon; acquire fittings and complete a safe trial.","fleet_supply"),
 ("ledger_in_arrears","administration",["administration"],"The Ledger in Arrears","the settlement office","Reconcile two records; hear an appeal and file a corrected account.","stability"),
 ("boundary_stones","local_dispute",["dispute","civilian"],"Boundary Stones","neighboring claimants","Survey the disputed use; hear both claims and witness a temporary accord.","reduced_unrest"),
 ("bales_and_balances","trade",["trade"],"Bales and Balances","market factors","Inspect weights and goods; complete a fair exchange through the current market.","currency"),
 ("route_hazards","transport",["delivery","trade"],"Hazards on the Route","carriers and route keepers","Confirm the obstruction; clear or bypass it and guide a test consignment.","experience"),
 ("harbor_missing","search_rescue",["maritime","civilian"],"Missing at the Harbor","families and harbor crews","Reconstruct the last sighting; search safely and return survivors or evidence.","settlement_reputation"),
]

def local():
 families=[]
 frames=[("plain","A routine request has become difficult because local conditions changed.","The giver is unavailable; use the witnessed alternate authority.","Failure records the loss and delays replacement."),
         ("contested","Two parties describe the same need differently, and evidence must decide the response.","Broker a limited compromise if the original remedy is blocked.","Escalation closes the offer without granting rewards."),
         ("urgent","A short deadline raises the cost of delay but does not excuse unsafe work.","Stabilize the immediate danger and return for a reduced outcome.","Expiry preserves the world consequence and starts cooldown."),
         ("scarce","Scarcity makes quality, price, and allocation as important as delivery.","Substitute only a context-appropriate material with consent.","Waste or fraud fails the request and consumes no reward." )]
 for fid,category,tags,title,actor,objective,effect in FAMILIES:
  variants=[]
  for suffix,premise,alternate,failure in frames:
   polity_effect=effect in {"polity_favor","garrison_readiness","fleet_supply","stability","trade_throughput"}
   rewards=[{"kind":"currency","scale":"difficulty_travel_scarcity_means","bounded":True},{"kind":"experience","amountBand":"small"}]
   if effect in {"settlement_reputation","profession_reputation","polity_favor"}: rewards.append({"kind":effect,"amountBand":"small","scope":"polity" if effect=="polity_favor" else "local"})
   elif effect not in {"currency","experience","discovery","mastery_progress"}: rewards.append({"kind":effect,"amountBand":"small","scope":"polity" if polity_effect else "settlement","temporary":polity_effect})
   variants.append({"id":suffix,"title":f"{title}: {suffix.title()}","summary":premise,"dialogue":f"{actor.title()} ask for accountable help, not an unquestioned errand.",
    "objectives":[objective,"Return to the originating settlement and make a witnessed accounting."],"alternate":alternate,"failure":failure,
    "guidance":{"precision":"exact","originPersistent":True,"blockedRoutePolicy":"show_authored_alternate","undiscoveredLeak":False},
    "rewards":rewards,"strategicAccomplishment":objective if polity_effect else None})
  families.append({"id":fid,"category":category,"requiredAnyTags":tags,"cooldownDays":20+(len(families)%5)*10,
    "campaignCompletionCap":3+(len(families)%3),"refillRule":"terminal_then_cooldown","variants":variants})
 return {"schemaVersion":1,"selectionPolicy":{"algorithm":"sha256_rank_v1","inputs":["campaign_seed","settlement_id","slot","cycle","family_id","variant_id"],"rerollOnBoardOpen":False},"families":families}

def main():
 campaign=ROOT/"scenario/campaign-quests.json"; data=json.loads(campaign.read_text()); data["releaseStoryQuests"]=story(); campaign.write_text(json.dumps(data,indent=2)+"\n")
 (ROOT/"scenario/local-random-quests.json").write_text(json.dumps(local(),indent=2)+"\n")
 print(f"wrote {len(story())} story quests and {sum(len(x['variants']) for x in local()['families'])} local variants")
if __name__=="__main__": main()
