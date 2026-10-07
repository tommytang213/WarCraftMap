"""Scenario-neutral audio manifest/profile validation."""
import hashlib
import json
import wave
from pathlib import Path, PurePosixPath

STABLE = __import__("re").compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
KINDS = {"music", "ambience", "one_shot", "loop", "ui", "voice", "spatial"}
FORMATS = {"warcraft_stock", "wav", "mp3"}

class AudioValidationError(ValueError): pass

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def validate(manifest, profiles, import_root=None, *, profile_format="warcraftmap_audio_profiles_v1"):
    if manifest.get("format") != "warcraftmap_audio_manifest_v1" or manifest.get("formatVersion") != 1:
        raise AudioValidationError("unsupported audio manifest")
    categories = {x.get("id"): x for x in manifest.get("categories", [])}
    assets = {x.get("id"): x for x in manifest.get("assets", [])}
    if None in categories or len(categories) != len(manifest["categories"]): raise AudioValidationError("duplicate or invalid category IDs")
    if None in assets or len(assets) != len(manifest["assets"]): raise AudioValidationError("duplicate or invalid asset IDs")
    for ident in (*categories, *assets):
        if not isinstance(ident, str) or not STABLE.fullmatch(ident): raise AudioValidationError(f"invalid stable ID: {ident}")
    for ident, row in categories.items():
        if row.get("kind") not in KINDS or not 0 <= row.get("priority", -1) <= 100: raise AudioValidationError(f"{ident}: invalid category")
        if row.get("maximumConcurrent", 0) < 1 or row.get("cooldownMs", -1) < 0 or row.get("fadeInMs", -1) < 0 or row.get("fadeOutMs", -1) < 0: raise AudioValidationError(f"{ident}: invalid playback bounds")
        if row.get("interrupt") not in {"never", "lower_priority", "same_or_lower", "replace_category"}: raise AudioValidationError(f"{ident}: invalid interruption policy")
    imported = decoded = 0; locators = {}; import_hashes = {}
    for ident, row in assets.items():
        if row.get("categoryId") not in categories: raise AudioValidationError(f"{ident}: unknown category")
        technical = row.get("technical", {})
        if row.get("source") not in {"stock", "import"}: raise AudioValidationError(f"{ident}: invalid source")
        if technical.get("format") not in FORMATS or technical.get("durationMs", 0) <= 0: raise AudioValidationError(f"{ident}: invalid format or duration")
        if technical.get("sampleRateHz") not in {22050, 32000, 44100, 48000}: raise AudioValidationError(f"{ident}: incompatible sample rate")
        if technical.get("channels") not in {1, 2}: raise AudioValidationError(f"{ident}: incompatible channels")
        if not -60 <= technical.get("integratedLufs", 1) <= -10 or not -12 <= technical.get("peakDbfs", 1) <= 0: raise AudioValidationError(f"{ident}: loudness out of bounds")
        looping = technical.get("loop")
        if looping and not (0 <= technical.get("loopStartMs", -1) < technical.get("loopEndMs", 0) <= technical["durationMs"]): raise AudioValidationError(f"{ident}: invalid loop metadata")
        if looping != (categories[row["categoryId"]]["kind"] in {"music", "ambience", "loop"}) and categories[row["categoryId"]]["kind"] in {"ambience", "loop"}: raise AudioValidationError(f"{ident}: loop/category mismatch")
        if technical.get("encodedBytes", -1) < 0 or technical.get("decodedBytes", -1) < 0: raise AudioValidationError(f"{ident}: invalid size metadata")
        for field in ("historicalFit", "provenance", "license", "attribution", "intendedUse"):
            if not row.get(field): raise AudioValidationError(f"{ident}: missing {field}")
        locator = row.get("locator")
        if locator in locators: raise AudioValidationError(f"duplicate audio locator: {ident}/{locators[locator]}")
        locators[locator] = ident
        if row.get("source") == "import":
            path = PurePosixPath(locator)
            if path.is_absolute() or ".." in path.parts or path.suffix.lower().removeprefix(".") != technical["format"]: raise AudioValidationError(f"{ident}: unsafe import path")
            file_path = Path(import_root or Path.cwd()) / path
            if not file_path.is_file(): raise AudioValidationError(f"{ident}: missing import")
            raw = file_path.read_bytes()
            if len(raw) != technical["encodedBytes"] or hashlib.sha256(raw).hexdigest() != technical.get("sha256"): raise AudioValidationError(f"{ident}: import size or hash mismatch")
            if technical["sha256"] in import_hashes: raise AudioValidationError(f"duplicate imported audio: {ident}/{import_hashes[technical['sha256']]}")
            import_hashes[technical["sha256"]] = ident
            samples = raw
            if technical["format"] == "wav":
                try:
                    with wave.open(str(file_path), "rb") as decoded_wave:
                        if decoded_wave.getframerate() != technical["sampleRateHz"] or decoded_wave.getnchannels() != technical["channels"]:
                            raise AudioValidationError(f"{ident}: WAV metadata mismatch")
                        actual_ms = round(decoded_wave.getnframes() * 1000 / decoded_wave.getframerate())
                        if abs(actual_ms - technical["durationMs"]) > 10: raise AudioValidationError(f"{ident}: duration mismatch")
                        samples = decoded_wave.readframes(decoded_wave.getnframes())
                except (wave.Error, EOFError) as error: raise AudioValidationError(f"{ident}: malformed WAV import") from error
            elif technical["format"] == "mp3" and not (raw.startswith(b"ID3") or (len(raw)>1 and raw[0] == 0xff and raw[1] & 0xe0 == 0xe0)):
                raise AudioValidationError(f"{ident}: malformed MP3 import")
            if not samples.strip(b"\0"): raise AudioValidationError(f"{ident}: silent import")
            imported += len(raw); decoded += technical["decodedBytes"]
    budgets = manifest.get("budgets", {})
    if imported > budgets.get("maximumImportedBytes", -1) or decoded > budgets.get("maximumDecodedBytes", -1): raise AudioValidationError("audio import or memory budget exceeded")
    if not 1 <= budgets.get("maximumActiveChannels", 0) <= 64: raise AudioValidationError("invalid active-channel budget")
    if profiles.get("format") != profile_format: raise AudioValidationError("unsupported scenario profiles")
    rows = [profiles.get("fallbackProfile"), *profiles.get("profiles", [])]
    refs = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"): raise AudioValidationError("invalid profile")
        if set(row.get("match", {})) - {"physical_map_id", "region_id", "settlement_type", "travel", "combat", "modal", "event"}: raise AudioValidationError(f"{row['id']}: invalid context selector")
        for category, choices in row.get("layers", {}).items():
            if category not in categories or not choices: raise AudioValidationError(f"{row['id']}: invalid layer")
            if len(choices) != len(set(choices)): raise AudioValidationError(f"{row['id']}: duplicate choice")
            for asset in choices:
                if asset not in assets or assets[asset]["categoryId"] != category: raise AudioValidationError(f"{row['id']}: incompatible asset reference {asset}")
                refs.add(asset)
    for category, asset in manifest.get("fallbacks", {}).items():
        if category not in categories or (asset is not None and (asset not in assets or assets[asset]["categoryId"] != category)): raise AudioValidationError("invalid fallback")
        if asset: refs.add(asset)
    for asset in profiles.get("feedback", {}).values():
        if asset not in assets: raise AudioValidationError(f"invalid feedback reference {asset}")
        refs.add(asset)
    orphaned = set(assets) - refs
    if orphaned: raise AudioValidationError("orphaned audio assets: " + ", ".join(sorted(orphaned)))
    return {"categories": categories, "assets": assets, "importedBytes": imported, "decodedBytes": decoded}
