"""Guard the hand-authored quest catalogues against destructive reseeding."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quest_seed", ROOT / "tooling/build_quest_breadth.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


class QuestSeedSafetyTests(unittest.TestCase):
    def prepare(self, target, *, story, local):
        scenario = target / "scenario"
        scenario.mkdir()
        campaign = scenario / "campaign-quests.json"
        source = json.loads((ROOT / "scenario/campaign-quests.json").read_text())
        if not story:
            source.pop("releaseStoryQuests", None)
        campaign.write_text(json.dumps(source, indent=2) + "\n")
        other = scenario / "local-random-quests.json"
        if local:
            shutil.copyfile(ROOT / "scenario/local-random-quests.json", other)
        return campaign, other

    def test_existing_authoring_is_untouched_even_if_only_one_catalogue_exists(self):
        for story, local in ((True, True), (True, False), (False, True)):
            with self.subTest(story=story, local=local), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                campaign, other = self.prepare(root, story=story, local=local)
                prior = (campaign.read_bytes(), other.read_bytes() if other.exists() else None)
                with patch.object(seed, "ROOT", root):
                    with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite authored quest catalogues"):
                        seed.main()
                self.assertEqual(prior, (campaign.read_bytes(), other.read_bytes() if other.exists() else None))

    def test_fresh_seed_works_once_and_subsequent_run_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign, other = self.prepare(root, story=False, local=False)
            original = json.loads(campaign.read_text())
            with patch.object(seed, "ROOT", root):
                seed.main()
                written = json.loads(campaign.read_text())
                self.assertEqual(original, {k: v for k, v in written.items() if k != "releaseStoryQuests"})
                self.assertEqual(len(seed.REGIONS) * len(seed.THEMES), len(written["releaseStoryQuests"]))
                family_rows = json.loads(other.read_text())["families"]
                self.assertEqual(len(seed.FAMILIES), len(family_rows))
                self.assertEqual(len(seed.FAMILIES) * 4, sum(len(f["variants"]) for f in family_rows))
                before = (campaign.read_bytes(), other.read_bytes())
                with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite authored quest catalogues"):
                    seed.main()
                self.assertEqual(before, (campaign.read_bytes(), other.read_bytes()))


if __name__ == "__main__":
    unittest.main()
