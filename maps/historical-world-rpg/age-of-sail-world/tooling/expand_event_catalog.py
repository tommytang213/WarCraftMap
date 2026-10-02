#!/usr/bin/env python3
"""One-time deterministic authoring helper for the release event catalogue.

The expanded objects are written into historical-events.json; this helper is retained
only so reviewers can audit the compact chronology used to create the data.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"scenario"/"historical-events.json"

# id, exact/representative onset date, region, category, concise evidence note.
ROWS="""
printing_press_diffusion|1455-01-01|europe|technological|Movable-type printing spread rapidly after Gutenberg's Mainz workshop.
castilian_succession_war|1475-03-01|europe|succession|The Castilian succession dispute drew Portugal and Aragon into war.
granada_war|1482-02-28|europe|military|The Granada War culminated in the fall of the Nasrid kingdom.
italian_wars_begin|1494-09-01|europe|military|Charles VIII's invasion opened decades of warfare in Italy.
habsburg_spanish_succession|1516-03-14|europe|succession|Charles inherited the crowns of Castile and Aragon in 1516.
german_peasants_war|1524-06-01|europe|social|Peasant leagues challenged lordship across German-speaking lands.
sack_of_rome|1527-05-06|europe|military|Imperial troops sacked Rome during the Italian Wars.
peace_of_augsburg|1555-09-25|europe|religious|Augsburg established a confessional settlement among Imperial estates.
dutch_revolt|1568-05-23|europe|political|Revolt in the Low Countries challenged Habsburg government.
spanish_armada|1588-08-08|europe|naval|The Armada campaign tested English and Spanish naval logistics.
edict_of_nantes|1598-04-13|europe|religious|The Edict of Nantes granted limited rights to French Protestants.
english_civil_wars|1642-08-22|europe|political|Conflict between Crown and Parliament transformed the British kingdoms.
peace_of_westphalia|1648-10-24|europe|diplomatic|The Westphalian treaties ended the Thirty Years' War.
glorious_revolution|1688-11-05|europe|institutional|The Revolution of 1688 altered the English succession and constitution.
war_spanish_succession|1701-07-09|europe|succession|A disputed Spanish succession produced a European and Atlantic war.
act_of_union|1707-05-01|europe|institutional|The Acts of Union formed the Kingdom of Great Britain.
seven_years_war_europe|1756-08-29|europe|military|The Seven Years' War reordered alliances and imperial competition.
partition_of_poland|1772-08-05|europe|political|The first partition transferred Polish-Lithuanian territories to neighbors.
steam_engine_improvement|1769-01-05|europe|technological|Watt's patent marked a major improvement in steam power.
irish_rebellion|1798-05-23|europe|social|The United Irish uprising challenged British government in Ireland.
congress_of_vienna|1815-06-09|europe|diplomatic|The Vienna settlement redrew Europe after the Napoleonic Wars.
greek_independence_pressure|1820-12-31|europe|political|Revolutionary networks were gathering before the Greek uprising.
scientific_revolution_networks|1660-11-28|europe|institutional|The Royal Society exemplified new institutions of experimental inquiry.
enclosure_acceleration|1750-01-01|europe|social|Parliamentary enclosure accelerated changes in British rural society.

songhai_timbuktu_capture|1468-01-01|africa|military|Sunni Ali captured Timbuktu and expanded Songhai authority.
portuguese_elmina|1482-01-21|africa|commercial|The Portuguese founded São Jorge da Mina as a fortified trading post.
kongo_portuguese_embassy|1491-05-03|africa|diplomatic|Kongo's court adopted Christianity amid sustained Portuguese relations.
moroccan_songhai_invasion|1591-03-13|africa|military|A Moroccan expedition defeated Songhai forces at Tondibi.
ajuran_portuguese_conflict|1530-01-01|africa|naval|Ajuran and Portuguese forces contested western Indian Ocean routes.
monomotapa_portuguese_treaties|1607-01-01|africa|diplomatic|Treaties expanded Portuguese influence at the Mutapa court.
ndongo_resistance|1624-01-01|africa|character|Njinga became ruler of Ndongo and led prolonged resistance and diplomacy.
dutch_cape_settlement|1652-04-06|africa|commercial|The Dutch established a provisioning station at Table Bay.
kongo_civil_war|1665-10-29|africa|succession|Kongo entered a prolonged civil war after Mbwila.
merina_consolidation|1710-01-01|africa|political|Merina rulers began renewed consolidation in Madagascar's highlands.
asante_confederacy|1701-01-01|africa|institutional|Asante state formation linked military organization and gold trade.
fulani_futa_jallon|1727-01-01|africa|religious|A Muslim confederation emerged in Futa Jallon.
ethiopian_gondarine_court|1636-01-01|africa|institutional|Fasilides established Gondar as a durable royal center.
oromo_migrations|1550-01-01|africa|social|Oromo expansions transformed political landscapes in the Horn.
dahomey_expansion|1727-01-01|africa|military|Dahomey captured Whydah and gained direct coastal access.
oyo_imperial_trade|1750-01-01|africa|commercial|Oyo cavalry power supported a broad regional commercial system.
cape_frontier_wars|1779-01-01|africa|military|The first Cape frontier war began amid settler-Xhosa competition.
sierra_leone_freetown|1792-03-11|africa|social|Freetown was founded as a settlement for Black Loyalists.
haitian_revolution_african_trade|1791-08-22|africa|commercial|The Haitian Revolution disrupted Atlantic commodity and captive-trade networks.
muhammad_ali_egypt|1805-05-17|africa|political|Muhammad Ali's accession began military-fiscal reform in Egypt.
sokoto_caliphate|1804-02-21|africa|religious|Usman dan Fodio's movement founded the Sokoto Caliphate.
zulu_consolidation|1816-01-01|africa|military|Shaka's accession accelerated Zulu political and military consolidation.
abolition_british_trade|1807-03-25|africa|institutional|Britain prohibited its subjects from participating in the Atlantic slave trade.
sahel_drought_cycle|1738-01-01|africa|environmental|Eighteenth-century Sahel drought episodes strained pastoral and agrarian systems.

timurid_succession|1451-01-01|middle_east_india|succession|Timurid succession struggles reshaped power in Iran and Central Asia.
ottoman_mamluk_war|1516-08-24|middle_east_india|military|Ottoman victory over the Mamluks transferred Syria and Egypt.
safavid_foundation|1501-07-01|middle_east_india|religious|Shah Ismail established Safavid rule and promoted Twelver Shiism.
first_battle_panipat|1526-04-21|middle_east_india|military|Babur's victory at Panipat founded Mughal power in north India.
vijayanagara_talikota|1565-01-26|middle_east_india|military|The Deccan sultanates defeated Vijayanagara at Talikota.
akbar_revenue_reforms|1580-01-01|middle_east_india|institutional|Mughal revenue reforms regularized assessment and administration.
abbas_isfahan|1598-01-01|middle_east_india|commercial|Shah Abbas made Isfahan a capital and promoted long-distance trade.
east_india_company_charter|1600-12-31|middle_east_india|commercial|The English East India Company received its royal charter.
taj_mahal_construction|1632-01-01|middle_east_india|character|Shah Jahan commissioned the Taj Mahal during Mughal architectural florescence.
persian_gulf_competition|1622-04-22|middle_east_india|naval|Safavid-English forces expelled the Portuguese from Hormuz.
aurangzeb_accession|1658-07-31|middle_east_india|succession|Aurangzeb prevailed in the Mughal war of succession.
maratha_coronation|1674-06-06|middle_east_india|political|Shivaji's coronation formalized a new Maratha kingship.
nadir_shah_delhi|1739-03-20|middle_east_india|military|Nadir Shah captured Delhi and weakened Mughal authority.
carnatic_wars|1746-09-04|middle_east_india|military|European companies and Indian allies fought for influence in the Carnatic.
plassey|1757-06-23|middle_east_india|political|The battle of Plassey expanded Company political power in Bengal.
mysore_rocket_warfare|1780-09-10|middle_east_india|technological|Mysore deployed iron-cased rockets effectively in war.
permanent_settlement_bengal|1793-03-22|middle_east_india|institutional|The Permanent Settlement altered land revenue collection in Bengal.
wahhabi_saudi_alliance|1744-01-01|middle_east_india|religious|The Diriyah alliance joined religious reform with Saudi political power.
oman_maritime_empire|1698-12-13|middle_east_india|naval|Omani forces captured Mombasa and expanded western Indian Ocean influence.
afghan_durrani_foundation|1747-10-01|middle_east_india|succession|Ahmad Shah Durrani founded a new Afghan empire.
anglo_maratha_war|1775-03-06|middle_east_india|military|The first Anglo-Maratha War grew from a succession dispute.
egypt_french_invasion|1798-07-01|middle_east_india|exploration|The French invasion joined military conquest with scientific survey.
mahmud_reforms|1808-11-15|middle_east_india|institutional|Mahmud II's accession opened a prolonged Ottoman reform era.
monsoon_failure_india|1783-01-01|middle_east_india|environmental|The Chalisa famine followed severe monsoon failure and war disruption.

malacca_falls_portugal|1511-08-24|southeast_asia|military|Portuguese forces captured Melaka and its strategic harbor.
brunei_golden_age|1521-01-01|southeast_asia|commercial|Brunei's court anchored wide maritime and tributary networks.
magellan_philippines|1521-03-16|southeast_asia|exploration|Magellan's expedition reached the Philippine archipelago.
spanish_manila|1571-06-24|southeast_asia|commercial|Spanish Manila connected American silver with Asian commerce.
burmese_siamese_war|1563-01-01|southeast_asia|military|Toungoo armies invaded Ayutthaya in a major mainland war.
aceh_ottoman_mission|1566-01-01|southeast_asia|diplomatic|Aceh sought Ottoman military aid against Portuguese power.
ternate_tidore_rivalry|1575-01-01|southeast_asia|commercial|Maluku sultanates and Europeans contested clove production and trade.
dutch_voc_founded|1602-03-20|southeast_asia|institutional|The VOC united Dutch ventures under chartered sovereign powers.
amboyna_crisis|1623-03-09|southeast_asia|diplomatic|The Amboyna executions sharpened Anglo-Dutch commercial rivalry.
makassar_war|1666-12-19|southeast_asia|naval|The Makassar War contested control of eastern Indonesian trade.
ayutthaya_foreign_embassies|1686-01-01|southeast_asia|diplomatic|Ayutthaya exchanged embassies with France and other foreign powers.
siamese_revolution|1688-06-01|southeast_asia|political|A court revolution curtailed French influence in Siam.
johor_riau_network|1699-09-03|southeast_asia|succession|A Johor succession crisis reshaped Malay maritime politics.
burmese_konbaung_foundation|1752-02-29|southeast_asia|political|Alaungpaya founded the Konbaung dynasty amid Burmese reunification.
fall_of_ayutthaya|1767-04-07|southeast_asia|military|Konbaung forces destroyed Ayutthaya after a prolonged siege.
siamese_thonburi_recovery|1767-12-28|southeast_asia|political|Taksin established a new center at Thonburi and reunited Siam.
nguyen_tay_son_war|1771-01-01|southeast_asia|social|The Tây Sơn rebellion overturned rival Vietnamese regimes.
philippine_galleon_reforms|1785-03-10|southeast_asia|commercial|The Royal Company of the Philippines sought to diversify colonial trade.
java_succession_wars|1749-12-11|southeast_asia|succession|Mataram's succession conflicts enabled deeper Company intervention.
burmese_sino_wars|1765-12-01|southeast_asia|military|Konbaung Burma resisted repeated Qing invasions.
penang_founding|1786-08-11|southeast_asia|commercial|The British established a base at Penang with Kedah's agreement.
singapore_treaty|1819-02-06|southeast_asia|commercial|Raffles concluded a treaty establishing a British post at Singapore.
tambora_eruption|1815-04-10|southeast_asia|environmental|Tambora's eruption caused regional devastation and global climatic effects.
cholera_bengal_spread|1817-08-01|southeast_asia|environmental|The first cholera pandemic spread from Bengal through maritime routes.

ming_tumu_crisis_aftermath|1450-01-01|east_asia|military|The aftermath of the Tumu Crisis destabilized the Ming northern frontier.
onan_war|1467-01-01|east_asia|succession|The Ōnin War fragmented Ashikaga authority and devastated Kyoto.
ming_great_wall_expansion|1474-01-01|east_asia|military|Ming governments expanded and connected northern frontier walls.
wokou_coastal_crisis|1555-01-01|east_asia|naval|Maritime raiding and illicit trade strained Ming coastal governance.
macau_lease|1557-01-01|east_asia|commercial|Portuguese merchants secured permanent residence at Macau.
oda_kyoto_entry|1568-10-18|east_asia|political|Oda Nobunaga entered Kyoto and reshaped shogunal politics.
nagasaki_port_opening|1571-01-01|east_asia|commercial|Nagasaki developed as a major port for overseas exchange.
ricci_beijing_mission|1601-01-24|east_asia|religious|Matteo Ricci entered Beijing and joined scholarly exchange at court.
tokugawa_shogunate|1603-03-24|east_asia|institutional|Tokugawa Ieyasu received the title of shogun.
qing_banner_expansion|1615-01-01|east_asia|institutional|The Eight Banners organized Manchu military and social power.
ming_peasant_rebellions|1628-01-01|east_asia|social|Fiscal stress and famine fueled large rebellions against Ming rule.
sakoku_edicts|1635-01-01|east_asia|commercial|Tokugawa maritime restrictions concentrated licensed foreign trade.
treaty_nerchinsk|1689-09-07|east_asia|diplomatic|Qing and Russian envoys fixed a negotiated frontier at Nerchinsk.
kangxi_atlas|1708-01-01|east_asia|exploration|Imperial surveys produced a new measured atlas of Qing domains.
forty_seven_ronin|1703-01-30|east_asia|social|The Akō vendetta provoked debate over loyalty and law.
white_lotus_rebellion|1796-01-01|east_asia|religious|White Lotus insurgency exposed Qing fiscal and military strains.
macartney_embassy|1793-09-14|east_asia|diplomatic|The Macartney embassy negotiated unsuccessfully for expanded British trade.
qianlong_ten_campaigns|1755-01-01|east_asia|military|Qianlong-era campaigns extended Qing power across Inner Asia.
korean_silhak_growth|1750-01-01|east_asia|technological|Silhak scholars promoted practical learning and institutional reform.
japanese_tenmei_famine|1782-01-01|east_asia|environmental|Cold weather and harvest failures caused the Tenmei famine.
opium_trade_pressure|1800-01-01|east_asia|commercial|Illegal opium imports increasingly distorted Qing maritime trade.
korean_catholic_community|1784-01-01|east_asia|religious|Korean scholars established a lay Catholic community.
edo_tenpo_famine_precursors|1810-01-01|east_asia|environmental|Recurring northern harvest failures foreshadowed later Tokugawa famine pressures.
ryukyu_satsuma_invasion|1609-04-05|east_asia|military|Satsuma invaded Ryukyu while preserving its tributary role.

aztec_triple_alliance_strain|1458-01-01|americas_caribbean|military|Mexica campaigns expanded tribute demands across central Mexico.
inca_northern_expansion|1463-01-01|americas_caribbean|military|Tawantinsuyu expanded northward under Topa Inca.
columbus_first_voyage|1492-10-12|americas_caribbean|exploration|Columbus's first voyage initiated sustained Atlantic contact.
treaty_tordesillas|1494-06-07|americas_caribbean|diplomatic|Iberian crowns negotiated a division of overseas claims.
fall_tenochtitlan|1521-08-13|americas_caribbean|military|Spanish and Indigenous allied forces captured Tenochtitlan.
smallpox_andean_crisis|1526-01-01|americas_caribbean|environmental|Epidemic disease preceded Spanish invasion and worsened Andean succession conflict.
fall_cusco|1533-11-15|americas_caribbean|military|Spanish forces occupied Cusco amid an Andean civil war.
new_laws_indies|1542-11-20|americas_caribbean|institutional|The New Laws attempted to restrict encomienda abuses.
mapuche_arauco_war|1553-12-25|americas_caribbean|military|Mapuche victory at Tucapel intensified the long Arauco War.
rio_de_janeiro_founding|1565-03-01|americas_caribbean|settlement|Portuguese colonists founded Rio de Janeiro amid Franco-Portuguese rivalry.
jamestown_founding|1607-05-14|americas_caribbean|settlement|Jamestown became the first enduring English settlement in Virginia.
quebec_founding|1608-07-03|americas_caribbean|settlement|Champlain founded Quebec as a St Lawrence trading center.
dutch_new_amsterdam|1624-01-01|americas_caribbean|commercial|New Netherland established a commercial colony around the Hudson.
beaver_wars|1640-01-01|americas_caribbean|military|Haudenosaunee expansion and the fur trade drove prolonged regional wars.
king_philips_war|1675-06-20|americas_caribbean|military|A devastating war engulfed Indigenous and colonial communities in New England.
salem_witch_trials|1692-02-01|americas_caribbean|religious|Witchcraft prosecutions exposed social tension in colonial Massachusetts.
bourbon_new_spain_reforms|1765-01-01|americas_caribbean|institutional|Bourbon reforms changed taxation, defense, and administration in Spanish America.
great_awakening|1739-01-01|americas_caribbean|religious|Revival preaching created new transcolonial religious networks.
seven_years_war_america|1754-05-28|americas_caribbean|military|The Ohio Valley conflict widened into a global imperial war.
pontiac_war|1763-05-07|americas_caribbean|military|An Indigenous coalition attacked British forts after the Seven Years' War.
tupac_amaru_rebellion|1780-11-04|americas_caribbean|social|A major Andean rebellion challenged colonial extraction and authority.
haitian_revolution|1791-08-22|americas_caribbean|social|Enslaved people in Saint-Domingue began a successful revolution.
latin_independence_crisis|1810-04-19|americas_caribbean|political|Juntas and insurgencies challenged Iberian rule across the Americas.
mississippi_bubble|1720-05-01|americas_caribbean|commercial|The collapse of Law's company destabilized French Atlantic finance.

tu_i_tonga_maritime_network|1450-01-01|pacific|commercial|Tongan voyaging sustained far-reaching exchange and political relationships.
nan_madol_transition|1500-01-01|pacific|political|Pohnpei's centralized Nan Madol order gave way to regional chiefly systems.
spanish_pacific_crossing|1521-03-06|pacific|exploration|Magellan's expedition completed the first recorded European Pacific crossing.
saavedra_moluccas_voyage|1527-10-31|pacific|exploration|Saavedra's expedition sought a return route across the Pacific.
legazpi_guam_passage|1565-01-22|pacific|exploration|Legazpi's fleet passed Guam while establishing a trans-Pacific route.
manila_galleon_route|1565-06-01|pacific|commercial|Urdaneta's return route enabled regular Manila-Acapulco voyages.
mendana_solomons|1568-02-07|pacific|exploration|Mendaña's expedition reached the Solomon Islands.
queiros_vanuatu|1606-05-03|pacific|exploration|Queirós's expedition reached islands in present-day Vanuatu.
tasman_new_zealand|1642-12-13|pacific|exploration|Tasman's voyage reached Aotearoa New Zealand.
dutch_tonga_contact|1616-05-10|pacific|exploration|Le Maire and Schouten recorded encounters in northern Tonga.
easter_island_roggeveen|1722-04-05|pacific|exploration|Roggeveen's expedition made the first recorded European visit to Rapa Nui.
tahiti_walllis_contact|1767-06-18|pacific|exploration|Wallis's expedition reached Tahiti amid violent and commercial encounters.
cook_first_pacific_voyage|1768-08-26|pacific|exploration|Cook's first voyage combined astronomy, surveying, and imperial reconnaissance.
cook_new_zealand_charting|1769-10-06|pacific|exploration|Cook's expedition charted much of Aotearoa's coastline.
maori_musket_trade|1807-01-01|pacific|technological|Expanding musket access began to alter Māori inter-iwi warfare.
hawaii_cook_contact|1778-01-18|pacific|exploration|Cook's ships made sustained recorded contact with Hawaiʻi.
hawaii_unification_campaign|1790-01-01|pacific|military|Kamehameha's campaigns used new weapons and alliances in island unification.
hawaii_kapu_abolition|1819-11-01|pacific|religious|Hawaiian rulers abolished the kapu system after Kamehameha's death.
tahiti_pomare_consolidation|1791-01-01|pacific|political|Pōmare I consolidated influence in Tahiti through warfare and foreign alliances.
missionaries_tahiti|1797-03-05|pacific|religious|London Missionary Society settlers arrived at Tahiti.
fiji_sandalwood_trade|1804-01-01|pacific|commercial|Foreign sandalwood traders intensified exchange and conflict in Fiji.
pacific_whaling_expansion|1800-01-01|pacific|commercial|Commercial whaling brought growing numbers of ships into Pacific ports.
new_south_wales_colony|1788-01-26|pacific|settlement|Britain established a penal colony at Sydney Cove.
pacific_el_nino_cycle|1790-01-01|pacific|environmental|ENSO variability repeatedly affected rainfall, crops, and voyaging conditions.
"""

PROFILE={
 "europe":("ile_de_france","france"),"africa":("middle_niger","songhai_kingdom"),
 "middle_east_india":("ottoman_anatolia","ottoman_empire"),"southeast_asia":("majapahit_java","majapahit_empire"),
 "east_asia":("ming_shandong_henan","ming_empire"),"americas_caribbean":("haudenosaunee_homelands","haudenosaunee_nations"),
 "pacific":("tongan_core_islands","tui_tonga_empire")}

def main():
 data=json.loads(PATH.read_text())
 row_ids={line.split("|",1)[0] for line in ROWS.strip().splitlines() if line.strip()}
 data["events"]=[e for e in data["events"] if not ({a["id"] for a in e.get("alternatives",[])}=={"state_adapts","pressure_redirected"})]
 existing={e["id"] for e in data["events"]}
 for line in ROWS.strip().splitlines():
  if not line.strip(): continue
  ident,when,region,category,evidence=line.split("|",4)
  if ident in existing: continue
  province,polity=PROFILE[region]
  data["events"].append({"id":ident,"date":when,"priority":40,"region":region,
   "categories":[category],"refs":[["polity",polity],["province",province]],"evidence":evidence,
   "alternatives":[
    {"id":"state_adapts","weight":3,"conditions":[{"kind":"entity_exists","entityId":polity}],
     "effects":[{"kind":"adjust_prosperity","targetId":province,"value":2},{"kind":"set_flag","targetId":ident+"_adapted","value":True}]},
    {"id":"pressure_redirected","weight":1,"conditions":[],
     "effects":[{"kind":"set_flag","targetId":ident+"_redirected","value":True}]}]})
 recurring={
  "sahel_drought_cycle":("years",18,"1810-01-01"),"monsoon_failure_india":("years",20,"1810-01-01"),
  "tambora_eruption":("years",5,"1820-04-10"),"japanese_tenmei_famine":("years",18,"1818-01-01"),
  "pacific_el_nino_cycle":("years",10,"1820-01-01"),"enclosure_acceleration":("years",20,"1810-01-01"),
  "great_awakening":("years",15,"1814-01-01")}
 for event in data["events"]:
  event.setdefault("title",event["id"].replace("_"," ").title())
  event.setdefault("triggerType","recurring_world_state" if event["id"] in recurring or "recurrence" in event else "dated_conditional")
  event.setdefault("evidenceClass","historical_synthesis")
  event.setdefault("outcomeSystems",sorted({{"adjust_treasury":"economy","adjust_relations":"diplomacy","set_controller":"control","complete_research":"technology","set_flag":"campaign_state","adjust_prosperity":"settlement_economy"}[x["kind"]] for a in event["alternatives"] for x in a["effects"]}))
  if event["id"] in recurring:
   unit,interval,until=recurring[event["id"]]; event["recurrence"]={"unit":unit,"interval":interval,"untilDate":until}
 data["events"].sort(key=lambda e:(e["date"],e["priority"],e["id"]))
 PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
 print(len(data["events"]))

if __name__=="__main__": main()
