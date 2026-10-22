#!/usr/bin/env python3
"""Run the unchanged gate with a deliberately tiny *harness* safety budget.

Pass the same arguments as verify-trade-full-scale.py. Expected exit status: 1.
This changes only the harness configuration constant, never compiled functions,
source, native stubs or the archived Lua. The generated report records the actual
10,000 instruction limit; its generic limitations describe the normal 2B mode.
"""
from pathlib import Path
import importlib.util

path = Path(__file__).resolve().with_name('verify-trade-full-scale.py')
spec = importlib.util.spec_from_file_location('full_scale_gate_negative_control', path)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
gate.BUDGET = 10_000
raise SystemExit(gate.main())
