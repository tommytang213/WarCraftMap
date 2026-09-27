"""Deterministic scenario-independent campaign calendar and schedules."""
from __future__ import annotations
import calendar, copy, re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Mapping
STATE_VERSION=1
ID_RE=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
class TimelineError(ValueError): pass

def parse_date(value: Any, context="date") -> date:
    if not isinstance(value,str): raise TimelineError(f"{context}: expected ISO date string")
    try: result=date.fromisoformat(value)
    except ValueError as exc: raise TimelineError(f"{context}: invalid Gregorian date {value!r}") from exc
    if result.isoformat()!=value: raise TimelineError(f"{context}: date must use YYYY-MM-DD")
    return result

def _id(value,context):
    if not isinstance(value,str) or not ID_RE.fullmatch(value): raise TimelineError(f"{context}: invalid stable ID {value!r}")
    return value

def _int(value,context,minimum=None):
    if isinstance(value,bool) or not isinstance(value,int) or minimum is not None and value<minimum: raise TimelineError(f"{context}: invalid integer")
    return value

def _next(value, rule):
    n,unit=rule["interval"],rule["unit"]
    if unit=="days": result=value+timedelta(days=n)
    else:
        months=n if unit=="months" else n*12
        year,month0=divmod(value.year*12+value.month-1+months,12)
        if not 1<=year<=9999: raise TimelineError("recurrence leaves supported calendar range")
        month=month0+1; result=date(year,month,min(value.day,calendar.monthrange(year,month)[1]))
    if result<=value: raise TimelineError("recurrence must advance campaign time")
    return result

@dataclass(frozen=True)
class EventOccurrence:
    date:str; priority:int; schedule_id:str; event_id:str; occurrence:int
    def to_dict(self): return {"date":self.date,"priority":self.priority,"scheduleId":self.schedule_id,"eventId":self.event_id,"occurrence":self.occurrence}

def validate_definition(value: Mapping[str,Any]):
    if not isinstance(value,Mapping): raise TimelineError("timeline: expected object")
    data=copy.deepcopy(dict(value))
    if data.get("calendar")!="proleptic_gregorian": raise TimelineError("timeline.calendar: only proleptic_gregorian is supported")
    start=parse_date(data.get("startDate"),"timeline.startDate"); end=parse_date(data.get("endDate"),"timeline.endDate"); initial=parse_date(data.get("initialDate"),"timeline.initialDate")
    if start>end: raise TimelineError("timeline: startDate must not follow endDate")
    if not start<=initial<=end: raise TimelineError("timeline.initialDate: outside campaign range")
    eras={}
    for raw in data.get("eras",[]):
        ident=_id(raw.get("id") if isinstance(raw,dict) else None,"timeline.eras.id")
        if ident in eras: raise TimelineError(f"timeline.eras: duplicate ID {ident!r}")
        first=parse_date(raw.get("startDate"),f"era {ident}.startDate"); last=parse_date(raw.get("endDate"),f"era {ident}.endDate")
        if first>last or first<start or last>end: raise TimelineError(f"era {ident}: invalid or out-of-range dates")
        for other,bounds in eras.items():
            if first<=bounds[1] and bounds[0]<=last: raise TimelineError(f"era {ident}: overlaps era {other!r}")
        eras[ident]=(first,last)
    events=set()
    for raw in data.get("eventDefinitions",[]):
        ident=_id(raw.get("id") if isinstance(raw,dict) else None,"timeline.eventDefinitions.id")
        if ident in events: raise TimelineError(f"timeline.eventDefinitions: duplicate ID {ident!r}")
        events.add(ident)
    schedules=set()
    for raw in data.get("schedules",[]):
        ident=_id(raw.get("id") if isinstance(raw,dict) else None,"timeline.schedules.id")
        if ident in schedules: raise TimelineError(f"timeline.schedules: duplicate ID {ident!r}")
        schedules.add(ident); event_id=_id(raw.get("eventId"),f"schedule {ident}.eventId")
        if event_id not in events: raise TimelineError(f"schedule {ident}: missing event reference {event_id!r}")
        first=parse_date(raw.get("firstDate"),f"schedule {ident}.firstDate")
        if not start<=first<=end: raise TimelineError(f"schedule {ident}.firstDate: outside campaign range")
        _int(raw.get("priority"),f"schedule {ident}.priority")
        if raw.get("eraId") is not None and raw["eraId"] not in eras: raise TimelineError(f"schedule {ident}: missing era reference {raw['eraId']!r}")
        rule=raw.get("recurrence")
        if rule is not None:
            if not isinstance(rule,dict) or rule.get("unit") not in {"days","months","years"}: raise TimelineError(f"schedule {ident}.recurrence: invalid unit")
            _int(rule.get("interval"),f"schedule {ident}.recurrence.interval",1); until=parse_date(rule.get("untilDate"),f"schedule {ident}.recurrence.untilDate")
            if until<first or until>end: raise TimelineError(f"schedule {ident}.recurrence: impossible date range")
            if "maxOccurrences" in rule: _int(rule["maxOccurrences"],f"schedule {ident}.recurrence.maxOccurrences",1)
            _next(first,rule)
    return data

def initial_state(definition):
    data=validate_definition(definition); pending=[{"scheduleId":x["id"],"nextDate":x["firstDate"],"occurrencesEmitted":0} for x in data.get("schedules",[])]
    return {"timelineStateVersion":STATE_VERSION,"currentDate":data["initialDate"],"pendingSchedules":sorted(pending,key=lambda x:x["scheduleId"])}

def validate_state(definition,state):
    data=validate_definition(definition)
    if not isinstance(state,Mapping) or state.get("timelineStateVersion")!=STATE_VERSION: raise TimelineError(f"timeline state must use version {STATE_VERSION}; migrate older versions before load")
    current=parse_date(state.get("currentDate"),"timeline state.currentDate")
    if not parse_date(data["startDate"])<=current<=parse_date(data["endDate"]): raise TimelineError("timeline state.currentDate: outside campaign range")
    if not isinstance(state.get("pendingSchedules"),list): raise TimelineError("timeline state.pendingSchedules: expected array")
    known={x["id"] for x in data.get("schedules",[])}; seen=set()
    for item in state["pendingSchedules"]:
        ident=item.get("scheduleId") if isinstance(item,Mapping) else None
        if ident not in known: raise TimelineError(f"timeline state: missing schedule reference {ident!r}")
        if ident in seen: raise TimelineError(f"timeline state: duplicate pending schedule {ident!r}")
        seen.add(ident); next_date=parse_date(item.get("nextDate"),f"pending schedule {ident}.nextDate"); _int(item.get("occurrencesEmitted"),f"pending schedule {ident}.occurrencesEmitted",0)
        if next_date<current: raise TimelineError(f"pending schedule {ident}.nextDate: precedes currentDate")

def advance(definition,state,target_date):
    data=validate_definition(definition); validate_state(data,state); target=parse_date(target_date,"targetDate"); current=parse_date(state["currentDate"])
    if target<current or target>parse_date(data["endDate"]): raise TimelineError("targetDate must be between currentDate and campaign end")
    schedules={x["id"]:x for x in data.get("schedules",[])}; pending=[]; emitted=[]
    for saved in state["pendingSchedules"]:
        schedule=schedules[saved["scheduleId"]]; next_date=parse_date(saved["nextDate"]); count=saved["occurrencesEmitted"]; rule=schedule.get("recurrence")
        while next_date<=target:
            count+=1; emitted.append(EventOccurrence(next_date.isoformat(),schedule["priority"],schedule["id"],schedule["eventId"],count))
            if rule is None or count>=rule.get("maxOccurrences",2**63-1): next_date=None; break
            candidate=_next(next_date,rule)
            if candidate>parse_date(rule["untilDate"]): next_date=None; break
            next_date=candidate
        if next_date is not None: pending.append({"scheduleId":schedule["id"],"nextDate":next_date.isoformat(),"occurrencesEmitted":count})
    emitted.sort(key=lambda x:(x.date,x.priority,x.schedule_id,x.occurrence,x.event_id))
    return {"timelineStateVersion":STATE_VERSION,"currentDate":target.isoformat(),"pendingSchedules":sorted(pending,key=lambda x:x["scheduleId"])},tuple(emitted)

def active_era(definition,current_date):
    data=validate_definition(definition); current=parse_date(current_date)
    return next((x["id"] for x in data.get("eras",[]) if parse_date(x["startDate"])<=current<=parse_date(x["endDate"])),None)

def research_cost_multiplier(preferred_year,current_date,ahead_multiplier,per_year_ahead):
    years=max(0,preferred_year-parse_date(current_date).year)
    return 1.0 if years==0 else float(ahead_multiplier+per_year_ahead*years)
