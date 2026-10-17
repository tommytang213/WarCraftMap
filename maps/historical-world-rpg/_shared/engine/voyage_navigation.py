"""Scenario-owned circuit voyages and exact position-finding logistics.

A circuit returns to its original station; it cannot relocate a force or reveal
knowledge. The military runtime owns provisions, identity and representations.
This contract owns only purchased equipment and reserved voyage progress.
"""
from __future__ import annotations
import copy
import re
from collections.abc import Mapping
from navigation import is_reachable


class VoyageError(ValueError):
    pass


def integer(value, low=0, high=1_000_000):
    if type(value) is not int or not low <= value <= high:
        raise VoyageError("invalid voyage integer")
    return value


class VoyageCatalog:
    def __init__(self, data, world):
        self.data = copy.deepcopy(data)
        if not isinstance(data, Mapping) or type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1:
            raise VoyageError("voyage catalogue schemaVersion must be 1")
        def stable(value):
            if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", value):
                raise VoyageError("invalid voyage stable ID")
            return value
        self.kind = data["entitlement"]["kind"]
        self.content = data["entitlement"]["contentId"]
        if self.kind != "modifier" or not any(
            u == data["entitlement"] for n in world["technologies"] for u in n["unlocks"]
        ):
            raise VoyageError("unknown voyage research entitlement")
        self.reduction = integer(data["positionFindingReductionBasisPoints"], 1, 1000)
        self.equipment_cost = integer(data["observationEquipmentMoneyCost"], 1, 100000)
        self.routes = {r["id"]: r for r in data["routes"]}
        self.ships = {s["forceId"]: s for s in data["ships"]}
        if not self.routes or not self.ships or len(self.routes) > 64 or len(self.ships) > 4096:
            raise VoyageError("voyage contract requires bounded routes and supported ships")
        if len(self.routes) != len(data["routes"]) or len(self.ships) != len(data["ships"]):
            raise VoyageError("duplicate voyage definition")
        zones = {z["id"]: z for z in world["navigationZones"]}
        units = {u["id"]: u for u in world["strategicUnits"]}
        for route in self.routes.values():
            for key in ("id", "mapId", "knownRegionId"):
                stable(route[key])
            integer(route["days"], 1, 60)
            integer(route["dailyProvisions"], 1, 100)
            integer(route["dailyPositionFindingProvisions"], 1, route["dailyProvisions"])
            path = route["zoneCircuit"]
            if len(path) < 2 or path[0] != path[-1] or any(
                a not in zones or b not in zones or not is_reachable(zones, "naval", a, b)
                or (a != b and b not in zones[a]["connections"].get("naval", []))
                for a, b in zip(path, path[1:])
            ):
                raise VoyageError("voyage circuit crosses an illegal naval edge")
        for ident, ship in self.ships.items():
            for key in ("forceId", "mapId", "stationZoneId", "runtimeTemplateId"):
                stable(ship[key])
            position = ship["stationPosition"]
            if not isinstance(position, list) or len(position) != 2 or any(type(x) is not int or abs(x) > 131072 for x in position):
                raise VoyageError("invalid voyage station coordinates")
            unit = units.get(ident)
            if not unit or unit["kind"] != "ship" or unit["runtimeInstantiation"]["runtimeTemplateId"] != ship["runtimeTemplateId"]:
                raise VoyageError("unsupported voyage vessel")
            if ship["stationZoneId"] != unit["currentLocationId"] or ship["stationZoneId"] not in zones:
                raise VoyageError("invalid voyage station")
            if not ship["observationCapable"] or type(ship["observationCapable"]) is not bool:
                raise VoyageError("vessel lacks observation capability")
            if not ship["routeIds"] or set(ship["routeIds"]) - self.routes.keys():
                raise VoyageError("unknown vessel route")
            for route_id in ship["routeIds"]:
                route = self.routes[route_id]
                if route["zoneCircuit"][0] != ship["stationZoneId"] or route["mapId"] != ship["mapId"]:
                    raise VoyageError("route does not return to the vessel station")

    def initial_state(self):
        return {"schemaVersion": 1, "ships": {ident: self.empty() for ident in self.ships}}

    @staticmethod
    def empty():
        return dict(equipment=False, routeId="", elapsedDays=0, lastDay=0, reserved=0, creditBasisPoints=0)

    def validate(self, value):
        if not isinstance(value, Mapping) or set(value) != {"schemaVersion", "ships"} or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1 or not isinstance(value["ships"], Mapping) or set(value["ships"]) != set(self.ships):
            raise VoyageError("invalid voyage save state")
        result = copy.deepcopy(value)
        for ident, state in result["ships"].items():
            if not isinstance(state, Mapping) or set(state) != set(self.empty()) or type(state["equipment"]) is not bool or not isinstance(state["routeId"], str):
                raise VoyageError("invalid navigation equipment record")
            for key in ("elapsedDays", "lastDay", "reserved", "creditBasisPoints"):
                integer(state[key])
            integer(state["creditBasisPoints"], 0, 9999)
            route = self.routes.get(state["routeId"])
            if state["routeId"]:
                if route is None or state["routeId"] not in self.ships[ident]["routeIds"] or state["elapsedDays"] >= route["days"] or state["reserved"] != (route["days"] - state["elapsedDays"]) * route["dailyProvisions"]:
                    raise VoyageError("invalid pending voyage")
            elif any(state[k] for k in ("elapsedDays", "lastDay", "reserved")):
                raise VoyageError("idle voyage retains progress")
        return result

    def start(self, ident, state, route_id, day, provisions):
        integer(day)
        if ident not in self.ships or route_id not in self.ships[ident]["routeIds"] or state["routeId"]:
            raise VoyageError("unsupported or already traveling vessel/route")
        route = self.routes[route_id]
        reserve = route["days"] * route["dailyProvisions"]
        if provisions < reserve:
            raise VoyageError("insufficient provisions for the undiscounted voyage")
        state.update(routeId=route_id, elapsedDays=0, lastDay=day, reserved=reserve)
        return provisions - reserve

    def resolve(self, state, day, eligible):
        """Return provisions released, consuming only elapsed whole campaign days.

        Call before changing controller/equipment so elapsed days use the old
        inputs. A day callback may span days; work remains bounded by route days.
        """
        integer(day)
        if not state["routeId"]:
            return 0
        if day < state["lastDay"]:
            raise VoyageError("voyage clock moved backwards")
        route = self.routes[state["routeId"]]
        days = min(day - state["lastDay"], route["days"] - state["elapsedDays"])
        state["reserved"] -= days * route["dailyProvisions"]
        state["elapsedDays"] += days
        state["lastDay"] += days
        credit = state["creditBasisPoints"]
        if eligible and state["equipment"]:
            credit += days * route["dailyPositionFindingProvisions"] * self.reduction
        released, state["creditBasisPoints"] = divmod(credit, 10000)
        if state["elapsedDays"] == route["days"]:
            state.update(routeId="", elapsedDays=0, lastDay=0, reserved=0)
        return released

    @staticmethod
    def interrupt(state):
        released = state["reserved"]
        state.update(routeId="", elapsedDays=0, lastDay=0, reserved=0)
        return released
