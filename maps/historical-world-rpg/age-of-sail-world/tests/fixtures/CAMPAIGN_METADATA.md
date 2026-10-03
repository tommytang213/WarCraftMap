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
