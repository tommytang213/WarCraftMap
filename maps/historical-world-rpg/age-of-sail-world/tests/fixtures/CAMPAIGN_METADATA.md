# Campaign metadata regression fixtures

`malformed-rc2-war3campaign.w3f.hex` reproduces the old writer: format v1,
flags 1 despite W3X maps, a non-v1 `mapVersion` integer, two-string chapter
records, and integer/title/path flow records. The corrected parser rejects it.

`war3net-campaign-3.0.0-war3campaign.w3f.hex` is `war3campaign.w3f` extracted
unchanged from War3Net's `campaign_3.0.0.w3n` test fixture at commit
`18e88f0e1f67e6b16870dcbcd827740275fe2173`. The source W3N SHA-256 is
`aac17d7739cf181e59846808960d0ccdbf0ccadbd68e6b18df0cbdf5079f1530` and the
extracted metadata SHA-256 is
`b00ad4d99905b82c37c4b0d9146f88b1d0b6cce4b1e3e140eeef8e88d6522654`.
War3Net is MIT licensed. Its fixture begins with an MPQ header at byte zero and
has no map-style HM3W prefix or signature footer.

Reference:
https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/tests/War3Net.TestTools.UnitTesting/TestData/Campaigns/campaign_3.0.0.w3n

`war3net-map-3.0.0-war3map.w3i.hex` is the unchanged 381-byte W3I from
`patch_3.0.0_1.w3x` inside that same campaign. SHA-256:
`82c6030751e491f98ba4429363b546b9dc59d0623cf3ff3b19babd6361b475ac`.
It uses format 39 and game version 3.0.0.24268. It is a JASS reference map,
not the Lua authoring profile and not evidence that this campaign was launched.

`artifact-704-bootstrap.lua.gz` and `artifact-704-europe-units.doo.gz` are
unchanged decoded members from the actual [Actions #704 artifact](https://github.com/tommytang213/WarCraftMap/actions/runs/37427137021),
source commit `5a324d75424d03f5eb1694954ac00b093d78754e`. They are negative
regression fixtures, never build inputs. The downloaded W3N SHA-256 is
`c8c0d14414402bd28a51d3d3f946b9a408020d67687b8258063443c64c9588d1`.
Decompressed fixture SHA-256 values:

- Bootstrap `war3map.lua` (272909 bytes): `c17afea376ab8b813cfb0386894a838bdf422c7014de5a38ecf63db4edc92dbe`.
- Europe West `war3mapUnits.doo` (9895 bytes): `baa0141352d4b3f23559761dfaf4dce21a18269ace494c0a68b9d493d31a8a02`.

The Lua lacks Blizzard initialization. The unit records omit the v8/11
item-table field, shifting later fields; an extra random payload word hid the
size error. The independent reader sees item-table ID 0 in a map with no item
tables. See the pinned [UnitData reader](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Serialization/Binary/Widget/UnitData.cs)
and [MapInfo reader](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Serialization/Binary/Info/MapInfo.cs).
