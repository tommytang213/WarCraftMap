"""Resolve scenario-owned catalogues without embedding a setting or start year."""
import json
from pathlib import Path


def configuration(project):
    return json.loads((project / "package.json").read_text(encoding="utf-8"))


def content_path(project, relative):
    path = (project / relative).resolve()
    if not path.is_relative_to(project.resolve()):
        raise ValueError(f"scenario input escapes project: {relative}")
    return path


def settlement_sources(project):
    return [(content_path(project, row["source"]),
             content_path(project, row["geography"]), row["regionId"])
            for row in configuration(project)["scenario"].get("settlements", [])]


def catalogue_paths(project):
    return {key: content_path(project, value) for key, value in
            configuration(project)["scenario"].get("catalogues", {}).items()}
