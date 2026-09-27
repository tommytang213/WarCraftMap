"""Expose shared timeline validation through world validation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"engine"))
import timeline
def validate(data,fail):
    try: return timeline.validate_definition(data.get("timeline"))
    except timeline.TimelineError as exc: fail(str(exc))
