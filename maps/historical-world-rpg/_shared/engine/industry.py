"""Deterministic industry consumer for headless campaigns.

The live Wurst consumer uses the same integer work and batch accounting rules.
Facilities and material identities are scenario-owned. Research layers are
reconstructed from durable completions, never serialized as numerical bonuses.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date


@dataclass
class IndustryState:
    equipment_owner: str = ''
    ready: int = 0
    owner: str = ''
    work: int = 0
    last_day: int = 0

    def stop(self):
        self.owner, self.work = '', 0


class IndustryRuntime:
    def __init__(self, catalog, research, economy):
        self.catalog = deepcopy(catalog)
        self.research, self.economy = research, economy
        self.sites = {s['id']: s for s in catalog['sites']}
        self.states = {ident: IndustryState() for ident in self.sites}
        self.layers = {}
        self.reconcile()

    def reconcile(self):
        self.layers = {p: {(e['kind'], e['contentId']) for e in self.research.entitlements(p)}
                       for p in self.research.polity_ids}

    def rate(self, owner, metric, year):
        # One contribution per typed identity, even with multiple source nodes.
        bindings = {(e['unlock']['kind'], e['unlock']['contentId']): e
                    for e in self.catalog['effects']}
        return sum(e['bonusBasisPoints'] for identity, e in bindings.items()
                   if identity in self.layers.get(owner, set()) and e['metric'] == metric
                   and year >= e['firstYear'])

    def eligible(self, d, owner, day):
        city = self.economy['cities'].get(d['settlementId'])
        return (bool(owner) and city is not None and date.fromordinal(day).year >= d['firstYear']
                and city['owner'] == owner and city['legal'] and city['administered']
                and city['accessible'] and city['warehouse_service']
                and not {d['inputGood'], d['outputGood'], self.catalog['rules']['fuelGood'],
                         self.catalog['rules']['equipmentGood']} & city['blocked']
                and d['prerequisite'] in self.research.completed(owner))

    def pay(self, d, owner, setup):
        rules = self.catalog['rules']
        city = self.economy['cities'][d['settlementId']]
        treasury = self.economy['treasury']
        money = rules['setup']['money'] if setup else d['money']
        stock = city['stock']
        inputs = {rules['fuelGood']: rules['setup']['fuel'] if setup else d['fuelUnits'],
                  rules['equipmentGood']: rules['setup']['equipment'] if setup else d['wearUnits']}
        if not setup:
            inputs[d['inputGood']] = d['inputUnits']
        workers = rules['setup']['workers'] if setup else 0
        if (treasury.get(owner, 0) < money or city['manpower'] < workers
                or any(stock.get(g, 0) + city.get('warehouse', {}).get(g, 0) < n or g in city['blocked'] for g, n in inputs.items())):
            return False
        treasury[owner] -= money
        city['manpower'] -= workers
        for g, n in inputs.items():
            local = min(n, stock.get(g, 0))
            stock[g] -= local
            if n > local:
                city['warehouse'][g] -= n - local
        return True

    def action(self, owner, ident, action, day):
        if ident not in self.sites or not owner:
            return False
        d, s = self.sites[ident], self.states[ident]
        if day < s.last_day or not self.eligible(d, owner, day):
            return False
        if action == 'stop':
            if s.owner != owner:
                return False
            s.stop()
            return True
        if s.owner:
            return False
        if action == 'equip':
            if s.equipment_owner or not self.pay(d, owner, True):
                return False
            s.equipment_owner, s.ready, s.last_day = owner, day + self.catalog['rules']['setup']['days'], day
            return True
        if (action != 'start' or s.equipment_owner != owner or day < s.ready
                or not self.pay(d, owner, False)):
            return False
        s.owner, s.work, s.last_day = owner, 0, day
        return True

    def advance(self, day):
        daily = self.catalog['rules']['daily']
        for ident, d in self.sites.items():
            s = self.states[ident]
            while s.owner and s.last_day < day:
                at = s.last_day
                s.last_day += 1
                if not self.eligible(d, s.owner, at) or s.equipment_owner != s.owner or at < s.ready:
                    s.stop()
                    continue
                rate = self.rate(s.owner, d['metric'], date.fromordinal(at).year)
                output, work = d['outputUnits'], d['dailyWork'] * 10000
                if d['mode'] == 'yield':
                    output += output * rate // 10000
                else:
                    work += d['dailyWork'] * rate
                completed = s.work + work >= d['workRequired'] * 10000
                city = self.economy['cities'][d['settlementId']]
                stock = city['stock']
                if completed and (d['outputGood'] in city['blocked'] or d['outputGood'] not in stock
                                  or output > city['capacity'] - stock[d['outputGood']]):
                    continue
                if city['supply'] < daily['supply'] or self.economy['treasury'][s.owner] < daily['money']:
                    continue
                city['supply'] -= daily['supply']
                self.economy['treasury'][s.owner] -= daily['money']
                s.work = min(d['workRequired'] * 10000, s.work + work)
                if completed:
                    stock[d['outputGood']] += output
                    s.stop()
            if not s.owner:
                s.last_day = max(day, s.last_day)

    def transfer(self, settlement, owner, day):
        self.economy['cities'][settlement]['owner'] = owner
        for ident, d in self.sites.items():
            if d['settlementId'] != settlement:
                continue
            s = self.states[ident]
            s.stop()
            at = max(day, s.last_day)
            if s.equipment_owner:
                if s.ready <= at:
                    s.equipment_owner = owner
                else:
                    s.equipment_owner, s.ready = '', 0
            s.last_day = at

    def snapshot(self):
        return dict(schemaVersion=1, states={i: asdict(s) for i, s in self.states.items()})

    def restore(self, saved, campaign_day):
        if saved is None:  # Old campaigns have no commissioned industry.
            candidate = {i: IndustryState() for i in self.sites}
        else:
            if not isinstance(saved, dict) or saved.get('schemaVersion') != 1 or set(saved.get('states', {})) != set(self.sites):
                raise ValueError('industry: incomplete/unsupported snapshot')
            candidate = {}
            for ident, raw in saved['states'].items():
                if not isinstance(raw, dict) or set(raw) != set(IndustryState.__dataclass_fields__):
                    raise ValueError('industry: malformed state')
                s = IndustryState(**raw)
                if type(s.owner) is not str or type(s.equipment_owner) is not str:
                    raise ValueError('industry: malformed controller')
                if any(type(v) is not int or v < 0 or v > 1000000 for v in (s.ready, s.last_day)):
                    raise ValueError('industry: malformed deadline')
                if (type(s.work) is not int or not 0 <= s.work < self.sites[ident]['workRequired'] * 10000
                        or s.last_day > campaign_day or bool(s.equipment_owner) != bool(s.ready)
                        or s.owner and (s.owner != s.equipment_owner or s.last_day < s.ready)
                        or not s.owner and s.work):
                    raise ValueError('industry: inconsistent work')
                city = self.economy['cities'].get(self.sites[ident]['settlementId'])
                if s.equipment_owner and (city is None or city['owner'] != s.equipment_owner):
                    raise ValueError('industry: controller mismatch')
                candidate[ident] = s
        self.states = candidate
        self.reconcile()
