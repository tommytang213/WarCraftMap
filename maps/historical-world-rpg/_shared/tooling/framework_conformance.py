"""Content vectors for the same production-adapter execution contract."""
import argparse
import json
from pathlib import Path
import re
import shutil


def assemble_contract(project, destination):
    vector = json.loads((project / "conformance.json").read_text())
    goods = json.loads((project / "scenario/economy/global-goods.json").read_text())
    selected_good = next(row for row in goods["goods"] if row["id"] == vector["good"])
    vector["goodBasePrice"] = selected_good["basePriceMinor"]
    lines = ["package ConformanceData", ""]
    for key, value in vector.items():
        name = "CONTRACT_" + re.sub(r"([a-z])([A-Z])", r"\1_\2", key).upper()
        kind = "string" if isinstance(value, str) else "int" if isinstance(value, int) else "real"
        lines.append(f"public constant {kind} {name} = {json.dumps(value)}")
    (destination / "ConformanceData.wurst").write_text("\n".join(lines) + "\n")


def mutate_content(source, destination):
    """Rename all authored identities, including reference keys and filenames.

    The replacement namespace is supplied as data by the fixture itself. No
    generated code or framework source is edited by this metamorphic test.
    """
    rules = json.loads((source / "mutation.json").read_text())
    def rename(value):
        for before, after in rules["replacements"].items():
            value = value.replace(before, after)
        return value
    for path in source.rglob("*"):
        if not path.is_file() or any(part in {"_build", ".wurst", "__pycache__"} for part in path.relative_to(source).parts):
            continue
        target = destination / rename(path.relative_to(source).as_posix())
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            target.write_text(rename(path.read_text()))
        else:
            shutil.copy2(path, target)
    goods_path = destination / rules["goodsPath"]
    goods = json.loads(goods_path.read_text())
    for good in goods["goods"]:
        good["basePriceMinor"] *= rules["priceMultiplier"]
    goods_path.write_text(json.dumps(goods, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.destination.exists():
        parser.error("mutation destination must not exist")
    mutate_content(args.source, args.destination)


if __name__ == "__main__":
    main()
