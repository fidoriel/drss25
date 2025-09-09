from typing import Any, Literal
from yaramo.model import Edge, Node, Topology
from time import sleep
from yaramo.model import EuclideanGeoNode
from yaramo.route import Route
from yaramo.signal import SignalFunction, Signal, SignalDirection, SignalKind
from railwayroutegenerator.routegenerator import RouteGenerator
from sumoexporter import SUMOExporter
from interlocking.infrastructureprovider import (
    LoggingInfrastructureProvider,
    SUMOInfrastructureProvider,
    InfrastructureProvider,
)
from interlocking.model import OccupancyState, Route
import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import asyncio
import traci
from interlocking.interlockinginterface import Interlocking
from Train import Train


def create_geo_node(x, y):
    return EuclideanGeoNode(x, y)


def create_edge(node_a, node_b, inter_geo_nodes=None):
    return Edge(node_a, node_b, intermediate_geo_nodes=inter_geo_nodes)


def find_route_for_signals(routes: dict, start_signal: Signal, stop_signal: Signal):
    for route in list(routes.values()):
        if route.end_signal is stop_signal and start_signal is route.start_signal:
            return route

    raise ValueError(f"No Route from {start_signal.name} to {start_signal.name} Found")


def bootstrap_train(interlocking: Interlocking, train_id: Any, route: Route):
    if route.maximum_speed is None:
        raise ValueError("Route needs maximum_speed")

    asyncio.run(interlocking.set_route(yaramo_route=route, train_id=train_id))
    interlocking.print_state()
    # traci.vehicle.setSpeedMode(train_id, 32)
    traci.simulationStep()  # we need the first tick so the train is spawned
    position = traci.vehicle.getRoadID(train_id)
    segment = interlocking.train_detection_controller.get_segment_by_segment_id(
        position
    )  # get the current position of the train, needs first simulation tick, so train is placed
    segment.used_by.add(train_id)  # tell the segment which train is on it
    segment.state = OccupancyState.RESERVED  # reserve segment
    interlocking.train_detection_controller.state[segment.segment_id] = (
        1  # mark track as used in train detection controller
    )

    return position


import httpx


class RestInfrastructureProviderSwitch(InfrastructureProvider):
    host = "http://127.0.0.1:5000"
    point_id: str
    client: httpx.AsyncClient
    position: Literal["left", "right"] = "right"  # change me

    def __init__(self, point_id, **kwargs):
        self.point_id = point_id
        self.client = httpx.AsyncClient()
        super().__init__(**kwargs)

    async def set_signal_aspect(self, yaramo_signal, target_aspect):
        return True

    async def turn_point(self, yaramo_point, target_orientation: str):
        point_id = yaramo_point.uuid[-5:]
        if self.point_id != point_id:
            return
        if (target_orientation == "left") and self.position == "right":
            await self.client.get(f"{self.host}/turn_left")
            self.position = "left"
        elif (target_orientation == "right") and self.position == "left":
            await self.client.get(f"{self.host}/turn_right")
            self.position = "right"
        return True


class RestInfrastructureProviderSignal(InfrastructureProvider):
    host = "http://127.0.0.1:5000"
    signal_id: str
    client: httpx.AsyncClient
    position: Literal["halt", "halt_erwarten", "fahrt"] = "halt"

    def __init__(self, signal_id, **kwargs):
        self.signal_id = signal_id
        self.client = httpx.AsyncClient()
        super().__init__(**kwargs)

    async def set_signal_aspect(self, yaramo_signal, target_aspect):
        if yaramo_signal.name == self.signal_id:
            if target_aspect == "go" and self.position != "fahrt":
                await self.client.get(f"{self.host}/signal?aspect=green")
                self.position = "fahrt"
                return True
            if target_aspect == "halt" and self.position != "halt":
                await self.client.get(f"{self.host}/signal?aspect=red")
                self.position = "halt"
                return True
        return False

    async def turn_point(self, yaramo_point, target_orientation: str):
        return True


def create_simple_weiche():
    """
    This test creates this kind of topology:
          ___ c
    a ___/___ b
    """
    topology = Topology(name="weiche")

    end_a = Node(name="a", geo_node=create_geo_node(0, 0))
    topology.add_node(end_a)

    end_b = Node(name="b", geo_node=create_geo_node(1500, 0))
    topology.add_node(end_b)

    end_c = Node(name="c", geo_node=create_geo_node(1500, 50))
    topology.add_node(end_c)

    weiche = Node(name="w", geo_node=create_geo_node(500, 0))
    topology.add_node(weiche)

    a2weiche = create_edge(end_a, weiche)
    topology.add_edge(a2weiche)

    weiche2b = create_edge(weiche, end_b)
    topology.add_edge(weiche2b)

    geo_node_weiche2c = create_geo_node(1000, 50)
    weiche2c = create_edge(weiche, end_c, inter_geo_nodes=[geo_node_weiche2c])
    topology.add_edge(weiche2c)

    signal_a = Signal(
        name="SA",
        edge=a2weiche,
        direction=SignalDirection.IN,
        kind=SignalKind.Hauptsignal,
        function=SignalFunction.Block_Signal,
        distance_edge=100.0,
    )
    topology.add_signal(signal_a)
    a2weiche.signals.append(signal_a)

    signal_b = Signal(
        name="SB",
        edge=weiche2b,
        direction=SignalDirection.IN,
        kind=SignalKind.Hauptsignal,
        function=SignalFunction.Block_Signal,
        distance_edge=100.0,
        additional_signals=[signal_a],
    )
    topology.add_signal(signal_b)
    weiche2b.signals.append(signal_b)

    signal_c = Signal(
        name="SC",
        edge=weiche2c,
        direction=SignalDirection.IN,
        kind=SignalKind.Hauptsignal,
        function=SignalFunction.Block_Signal,
        distance_edge=100.0,
        additional_signals=[signal_a],
    )
    topology.add_signal(signal_c)
    weiche2c.signals.append(signal_c)
    topology.update_edge_lengths()

    RouteGenerator(topology).generate_routes()

    sumo_exporter = SUMOExporter(topology)
    sumo_exporter.convert()
    sumo_exporter.write_output()

    traci.init(port=9090)
    # traci.start(["sumo-gui", "--configuration-file", "sumo-config/weiche.scenario.sumocfg"], port=9090, verbose=True)
    traci.setOrder(1)
    interlocking = Interlocking(
        [
            SUMOInfrastructureProvider(traci_instance=traci),
            LoggingInfrastructureProvider(),
            # RestInfrastructureProviderSwitch(point_id=weiche.uuid[-5:]),
            RestInfrastructureProviderSignal(signal_id=signal_a.name),
        ]
    )
    interlocking.prepare(topology)

    train_id = "TRAIN_1"
    train = Train(train_id)

    begin = signal_a
    end = signal_c

    traci.vehicle.add(train_id, f"route_{begin.name}-{end.name}", "regio")

    route = find_route_for_signals(topology.routes, begin, end)
    route.maximum_speed = 50

    old_position = bootstrap_train(interlocking, train_id, route)
    while True:
        traci.simulationStep()
        new_position = traci.vehicle.getRoadID(train_id)
        if new_position.startswith(":"):  # Point internal edges will be ignored
            continue
        if new_position.endswith("-re"):
            new_position = new_position[:-3]
        if new_position != old_position:
            interlocking.train_detection_controller.count_out(old_position, train_id)
            asyncio.run(
                interlocking.train_detection_controller.count_in(new_position, train_id)
            )
            train.current_position = new_position
        sleep(1)


if __name__ == "__main__":
    create_simple_weiche()
