#!/usr/bin/env python3
"""Validate and project the selective Pacific 1450 political baseline."""
from __future__ import annotations
import json, sys
from pathlib import Path
from middle_east_india_politics import PoliticsError, project as _project, validate as _validate

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/politics/pacific-1450.json"; GEOGRAPHY=ROOT/"scenario/geography/pacific.json"; WORLD=ROOT/"scenario/world/world.json"

def validate(source_path=SOURCE,world_path=WORLD,geography_path=GEOGRAPHY,require_projection=True):
 data=_validate(source_path,world_path,geography_path,require_projection)
 evidence={x.get("id") for x in data.get("historicalEvidence",[]) if isinstance(x,dict)}
 if not evidence or any(not x.get("citation") or not x.get("note") for x in data["historicalEvidence"]): raise PoliticsError("Pacific baseline requires documented historical evidence")
 for polity in data["polities"]:
  if not polity.get("evidenceIds") or any(x not in evidence for x in polity["evidenceIds"]): raise PoliticsError(f"polity {polity['id']}: invalid historical evidence references")
  if polity.get("structure") not in {"chiefdom","confederated","decentralized","ritual_state"}: raise PoliticsError(f"polity {polity['id']}: invalid Pacific authority model")
 return data

def project(data,world): return _project(data,world)
def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try:
  if argv==["--write"]:
   data=validate(require_projection=False); WORLD.write_text(json.dumps(project(data,json.loads(WORLD.read_text())),ensure_ascii=False,indent=2)+"\n")
  elif argv: raise PoliticsError("usage: pacific_politics.py [--write]")
  data=validate(); print(f"Pacific politics valid: {len(data['polities'])} polities, {sum(len(x['provinces']) for x in data['polities'])} territorial regions")
 except (OSError,json.JSONDecodeError,KeyError,PoliticsError) as e: print(f"Pacific politics validation failed: {e}",file=sys.stderr); return 1
 return 0
if __name__=="__main__": raise SystemExit(main())
