# Phase 9 release-blocker audit

Result: **FAIL**

Unresolved campaign blockers: **239**

## Severity taxonomy

| ID | Release blocking | Definition |
|---|---:|---|
| `campaign_blocker` | yes | A reproducible failure that prevents starting, progressing, saving, loading, travelling, recovering, or completing otherwise reachable campaign content. |
| `critical_unclassified` | yes | A critical validation failure whose campaign impact has not yet been classified. |
| `major` | no | A bounded loss of optional content or degraded behavior with a deterministic workaround; no mandatory route or persisted authority is lost. |
| `minor` | no | Cosmetic, informational, or low-impact behavior that does not impede campaign play. |

## Declared campaign journeys and executed save fixtures

Each row executes save serialization/loading and schema-3 migration. Regions, maps, systems and end dates describe the declared itinerary; they are not evidence of executing that itinerary or native Warcraft saves. The soak below separately executes the headless simulation fixture.

| Stable ID | Declared branch | Seed | Declared regions | Declared maps | Save fixture result |
|---|---|---:|---:|---:|---|
| `JOURNEY-ATLANTIC-TO-PACIFIC` | maritime_expansion | 1450 | 7 | 8 | pass |
| `JOURNEY-ALTERNATE-HISTORY` | alternate_history | 1701 | 7 | 8 | pass |

## Player-facing runtime acceptance

Static readiness, executed production integration, built-artifact inspection and real-client status are separate. Source/test names and declared itineraries cannot satisfy integration. Missing same-revision execution or artifact evidence blocks this gate.

| System | Data complete | Headless simulation complete | Runtime integrated | Player-facing complete | Release-validated |
|---|---:|---:|---:|---:|---:|
| `campaign_launch` | yes | no | no | no | no |
| `origin_selection` | yes | no | no | no | no |
| `country_diplomacy` | yes | no | no | no | no |
| `trade` | yes | no | no | no | no |
| `army_fleet_control` | yes | no | no | no | no |
| `city_capture` | yes | no | no | no | no |
| `garrisons` | yes | no | no | no | no |
| `administration` | yes | no | no | no | no |
| `heroes` | yes | no | no | no | no |
| `inventory_equipment` | yes | no | no | no | no |
| `technology_institutions` | yes | no | no | no | no |
| `quests_journal` | yes | no | no | no | no |
| `treasures_discovery` | yes | no | no | no | no |
| `save_autosave_load` | yes | no | no | no | no |
| `cross_map_travel` | yes | no | no | no | no |
| `world_map` | yes | no | no | no | no |
| `remote_management` | yes | no | no | no | no |
| `government_rewards` | yes | no | no | no | no |
| `religion` | yes | no | no | no | no |
| `piracy` | yes | no | no | no | no |

## Findings

| Stable ID | Severity | Class | Context | Disposition |
|---|---|---|---|---|
| `RESEARCH-UNBOUND-ABOLITIONIST-PUBLIC-SPHERE-POLICY-PROGRESSION-ABOLITIONIST-PUBLIC-SPHERE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-AGRARIAN-IMPROVEMENT-BUILDING-GRANARY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-AGRARIAN-IMPROVEMENT-POLICY-LAND-TENURE-REFORM` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-AGRICULTURAL-MECHANIZATION-POLICY-ENCLOSURE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-AGRICULTURAL-SOCIETIES-POLICY-PROGRESSION-AGRICULTURAL-SOCIETIES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ANATOMY-AND-MEDICINE-ABILITY-EPIDEMIC-CONTROL` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ARQUEBUS-VOLLEY-DRILL-MODIFIER-PROGRESSION-ARQUEBUS-VOLLEY-DRILL` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ARTILLERY-OFFICES-POLICY-PROGRESSION-ARTILLERY-OFFICES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ARTILLERY-TRAIN-MODIFIER-PROGRESSION-ARTILLERY-TRAIN` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-AUCTION-MARKETS-MODIFIER-PROGRESSION-AUCTION-MARKETS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BAROMETRIC-MEASUREMENT-MODIFIER-PROGRESSION-BAROMETRIC-MEASUREMENT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BATTLEFLEET-DOCTRINE-UNIT-SHIP-OF-THE-LINE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BAYONET-SYSTEM-MODIFIER-PROGRESSION-BAYONET-SYSTEM` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BILL-OF-EXCHANGE-NETWORKS-MODIFIER-PROGRESSION-BILL-OF-EXCHANGE-NETWORKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BLAST-FURNACE-PRACTICE-MODIFIER-PROGRESSION-BLAST-FURNACE-PRACTICE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BORING-MILLS-MODIFIER-PROGRESSION-BORING-MILLS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BOTANICAL-COLLECTING-MODIFIER-PROGRESSION-BOTANICAL-COLLECTING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-BROKERAGE-HOUSES-MODIFIER-PROGRESSION-BROKERAGE-HOUSES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CADASTRAL-SURVEY-MODIFIER-PROGRESSION-CADASTRAL-SURVEY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CALCULUS-METHODS-MODIFIER-PROGRESSION-CALCULUS-METHODS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CAMPAIGN-BAKERIES-MODIFIER-PROGRESSION-CAMPAIGN-BAKERIES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CANAL-LOGISTICS-MODIFIER-PROGRESSION-CANAL-LOGISTICS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CANAL-TOLLS-FINANCE-MODIFIER-PROGRESSION-CANAL-TOLLS-FINANCE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CAREENING-STATIONS-MODIFIER-PROGRESSION-CAREENING-STATIONS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CARRONADE-BATTERIES-MODIFIER-PROGRESSION-CARRONADE-BATTERIES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CARVEL-HULL-CONSTRUCTION-MODIFIER-PROGRESSION-CARVEL-HULL-CONSTRUCTION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CAST-CANNON-MODIFIER-PROGRESSION-CAST-CANNON` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CENTRAL-BANK-INSTITUTION-POLICY-PROGRESSION-CENTRAL-BANK-INSTITUTION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CENTRAL-BANKING-MODIFIER-PROGRESSION-CENTRAL-BANKING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CHANCERY-ARCHIVES-MODIFIER-PROGRESSION-CHANCERY-ARCHIVES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CHARTERED-COMPANIES-POLICY-COMMERCIAL-COURTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CHARTERED-COMPANIES-UNIT-ARMED-INDIAMAN` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CHARTERED-MUNICIPALITIES-POLICY-PROGRESSION-CHARTERED-MUNICIPALITIES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CHEMICAL-CLASSIFICATION-MODIFIER-PROGRESSION-CHEMICAL-CLASSIFICATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CIPHERED-DISPATCHES-MODIFIER-PROGRESSION-CIPHERED-DISPATCHES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CIVIC-PEST-HOSPITALS-MODIFIER-PROGRESSION-CIVIC-PEST-HOSPITALS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CIVIL-SERVICE-EXAMINATIONS-MODIFIER-PROGRESSION-CIVIL-SERVICE-EXAMINATIONS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CLINICAL-CASE-RECORDS-MODIFIER-PROGRESSION-CLINICAL-CASE-RECORDS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COASTAL-TRIANGULATION-MODIFIER-PROGRESSION-COASTAL-TRIANGULATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CODIFIED-LAW-MODIFIER-PROGRESSION-CODIFIED-LAW` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COKE-SMELTED-IRON-MODIFIER-PROGRESSION-COKE-SMELTED-IRON` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COLONIAL-COUNCILS-POLICY-PROGRESSION-COLONIAL-COUNCILS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COMBINED-ARMS-COLUMNS-MODIFIER-PROGRESSION-COMBINED-ARMS-COLUMNS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COMMERCIAL-COURTS-INSTITUTION-POLICY-PROGRESSION-COMMERCIAL-COURTS-INSTITUTION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COMMERCIAL-STATISTICS-MODIFIER-PROGRESSION-COMMERCIAL-STATISTICS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COMMODITY-EXCHANGES-BUILDING-CUSTOMS-HOUSE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COMMODITY-EXCHANGES-MODIFIER-CREDIT-LIQUIDITY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COMPARATIVE-LINGUISTICS-MODIFIER-PROGRESSION-COMPARATIVE-LINGUISTICS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CONFESSIONAL-STATE-POLICY-RELIGIOUS-TOLERATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CONSTITUTIONALISM-POLICY-CONSTITUTIONAL-GOVERNMENT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CONSULAR-TRADE-NETWORKS-MODIFIER-PROGRESSION-CONSULAR-TRADE-NETWORKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CONTINENTAL-INTERIORS-MODIFIER-PROGRESSION-CONTINENTAL-INTERIORS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-CONTRACT-VICTUALLING-MODIFIER-PROGRESSION-CONTRACT-VICTUALLING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COPPER-SHEATHING-MODIFIER-PROGRESSION-COPPER-SHEATHING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COUNTERMARCH-FIRE-MODIFIER-PROGRESSION-COUNTERMARCH-FIRE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-COURIER-RELAYS-MODIFIER-PROGRESSION-COURIER-RELAYS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-DEEP-MINE-DRAINAGE-MODIFIER-PROGRESSION-DEEP-MINE-DRAINAGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-DEEP-SEA-SOUNDING-MODIFIER-PROGRESSION-DEEP-SEA-SOUNDING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-DOCKYARD-LOGISTICS-BUILDING-DRY-DOCK` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-DOCKYARD-LOGISTICS-UNIT-COASTAL-PATROL-SLOOP` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-DOUBLE-ENTRY-BOOKKEEPING-MODIFIER-TRADE-EFFICIENCY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-DRAINAGE-RECLAMATION-MODIFIER-PROGRESSION-DRAINAGE-RECLAMATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ELECTRICAL-EXPERIMENTATION-MODIFIER-PROGRESSION-ELECTRICAL-EXPERIMENTATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ELECTRICAL-TELEGRAPH-CONCEPTS-MODIFIER-PROGRESSION-ELECTRICAL-TELEGRAPH-CONCEPTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ELECTROMAGNETIC-EXPERIMENT-MODIFIER-PROGRESSION-ELECTROMAGNETIC-EXPERIMENT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-EMERGENCY-TRIAGE-MODIFIER-PROGRESSION-EMERGENCY-TRIAGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ENLIGHTENMENT-PUBLIC-SPHERE-POLICY-FREE-PRESS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-EXPEDITIONARY-ETHNOGRAPHY-MODIFIER-PROGRESSION-EXPEDITIONARY-ETHNOGRAPHY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-EXPERIMENTAL-METHOD-MODIFIER-RESEARCH-EXCHANGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FIELD-ENTRENCHMENT-MODIFIER-PROGRESSION-FIELD-ENTRENCHMENT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FIELD-SIGNAL-CORPS-MODIFIER-PROGRESSION-FIELD-SIGNAL-CORPS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FISCAL-CADASTRES-MODIFIER-PROGRESSION-FISCAL-CADASTRES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FLEET-VICTUALLING-MODIFIER-PROGRESSION-FLEET-VICTUALLING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FLINTLOCK-DRILL-UNIT-FLINTLOCK-INFANTRY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FODDER-CROP-SYSTEMS-MODIFIER-PROGRESSION-FODDER-CROP-SYSTEMS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FRIGATE-CRUISING-ABILITY-CONVOY-ESCORT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-FRIGATE-CRUISING-UNIT-OCEAN-CRUISING-FRIGATE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GALLEON-DESIGN-UNIT-GALLEON` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GAS-LIGHTING-MODIFIER-PROGRESSION-GAS-LIGHTING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GENERAL-STAFF-METHODS-MODIFIER-PROGRESSION-GENERAL-STAFF-METHODS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GEODETIC-ARCS-MODIFIER-PROGRESSION-GEODETIC-ARCS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GEOLOGICAL-SURVEY-MODIFIER-PROGRESSION-GEOLOGICAL-SURVEY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GLOBAL-HYDROGRAPHY-MODIFIER-PROGRESSION-GLOBAL-HYDROGRAPHY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-GLOBAL-PRICE-BULLETINS-MODIFIER-PROGRESSION-GLOBAL-PRICE-BULLETINS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-HERBAL-PHARMACOPOEIA-MODIFIER-PROGRESSION-HERBAL-PHARMACOPOEIA` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-HIGH-PRESSURE-STEAM-MODIFIER-PROGRESSION-HIGH-PRESSURE-STEAM` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-HORSE-ARTILLERY-MODIFIER-PROGRESSION-HORSE-ARTILLERY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-INDUSTRIAL-MANUFACTURE-MODIFIER-INDUSTRIAL-OUTPUT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-INSURANCE-MARKETS-MODIFIER-PROGRESSION-INSURANCE-MARKETS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-INTEGRATED-WORLD-MARKETS-ABILITY-GLOBAL-EXPEDITION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-INTEGRATED-WORLD-MARKETS-MODIFIER-TRADE-EFFICIENCY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-INTENSIVE-CROP-ROTATION-MODIFIER-AGRICULTURAL-OUTPUT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-INTERCHANGEABLE-PARTS-MODIFIER-PROGRESSION-INTERCHANGEABLE-PARTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-IRON-PLOUGHS-MODIFIER-PROGRESSION-IRON-PLOUGHS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-IRRIGATION-HYDRAULICS-MODIFIER-HARVEST-RESILIENCE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-JOINT-STOCK-ENTERPRISE-BUILDING-STOCK-EXCHANGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-LATEEN-SQUARE-RIG-MODIFIER-PROGRESSION-LATEEN-SQUARE-RIG` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-LINEAR-TACTICS-UNIT-LINE-INFANTRY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-LITHOGRAPHIC-PRINTING-MODIFIER-PROGRESSION-LITHOGRAPHIC-PRINTING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-LONGITUDE-LUNAR-DISTANCE-MODIFIER-PROGRESSION-LONGITUDE-LUNAR-DISTANCE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MACHINE-TOOLS-MODIFIER-PROGRESSION-MACHINE-TOOLS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MANUFACTURING-CREDIT-MODIFIER-PROGRESSION-MANUFACTURING-CREDIT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MARINE-CHRONOMETER-ABILITY-SCIENTIFIC-SURVEY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MARKET-GARDENING-MODIFIER-PROGRESSION-MARKET-GARDENING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MASS-ARMY-LOGISTICS-MODIFIER-SUPPLY-EFFICIENCY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MASS-ARMY-LOGISTICS-POLICY-MASS-CONSCRIPTION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MASS-ARMY-LOGISTICS-UNIT-COMMON-WAGON-TRAIN` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MASS-EDUCATION-POLICY-PROGRESSION-MASS-EDUCATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MASS-POSTAL-SERVICE-MODIFIER-PROGRESSION-MASS-POSTAL-SERVICE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MECHANIZED-PAPER-MAKING-MODIFIER-PROGRESSION-MECHANIZED-PAPER-MAKING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MERCHANT-CORRESPONDENCE-MODIFIER-PROGRESSION-MERCHANT-CORRESPONDENCE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MERCHANT-DIASPORAS-POLICY-PROGRESSION-MERCHANT-DIASPORAS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MERIT-CIVIL-SERVICE-MODIFIER-PROGRESSION-MERIT-CIVIL-SERVICE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-METRIC-METROLOGY-MODIFIER-PROGRESSION-METRIC-METROLOGY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-METRIC-STANDARDIZATION-POLICY-PROGRESSION-METRIC-STANDARDIZATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MICROSCOPY-MODIFIER-PROGRESSION-MICROSCOPY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MILITARY-FIELD-HOSPITALS-MODIFIER-PROGRESSION-MILITARY-FIELD-HOSPITALS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MILITARY-FISCAL-STATE-POLICY-PUBLIC-CREDIT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MILITARY-MAGAZINES-MODIFIER-PROGRESSION-MILITARY-MAGAZINES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MINISTERIAL-CABINETS-MODIFIER-PROGRESSION-MINISTERIAL-CABINETS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MOBILE-FIELD-ARTILLERY-ABILITY-FIELD-ARTILLERY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MONSOON-ROUTE-ALMANACS-MODIFIER-PROGRESSION-MONSOON-ROUTE-ALMANACS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MOVABLE-TYPE-PRINTING-BUILDING-PRINTING-HOUSE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-MUNICIPAL-CHARTERS-MODIFIER-PROGRESSION-MUNICIPAL-CHARTERS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NATIONAL-ACCOUNTS-MODIFIER-PROGRESSION-NATIONAL-ACCOUNTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-ADMINISTRATION-BUILDING-DRY-DOCK` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-ADMINISTRATION-POLICY-PERMANENT-NAVAL-BOARD` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-FLAG-SIGNALS-MODIFIER-PROGRESSION-NAVAL-FLAG-SIGNALS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-GUNNERY-MODIFIER-SHIPBUILDING-CAPACITY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-GUNNERY-UNIT-EAST-ASIAN-WAR-JUNK` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-HOSPITALS-MODIFIER-PROGRESSION-NAVAL-HOSPITALS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-SCURVY-PREVENTION-MODIFIER-PROGRESSION-NAVAL-SCURVY-PREVENTION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NAVAL-SIGNAL-BOOKS-MODIFIER-PROGRESSION-NAVAL-SIGNAL-BOOKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NEW-WORLD-CROPS-MODIFIER-POPULATION-GROWTH` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NEWSPAPER-EXCHANGES-MODIFIER-PROGRESSION-NEWSPAPER-EXCHANGES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-NEWTONIAN-SCIENCE-MODIFIER-PROGRESSION-NEWTONIAN-SCIENCE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-OBSTETRIC-TRAINING-MODIFIER-PROGRESSION-OBSTETRIC-TRAINING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-OCEANIC-SEAMANSHIP-ABILITY-OPEN-WATER-NAVIGATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-OFFICER-ACADEMIES-MODIFIER-PROGRESSION-OFFICER-ACADEMIES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-OPTICAL-TELEGRAPH-MODIFIER-PROGRESSION-OPTICAL-TELEGRAPH` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-OVERLAND-CARAVAN-SURVEYS-MODIFIER-PROGRESSION-OVERLAND-CARAVAN-SURVEYS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PACIFIC-CHARTING-MODIFIER-PROGRESSION-PACIFIC-CHARTING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PACK-TRAIN-CONTRACTS-MODIFIER-PROGRESSION-PACK-TRAIN-CONTRACTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PATENT-OFFICES-POLICY-PROGRESSION-PATENT-OFFICES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PATHOLOGICAL-ANATOMY-MODIFIER-PROGRESSION-PATHOLOGICAL-ANATOMY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PILOT-BOOKS-MODIFIER-PROGRESSION-PILOT-BOOKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PLANTATION-PROCESSING-MODIFIER-PROGRESSION-PLANTATION-PROCESSING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-POLAR-NAVIGATION-MODIFIER-PROGRESSION-POLAR-NAVIGATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-POPULATION-CENSUS-MODIFIER-PROGRESSION-POPULATION-CENSUS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-POSTAL-NETWORKS-BUILDING-POSTAL-STATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PRECISION-ENGINEERING-POLICY-PATENT-LAW` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PRESERVED-RATIONS-MODIFIER-PROGRESSION-PRESERVED-RATIONS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PRINTED-BROADSHEETS-MODIFIER-PROGRESSION-PRINTED-BROADSHEETS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PRINTED-OBSERVATION-TABLES-MODIFIER-PROGRESSION-PRINTED-OBSERVATION-TABLES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROBABILITY-STATISTICS-MODIFIER-PROGRESSION-PROBABILITY-STATISTICS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROFESSIONAL-BUREAUCRACY-POLICY-CENTRAL-RECORDS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROFESSIONAL-CIVIL-SERVICE-POLICY-PROGRESSION-PROFESSIONAL-CIVIL-SERVICE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROFESSIONAL-MEDICAL-COLLEGES-POLICY-PROGRESSION-PROFESSIONAL-MEDICAL-COLLEGES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROVINCIAL-AUDITS-MODIFIER-PROGRESSION-PROVINCIAL-AUDITS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROVINCIAL-GOVERNANCE-MODIFIER-ADMINISTRATIVE-REACH` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PROVINCIAL-GOVERNANCE-POLICY-PROVINCIAL-GOVERNORS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PUBLIC-CREDIT-POLICY-PUBLIC-CREDIT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PUBLIC-MORTALITY-STATISTICS-MODIFIER-PROGRESSION-PUBLIC-MORTALITY-STATISTICS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-PUDDLING-IRON-MODIFIER-PROGRESSION-PUDDLING-IRON` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-QUARANTINE-PRACTICE-MODIFIER-PROGRESSION-QUARANTINE-PRACTICE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-QUARTERMASTER-CORPS-MODIFIER-PROGRESSION-QUARTERMASTER-CORPS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-RATED-WARSHIPS-MODIFIER-PROGRESSION-RATED-WARSHIPS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-REGIMENTAL-ORGANIZATION-MODIFIER-PROGRESSION-REGIMENTAL-ORGANIZATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-REGIONAL-SEED-EXCHANGE-MODIFIER-PROGRESSION-REGIONAL-SEED-EXCHANGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-RENAISSANCE-HUMANISM-POLICY-PROGRESSION-RENAISSANCE-HUMANISM` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-REPRESENTATIVE-ASSEMBLIES-POLICY-PROGRESSION-REPRESENTATIVE-ASSEMBLIES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-RESERVE-MOBILIZATION-MODIFIER-PROGRESSION-RESERVE-MOBILIZATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-RIFLED-INFANTRY-TRIALS-MODIFIER-PROGRESSION-RIFLED-INFANTRY-TRIALS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-RIVER-TRANSPORT-BUREAUS-MODIFIER-PROGRESSION-RIVER-TRANSPORT-BUREAUS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ROAD-WAYSTATIONS-MODIFIER-PROGRESSION-ROAD-WAYSTATIONS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ROTATIVE-STEAM-POWER-BUILDING-FACTORY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-ROYAL-DOCKYARDS-POLICY-PROGRESSION-ROYAL-DOCKYARDS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SAVINGS-BANKS-MODIFIER-PROGRESSION-SAVINGS-BANKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SCHEDULED-POST-MODIFIER-PROGRESSION-SCHEDULED-POST` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SCHOLASTIC-NATURAL-PHILOSOPHY-MODIFIER-PROGRESSION-SCHOLASTIC-NATURAL-PHILOSOPHY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SCIENTIFIC-SOCIETIES-MODIFIER-RESEARCH-EXCHANGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SEED-DRILL-MODIFIER-PROGRESSION-SEED-DRILL` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SELECTIVE-BREEDING-MODIFIER-PROGRESSION-SELECTIVE-BREEDING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SEMAPHORE-SIGNALS-MODIFIER-PROGRESSION-SEMAPHORE-SIGNALS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SHIPBOARD-ARTILLERY-DECKS-MODIFIER-PROGRESSION-SHIPBOARD-ARTILLERY-DECKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SIEGE-ENGINEERING-CORPS-ABILITY-SIEGE-ENGINEERING` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SIEGE-ENGINEERING-CORPS-UNIT-COMMON-SAPPER-CORPS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SIGNAL-INTELLIGENCE-BUREAUS-MODIFIER-PROGRESSION-SIGNAL-INTELLIGENCE-BUREAUS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SKIRMISHER-DOCTRINE-MODIFIER-PROGRESSION-SKIRMISHER-DOCTRINE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SMALLPOX-INOCULATION-MODIFIER-PROGRESSION-SMALLPOX-INOCULATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SOIL-CHEMISTRY-MODIFIER-PROGRESSION-SOIL-CHEMISTRY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STANDARD-SUPPLY-WEIGHTS-MODIFIER-PROGRESSION-STANDARD-SUPPLY-WEIGHTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STANDARDIZED-CHARTS-MODIFIER-FLEET-NAVIGATION-EFFICIENCY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STANDARDIZED-ORDNANCE-UNIT-COMMON-SIEGE-BATTERY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STANDING-ARMY-ESTABLISHMENT-POLICY-PROGRESSION-STANDING-ARMY-ESTABLISHMENT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STANDING-ARMY-SYSTEM-MODIFIER-GARRISON-READINESS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STANDING-ARMY-SYSTEM-POLICY-STANDING-ARMY-REFORM` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STATISTICAL-ADMINISTRATION-POLICY-STANDARD-MEASURES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STEAM-HAMMER-CONCEPTS-MODIFIER-PROGRESSION-STEAM-HAMMER-CONCEPTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STEAM-NAVIGATION-UNIT-STEAM-VESSEL` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STEAM-TOWAGE-MODIFIER-PROGRESSION-STEAM-TOWAGE` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-STRATEGIC-DEPOTS-MODIFIER-PROGRESSION-STRATEGIC-DEPOTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SURGICAL-ANATOMY-MODIFIER-PROGRESSION-SURGICAL-ANATOMY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SURVEYING-INSTRUMENTS-MODIFIER-PROGRESSION-SURVEYING-INSTRUMENTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SYSTEMATIC-NATURAL-HISTORY-ABILITY-SCIENTIFIC-SURVEY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-SYSTEMATIC-NATURAL-HISTORY-BUILDING-ACADEMY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-TERRACE-CONSERVATION-MODIFIER-PROGRESSION-TERRACE-CONSERVATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-TEXTILE-MECHANIZATION-MODIFIER-WORKSHOP-OUTPUT` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-TRACE-ITALIENNE-BUILDING-ARSENAL` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-TRADE-WIND-ROUTES-MODIFIER-PROGRESSION-TRADE-WIND-ROUTES` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-TRAINED-MAGISTRACY-MODIFIER-PROGRESSION-TRAINED-MAGISTRACY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-TURNPIKE-NETWORKS-MODIFIER-PROGRESSION-TURNPIKE-NETWORKS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-URBAN-PUBLIC-HEALTH-POLICY-PUBLIC-HEALTH` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-VACCINATION-MODIFIER-PROGRESSION-VACCINATION` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-VETERINARY-HUSBANDRY-MODIFIER-PROGRESSION-VETERINARY-HUSBANDRY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-WAREHOUSE-WARRANTS-MODIFIER-PROGRESSION-WAREHOUSE-WARRANTS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-WATER-POWERED-MACHINERY-MODIFIER-PROGRESSION-WATER-POWERED-MACHINERY` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RESEARCH-UNBOUND-WIRE-DRAWING-MILLS-MODIFIER-PROGRESSION-WIRE-DRAWING-MILLS` | campaign_blocker | missing_runtime_integration | scenario/world/world.json | unresolved |
| `RUNTIME-EVIDENCE-INCOMPLETE` | campaign_blocker | missing_runtime_integration | runtime-acceptance | unresolved |
| `RUNTIME-MISSING-ADMINISTRATION` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-ARMY-FLEET-CONTROL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-CAMPAIGN-LAUNCH` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-CITY-CAPTURE` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-COUNTRY-DIPLOMACY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-CROSS-MAP-TRAVEL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-GARRISONS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-GOVERNMENT-REWARDS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-HEROES` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-INVENTORY-EQUIPMENT` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-ORIGIN-SELECTION` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-PIRACY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-QUESTS-JOURNAL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-RELIGION` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-REMOTE-MANAGEMENT` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-SAVE-AUTOSAVE-LOAD` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TECHNOLOGY-INSTITUTIONS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TRADE` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TREASURES-DISCOVERY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-WORLD-MAP` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |

## Audited release evidence

- 31 tracked validation reports
- 8 hashed release inputs
- 10 supported release-save schemas migrated and authority-checked
- 2 deterministic 1450–1820 soak runs
- Journey rows execute campaign-save round trips and migration; their route/system coverage is declared metadata.
- Native Warcraft save/load, physical-map launches and real-client journeys are not executed by this audit.
