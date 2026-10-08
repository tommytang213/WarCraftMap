import copy
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import struct
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_acceptance", PROJECT / "tooling/runtime_acceptance.py")
runtime = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runtime)


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_malformed_source_manifest_cannot_be_treated_as_readiness_evidence(self):
        original = json.loads(runtime.MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            variants = ["pass", [], {**original, "systems": ["trade"]},
                        {**original, "smokeJourneys": "pass"},
                        {**original, "smokeJourneys": ["pass"]},
                        {**original, "smokeJourneys": [{"id": "fixture", "systems": "trade"}]}]
            for field in ("releaseRequired", "simulationOnly"):
                for value in (None, "false", "true", 0, 1):
                    changed = copy.deepcopy(original)
                    changed["systems"][0][field] = value
                    variants.append(changed)
            for value in variants:
                path.write_text(json.dumps(value))
                with self.subTest(manifest=value), self.assertRaises(runtime.RuntimeAcceptanceError):
                    runtime.audit_sources(path)
        for item in ("pass", {"path": 1, "contains": ["trade"]},
                     {"path": "wurst/PlayableTrade.wurst", "contains": "trade"}):
            with self.subTest(item=item), self.assertRaises(runtime.RuntimeAcceptanceError):
                runtime._evidence_ok([item], "fixture")

    def test_malformed_real_client_configuration_is_rejected_without_attribute_error(self):
        for value in ("pass", [], None):
            with self.subTest(value=value), patch.object(runtime, "_read", return_value=json.dumps(value)):
                with self.assertRaisesRegex(runtime.RuntimeAcceptanceError, "real-client release configuration"):
                    runtime.audit_sources()

    def test_malformed_built_map_metadata_is_rejected_without_attribute_error(self):
        source = PROJECT / "map/AgeOfSailWorld.w3x"
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "malformed.w3x"
            cases = [(name, value) for name in ("runtime/scenario-runtime.json", "runtime/physical-map.json")
                     for value in ("pass", [], None)]
            cases.append(("runtime/scenario-runtime.json", {"ids": "pass"}))
            for name, value in cases:
                with self.subTest(name=name, value=value):
                    metadata = {"runtime/scenario-runtime.json": {}, "runtime/physical-map.json": {}}
                    metadata[name] = value
                    with zipfile.ZipFile(fixture, "w") as archive:
                        for binary in ("war3map.w3e", "war3map.wpm", "war3mapUnits.doo", "war3map.w3i", "war3map.shd"):
                            archive.write(source / binary, binary)
                        archive.writestr("war3map.lua", "function config() end\nfunction main() InitBlizzard() end")
                        for member, document in metadata.items():
                            archive.writestr(member, json.dumps(document))
                    with self.assertRaisesRegex(runtime.RuntimeAcceptanceError, "metadata must be JSON objects"):
                        runtime.inspect_built_map(fixture)

    def test_all_materialized_maps_pass_structure_including_bounded_encounters(self):
        # Exercise production generation/localization/materialization for every
        # configured map. Lua is a fixture: this is binary integration coverage,
        # not compilation, execution, or real-client playability evidence.
        sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
        from package_wurst_campaign import load_campaign_config, validate_campaign, _localize_runtime, _write_campaign
        from package_wurst_map import load_config, generate
        from materialize_physical_map import materialize, _wpm
        from warcraft_campaign import write_mpq
        import package_release_candidate as release
        import verify_ci_release_artifact as upload
        from unittest.mock import patch
        campaign = load_campaign_config(PROJECT / "physical-maps.json")
        world = validate_campaign(campaign)
        identity = runtime.source_identity(PROJECT, "a" * 40)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = root / "authority"
            generate(load_config(campaign.map_config_path), authority)
            encounters = 0
            built = []
            for physical in campaign.maps:
                with self.subTest(map_id=physical.id):
                    generated = root / physical.id / "generated"
                    shutil.copytree(authority, generated)
                    _localize_runtime(campaign, world, physical, generated)
                    data = json.loads((generated / "scenario-runtime.json").read_text())
                    source = root / physical.id / "source"
                    shutil.copytree(physical.source_map, source)
                    materialize(PROJECT, source, generated, physical, data)
                    (source / "runtime/scenario-runtime.json").write_text(json.dumps(data))
                    (source / "runtime/build-identity.json").write_text(json.dumps(identity))
                    script = ("function config() end\nfunction main() InitBlizzard() TimerStart() showPage() ChangeLevel(path, true) end"
                              if physical.bootstrap else self.executable_script())
                    (source / "war3map.lua").write_text(script)
                    fixture = root / (physical.id + ".w3x")

                    def package():
                        files = {path.relative_to(source).as_posix(): path.read_bytes()
                                 for path in sorted(source.rglob("*")) if path.is_file()}
                        files["(listfile)"] = ("\r\n".join(sorted(files)) + "\r\n").encode()
                        write_mpq(fixture, files)

                    package()
                    result = runtime.inspect_built_map(fixture, physical.id, physical.bootstrap)
                    self.assertEqual([], result["failures"])
                    built.append((physical, fixture))
                    if physical.id == "europe_west":
                        shadow = source / "war3map.shd"
                        correct_shadow = shadow.read_bytes()
                        shadow.write_bytes(bytes(64 * 64 * 16))
                        package()
                        self.assertIn("shadow raster does not match terrain",
                                      runtime.inspect_built_map(fixture, physical.id, False)["failures"])
                        shadow.write_bytes(correct_shadow)
                        package()
                    if physical.bootstrap:
                        self.assertFalse(data["settlementDefinitions"])
                        self.assertFalse(data["physicalBoundaries"])
                        # Localized JSON cannot hide global initialization in
                        # the compiled bootstrap, even under a renamed helper.
                        unrelated = ('function initGlobal(x, trace) end\n' + script.replace(
                            'showPage()', 'showPage() initGlobal(globalData, '
                            '"when calling registerSettlement in ScenarioData, line 12")'))
                        (source / "war3map.lua").write_text(unrelated)
                        package()
                        broken = runtime.inspect_built_map(fixture, physical.id, True)
                        self.assertIn("bootstrap contains regional registration: registerSettlement", broken["failures"])
                        (source / "war3map.lua").write_text(script)
                        package()
                    if not physical.bootstrap and not physical.terrain_ids:
                        encounters += 1
                        paths = (source / "war3map.wpm").read_bytes()[16:]
                        # The center admits ships; every outer pixel blocks them.
                        self.assertEqual(0x0a, paths[128 * 256 + 128])
                        for edge in (paths[:256], paths[-256:], paths[::256], paths[255::256]):
                            self.assertEqual({0x4e}, set(edge))
                        # Reproduce the CI failure with the old uniform arena.
                        pathing = source / "war3map.wpm"
                        valid_pathing = pathing.read_bytes()
                        pathing.write_bytes(_wpm(64, 64, [2] * 4096))
                        package()
                        broken = runtime.inspect_built_map(fixture, physical.id, False)
                        self.assertIn("physical terrain/pathing is blank or placeholder-only", broken["failures"])
                        pathing.write_bytes(valid_pathing)
                        package()
            self.assertGreater(encounters, 0)
            # Reopen every nested map through the production RC gate, including
            # origin destinations, assignments and the full transition set.
            archive = root / "campaign.w3n"
            _write_campaign(archive, campaign, built)
            with self.assertRaisesRegex(release.PackagingError, "requires a full source revision"):
                release.verify_campaign_runtime(archive, campaign)
            result = release.verify_campaign_runtime(archive, campaign, revision=identity["sourceRevision"],
                                                     source_tree_sha256=identity["sourceTreeSha256"])
            self.assertEqual("pass", result["status"])
            self.assertEqual("completed", result["executionStatus"])
            self.assertEqual("not_run", result["runtimeExecutionStatus"])
            self.assertEqual(identity["sourceRevision"], result["sourceRevision"])
            self.assertIn("compiled_text_static_heuristic", result["evidenceLevels"])
            self.assertEqual(len(campaign.maps), len(result["maps"]))
            self.assertEqual(len(campaign.boundaries), result["transitions"])
            bound = result
            self.assertEqual(release.sha(archive), bound["artifactSha256"])
            self.assertTrue(all(row["sourceRevision"] == identity["sourceRevision"] for row in bound["maps"]))
            self.assertEqual([release.sha(path) for _, path in built],
                             [row["artifactSha256"] for row in bound["maps"]])
            for revision, tree in (("b" * 40, identity["sourceTreeSha256"]), ("a" * 40, "0" * 64)):
                with self.assertRaisesRegex(release.PackagingError, "artifact source identity mismatch"):
                    release.verify_campaign_runtime(archive, campaign, revision=revision, source_tree_sha256=tree)
            # Checking nested maps is insufficient if the campaign browser
            # cannot read the W3N itself, even with intact revision metadata.
            damaged = root / "damaged-campaign.w3n"
            members = release.MpqReader(archive).members()
            members["war3campaign.w3f"] = b"invalid campaign metadata"
            write_mpq(damaged, members)
            with self.assertRaisesRegex(release.PackagingError, "campaign inspection"):
                release.verify_campaign_runtime(damaged, campaign, revision=identity["sourceRevision"],
                                                source_tree_sha256=identity["sourceTreeSha256"])
            self.assertEqual(len(campaign.maps) + 2, len(release.normalized_campaign(archive, campaign)))
            # Run the real ZIP/upload verifiers on this binary integration
            # fixture, without claiming that its synthetic Lua was executed.
            config = release.load_release_config()
            payload = archive.read_bytes()
            revision = "a" * 40
            manifest = {
                "format": release.MANIFEST_FORMAT,
                "releaseCandidateId": config["releaseCandidateId"],
                "sourceRevision": revision,
                "schemaCompatibility": {"supportedSaveSchemas": [1, 2, 3, 4, 5, 6, 7, 8]},
                "artifacts": [{"kind": "campaign", "archivePath": config["archive"]["campaignPath"],
                               "bytes": len(payload), "sha256": release.sha_bytes(payload)}]
                             + release._campaign_rows(archive, campaign),
            }
            candidate = root / "candidate.zip"
            from wurst_execution_fixture import passing_evidence
            wurst_report, wurst_log = passing_evidence(revision)
            trace_fixture = {"fixture": "binary structure only; exhaustive traceability tested separately"}
            execution_payloads = {"Metadata/wurst-execution.json": release.canonical(wurst_report),
                                  "Metadata/wurst-execution.log": wurst_log,
                                  "Metadata/requirement-traceability.json": release.canonical(trace_fixture)}
            manifest["artifacts"] += [
                {"kind": "execution-evidence", "archivePath": name,
                 "bytes": len(value), "sha256": release.sha_bytes(value)}
                for name, value in execution_payloads.items()]
            release._write_zip(candidate, {
                **execution_payloads,
                config["archive"]["campaignPath"]: payload,
                config["archive"]["manifestPath"]: release.canonical(manifest),
                config["archive"]["provenancePath"]: release.canonical({
                    "format": release.PROVENANCE_FORMAT, "sourceRevision": revision,
                    "gates": {"wurstExecution": "pass", "requirementTraceability": "pass"}}),
            })
            evidence = root / "artifact-evidence.json"
            with patch.object(release.traceability, "validate_final", return_value=trace_fixture), \
                 patch.object(sys, "argv", ["verify", str(candidate), "--source-revision", revision,
                                           "--evidence", str(evidence)]):
                with self.assertRaisesRegex(release.PackagingError, "automated candidate acceptance failed"):
                    upload.main()
            self.assertFalse(evidence.exists())
            # An intact campaign does not excuse a false nested-map checksum
            # in the surrounding release manifest.
            manifest["artifacts"][1]["sha256"] = "0" * 64
            with zipfile.ZipFile(candidate) as reader:
                payloads = {name: reader.read(name) for name in reader.namelist()}
            payloads[config["archive"]["manifestPath"]] = release.canonical(manifest)
            release._write_zip(candidate, payloads)
            with self.assertRaisesRegex(release.PackagingError, "physical-map metadata/checksums"):
                release.verify_release_archive(candidate, config)

    def test_identically_malformed_canonical_and_packaged_w3i_still_fail(self):
        current = (PROJECT / "map/AgeOfSailWorld.w3x/war3map.w3i").read_bytes()
        malformed = bytearray(current)
        # Corrupt the parsed player count while leaving source and output equal.
        marker = struct.pack("<6i", 1, 3, 1, 1650, 3000, 1250)
        player_count_at = malformed.index(marker) + len(marker)
        struct.pack_into("<i", malformed, player_count_at, 0)
        original_project = runtime.PROJECT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); canonical = root / "map/AgeOfSailWorld.w3x"
            canonical.mkdir(parents=True); (canonical / "war3map.w3i").write_bytes(malformed)
            source = PROJECT / "map/AgeOfSailWorld.w3x"
            fixture = root / "same-malformed.w3x"
            w3e = (source / "war3map.w3e").read_bytes(); offset = 13
            ground = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + ground * 4
            cliffs = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + cliffs * 4
            width, height = struct.unpack_from("<II", w3e, offset)
            with zipfile.ZipFile(fixture, "w") as archive:
                for name in ("war3map.w3e", "war3map.wpm", "war3mapUnits.doo", "war3map.shd"):
                    archive.write(source / name, name)
                archive.writestr("war3map.w3i", malformed)
                archive.writestr("war3map.lua", self.executable_script())
                archive.writestr("runtime/scenario-runtime.json", json.dumps({
                    "ids": {"polities": ["fixture"]}, "regionalGeography": ["fixture"]}))
                archive.writestr("runtime/physical-map.json", json.dumps({
                    "physicalMapId": "fixture", "bootstrap": False,
                    "terrain": {"width": width - 1, "height": height - 1}}))
            runtime.PROJECT = root
            try:
                result = runtime.inspect_built_map(fixture, "fixture", False)
                self.assertEqual("fail", result["status"])
                self.assertTrue(any("invalid player count" in x for x in result["failures"]))
            finally:
                runtime.PROJECT = original_project

    def test_w3i_layout_is_validated_independently_of_version_labels(self):
        current = (PROJECT / "map/AgeOfSailWorld.w3x/war3map.w3i").read_bytes()
        info = runtime.validate_w3i_structure(current)
        self.assertEqual((33, 6116, (3, 0, 0, 24268)),
                         (info["format"], info["editorVersion"], info["gameVersion"]))
        generated = bytearray(current)
        struct.pack_into("<i4i", generated, 0, 31, 79, 6052, 0, 0)
        struct.pack_into("<2i", generated, 20, 0, 0)
        # v31 ends its common header at gameDataVersion; forced camera zoom was
        # introduced in v32 and therefore must not be parsed from player data.
        camera_marker = struct.pack("<6i", 1, 3, 1, 1650, 3000, 1250)
        camera_at = generated.index(camera_marker) + 12
        del generated[camera_at:camera_at + 12]
        generated_info = runtime.validate_w3i_structure(bytes(generated))
        self.assertEqual((31, (0, 0, 0, 0)),
                         (generated_info["format"], generated_info["gameVersion"]))
        malformed = bytearray(current)
        struct.pack_into("<i", malformed, 0, 30)
        with self.assertRaisesRegex(runtime.MapInfoError, "no supported structural parser"):
            runtime.validate_w3i_structure(bytes(malformed))

    def test_w3i_playable_dimensions_account_for_camera_bound_margins(self):
        source = PROJECT / "map/AgeOfSailWorld.w3x"
        info = runtime.validate_w3i_structure((source / "war3map.w3i").read_bytes())
        self.assertEqual((6, 6, 4, 8), info["cameraComplements"])
        self.assertEqual((52, 52), (info["playableWidth"], info["playableHeight"]))

    def test_w3i_checks_player_slot_records_and_complete_metadata_layout(self):
        current = (PROJECT / "map/AgeOfSailWorld.w3x/war3map.w3i").read_bytes()
        marker = struct.pack("<6i", 1, 3, 1, 1650, 3000, 1250)
        player_at = current.index(marker) + len(marker) + 4
        for offset, value in ((player_at, -1), (player_at, 24),
                              (player_at + 4, 2), (player_at + 12, 2)):
            with self.subTest(offset=offset, value=value):
                malformed = bytearray(current)
                struct.pack_into("<i", malformed, offset, value)
                with self.assertRaisesRegex(runtime.MapInfoError, "player"):
                    runtime.validate_w3i_structure(malformed)
        for value in (current[:-1], current + b'\0', current[:28] + b'\xff' + current[29:]):
            with self.subTest(value=value[-12:]):
                with self.assertRaises(runtime.MapInfoError):
                    runtime.validate_w3i_structure(value)

    def executable_script(self):
        calls = sorted({call for required, _ in runtime.COMPILED_TEXT_REQUIREMENTS.values()
                        for call in required})
        commands = sorted({command for _, required in runtime.COMPILED_TEXT_REQUIREMENTS.values()
                           for command in required})
        return ("function config() end\nfunction main() InitBlizzard()\n" + "\n".join(f"  {call}()" for call in calls) +
                "\n" + "\n".join(f'  registry:register("{command}", handler)'
                                   for command in commands) + "\nend\n")

    def test_manifest_covers_required_player_systems_and_reports_stage_distinctions(self):
        report = runtime.audit_sources()
        ids = {row["id"] for row in report["systems"] if row["releaseRequired"]}
        self.assertTrue({"campaign_launch", "origin_selection", "country_diplomacy", "trade",
                         "army_fleet_control", "city_capture", "garrisons", "administration",
                         "heroes", "inventory_equipment", "technology_institutions",
                         "quests_journal", "treasures_discovery", "save_autosave_load",
                         "cross_map_travel", "world_map", "remote_management",
                         "government_rewards", "religion", "piracy"} <= ids)
        self.assertEqual(list(runtime.STAGES), report["stages"])
        self.assertEqual("fail", report["status"])
        self.assertFalse(report["candidateReady"])
        self.assertEqual("pass", report["evidenceLevels"]["sourceStatic"]["status"])
        self.assertEqual("not_run", report["executionStatus"])

    def test_trade_has_real_runtime_entry_and_release_evidence(self):
        report = runtime.audit_sources()
        trade = next(row for row in report["systems"] if row["id"] == "trade")
        self.assertTrue(all(trade["sourceChecks"][stage] for stage in runtime.STAGES[:-1]))
        self.assertFalse(trade["stages"]["runtimeIntegrated"])
        self.assertFalse(trade["stages"]["releaseValidated"])
        self.assertEqual([], trade["diagnostics"])
        self.assertTrue(any(message.startswith("trade:") for message in report["failures"]))

    def test_country_diplomacy_and_government_rewards_use_real_release_entry_points(self):
        report = runtime.audit_sources()
        rows = {row["id"]: row for row in report["systems"]}
        for system_id in ("country_diplomacy", "government_rewards"):
            self.assertTrue(all(rows[system_id]["sourceChecks"][stage]
                                for stage in runtime.STAGES[:-1]))
            self.assertFalse(rows[system_id]["stages"]["releaseValidated"])
            self.assertEqual([], rows[system_id]["diagnostics"])
        self.assertFalse(any("RUNTIME-MISSING-COUNTRY-DIPLOMACY" in failure or
                             "RUNTIME-MISSING-GOVERNMENT-REWARDS" in failure
                             for failure in report["failures"]))

    def test_compiled_artifact_requires_executable_calls_and_registrations(self):
        script = self.executable_script()
        self.assertEqual("pass", runtime.verify_compiled_script(script)["status"])
        result = runtime.verify_compiled_script(script.replace('  registry:register("origin", handler)', ""))
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("origin_selection" in x for x in result["failures"]))

    def test_inlined_origin_wrapper_requires_real_registration_and_operations(self):
        # PR #423: the pinned optimizer expands registerOriginSelection into
        # Bootstrap. Its stack annotation survives, but it is no longer a call.
        # Model the emitted alias and call, including the actual handler value.
        registration = ('CommandRegistry_CommandRegistry_register(commands, "origin", "citizenship", '
                        '"origin [page N|search WORDS|choose ID]", "Choose your origin.", '
                        '"Confirm one immutable origin.", 0, 99, visibility, handler, '
                        '"when calling register in CommandRouter, line 486")')
        alias = 'CommandRegistry.CommandRegistry_register = CommandRegistry_CommandRegistry_register'
        definition = 'function CommandRegistry_CommandRegistry_register(self, command, ...) end'
        annotation = ('wurst_stack[wurst_stack_depth] = '
                      '"when calling registerOriginSelection in Bootstrap, line 99"')
        script = (definition + '\n' + alias + '\n' + self.executable_script()
                  .replace('  registerOriginSelection()', '')
                  .replace('registry:register("origin", handler)', annotation + '\n' + registration))
        calls, commands = runtime._compiled_call_evidence(script)
        self.assertNotIn("registerOriginSelection", calls)
        self.assertIn("origin", commands)
        self.assertEqual([], runtime.verify_compiled_script(script)["failures"])
        # Neither the inlining annotation nor a wrapper call can substitute for
        # the actual command registration, catalogue setup, or physical travel.
        broken_scripts = [script.replace(registration, replacement) for replacement in
                          ('', '-- ' + registration, 'registerOriginSelection()',
                           'local note = ' + json.dumps(registration))]
        broken_scripts += [script.replace(alias, ''), script.replace(definition, '')]
        broken_scripts += [script.replace(f'  {operation}()', '') for operation in
                           ('configureGeneratedOrigins', 'compatLoadPhysicalMap')]
        for broken in broken_scripts:
            with self.subTest(script=broken):
                failures = runtime.verify_compiled_script(broken)["failures"]
                self.assertTrue(any(failure.startswith("origin_selection:") for failure in failures))

    def test_classes_commands_and_markers_without_bootstrap_calls_fail(self):
        marker_only = '\n'.join(
            ["function config() end\nfunction main() InitBlizzard() end", "-- registerOriginSelection initializePlayableCampaignRuntime",
             'local marker = "commands.register(\\"origin\\")"',
             "function registerOriginSelection() end"])
        result = runtime.verify_compiled_script(marker_only)
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("production calls absent" in x for x in result["failures"]))

    def test_inlined_religion_requires_actual_registration_and_initialization(self):
        script = self.executable_script()
        # The wrapper disappears in the production Lua after registration was
        # moved out of Bootstrap, while the domain operations remain calls.
        self.assertNotIn("configureGeneratedReligion", script)
        self.assertEqual("pass", runtime.verify_compiled_script(script)["status"])
        for operation in ("registerFaith", "setCharacterFaith", "setInfluence"):
            broken = script.replace(f"  {operation}()", "")
            broken += '\nwurst_stack[wurst_stack_depth] = "when calling configureGeneratedReligion in CampaignRegistration, line 119"\n'
            result = runtime.verify_compiled_script(broken)
            self.assertEqual("fail", result["status"])
            self.assertTrue(any(f"religion: production calls absent: {operation}" in failure
                                for failure in result["failures"]))

    def test_compiled_lua_payload_budgets_reject_pathological_line(self):
        result = runtime.verify_compiled_script("function config() end\nfunction main() InitBlizzard() " +
                                                "x" * (runtime.MAX_LUA_LINE_BYTES + 1) + " end")
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("line exceeds" in x for x in result["failures"]))

    def test_renamed_compiler_calls_and_registry_aliases_are_static_evidence(self):
        script = '''function renamed(a, trace) end
function CommandRegistry_TO(self, command, trace) end
CommandRegistry.CommandRegistry_register = CommandRegistry_TO
renamed(value, "when calling configureGeneratedTrade in Bootstrap, line 237")
CommandRegistry_TO(registry, "trade", "when calling register in PlayableTrade, line 442")
'''
        calls, commands = runtime._compiled_call_evidence(script)
        self.assertIn("configureGeneratedTrade", calls)
        self.assertEqual({"trade"}, commands)
        for fake in (
            '-- renamed(value, "when calling configureGeneratedTrade in Bootstrap, line 237")',
            'local note = "when calling configureGeneratedTrade in Bootstrap, line 237"',
            'missing(value, "when calling configureGeneratedTrade in Bootstrap, line 237")',
        ):
            calls, commands = runtime._compiled_call_evidence('function renamed(a, trace) end\n' + fake)
            self.assertNotIn("configureGeneratedTrade", calls)
            self.assertEqual(set(), commands)
        _, commands = runtime._compiled_call_evidence(script.replace('CommandRegistry.CommandRegistry_register = CommandRegistry_TO', ''))
        self.assertEqual(set(), commands)

    def test_generated_regional_map_info_tracks_terrain_and_preserves_layout(self):
        import sys
        sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
        from materialize_physical_map import _resize_map_info, MaterializationError
        original = (PROJECT / "map/AgeOfSailWorld.w3x/war3map.w3i").read_bytes()
        resized = _resize_map_info(original, 128, 192)
        info = runtime.validate_w3i_structure(resized)
        self.assertEqual((116, 180), (info["playableWidth"], info["playableHeight"]))
        self.assertEqual((6, 6, 4, 8), info["cameraComplements"])
        self.assertEqual(original, _resize_map_info(resized, 64, 64))
        with self.assertRaises(MaterializationError):
            _resize_map_info(original[:40], 128, 128)

    def test_bootstrap_compiled_semantics_require_native_transition_before_end(self):
        good = "function config() end\nfunction main() InitBlizzard() TimerStart() showPage() bj_changeLevelMapName=path ChangeLevel(bj_changeLevelMapName, true) end"
        self.assertEqual("pass", runtime.verify_compiled_bootstrap(good)["status"])
        helper = "function config() end\nfunction main() InitBlizzard() TimerStart() showPage() SetNextLevelBJ(path) EndGame(true) end"
        self.assertEqual("fail", runtime.verify_compiled_bootstrap(helper)["status"])
        native = "function config() end\nfunction main() InitBlizzard() TimerStart() showPage() ChangeLevel(path, true) end"
        self.assertEqual("pass", runtime.verify_compiled_bootstrap(native)["status"])
        lost_native = "-- source said SetNextLevelBJ\nfunction config() end\nfunction main() InitBlizzard() TimerStart() showPage() EndGame(true) end"
        self.assertEqual("fail", runtime.verify_compiled_bootstrap(lost_native)["status"])
        reversed_calls = "function config() end\nfunction main() InitBlizzard() TimerStart() showPage() EndGame(true) ChangeLevel(path, true) end"
        self.assertEqual("fail", runtime.verify_compiled_bootstrap(reversed_calls)["status"])

    def test_bootstrap_handoff_comments_and_strings_are_not_effects(self):
        for fake in ('-- SetNextLevel(path)\n', 'local note = "SetNextLevel(path)"\n'):
            script = fake + "function config() end\nfunction main() InitBlizzard() TimerStart() showPage() EndGame(true) end"
            result = runtime.verify_compiled_bootstrap(script)
            self.assertEqual("fail", result["status"])
            self.assertEqual("compiled_text_static_heuristic", result["evidenceLevel"])
            self.assertTrue(any("does not select" in x for x in result["failures"]))

    def test_bootstrap_direct_change_level_survives_renamed_adapter(self):
        script = ('function BO(CO, VO) ChangeLevel(CO, true) end\n'
                  'function config() end\nfunction main() InitBlizzard() TimerStart() showPage() BO(path, note) end')
        self.assertEqual("pass", runtime.verify_compiled_bootstrap(script)["status"])
        # Exact failure shape emitted by the pinned compiler before the repair:
        # the unused BJ destination assignment disappeared, leaving only EndGame.
        broken = script.replace('ChangeLevel(CO, true)', 'EndGame(true)')
        self.assertEqual("fail", runtime.verify_compiled_bootstrap(broken)["status"])
        for fake in ('-- ChangeLevel(path, true)\n',
                     'local note = "ChangeLevel(path, true)"\n'):
            self.assertEqual("fail", runtime.verify_compiled_bootstrap(fake + broken)["status"])

    def test_bootstrap_compiled_semantics_reject_global_scenario_registrations(self):
        script = "function config() end\nfunction main() InitBlizzard() TimerStart() showPage() registerSettlement(x) ChangeLevel(path, true) end"
        result = runtime.verify_compiled_bootstrap(script)
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("regional registration" in x for x in result["failures"]))
        renamed = script.replace('registerSettlement(x)',
            'renamed(x, "when calling registerSettlement in ScenarioData, line 12")')
        result = runtime.verify_compiled_bootstrap('function renamed(x, trace) end\n' + renamed)
        self.assertTrue(any("regional registration" in x for x in result["failures"]))

    def test_valid_metadata_with_blank_placeholder_terrain_fails(self):
        source = PROJECT / "map/AgeOfSailWorld.w3x"
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "placeholder.w3x"
            with zipfile.ZipFile(fixture, "w") as archive:
                for name in ("war3mapUnits.doo", "war3map.w3i", "war3map.shd"):
                    archive.write(source / name, name)
                w3e = bytearray((source / "war3map.w3e").read_bytes())
                offset = 13
                ground = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + ground * 4
                cliffs = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + cliffs * 4 + 16
                w3e[offset:] = w3e[offset:offset + 7] * ((len(w3e) - offset) // 7)
                wpm = bytearray((source / "war3map.wpm").read_bytes())
                wpm[16:] = bytes([wpm[16]]) * (len(wpm) - 16)
                archive.writestr("war3map.w3e", w3e)
                archive.writestr("war3map.wpm", wpm)
                archive.writestr("war3map.lua", self.executable_script())
                archive.writestr("runtime/scenario-runtime.json", json.dumps({
                    "ids": {"polities": ["fixture"]}, "regionalGeography": ["fixture"]}))
                archive.writestr("runtime/physical-map.json", json.dumps({
                    "physicalMapId": "placeholder", "bootstrap": False}))
            result = runtime.inspect_built_map(fixture, "placeholder", False)
            self.assertEqual("fail", result["status"])
            self.assertTrue(any("placeholder" in message for message in result["failures"]))

    def test_required_system_cannot_be_declared_simulation_only(self):
        data = runtime.load_manifest(); data = copy.deepcopy(data)
        data["systems"][0]["simulationOnly"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(runtime.RuntimeAcceptanceError, "cannot be simulation-only"):
                runtime.audit_sources(path)


if __name__ == "__main__":
    unittest.main()
