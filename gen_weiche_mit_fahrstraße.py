import interlocking
from yaramo.model import Edge, Node, Topology
from time import sleep
from yaramo.model import Edge, EuclideanGeoNode, Node
from yaramo.route import Route
from yaramo.signal import SignalFunction, Signal, SignalDirection, SignalKind
from railwayroutegenerator.routegenerator import RouteGenerator
from sumoexporter import SUMOExporter
from yaramo.operations import Split
from interlocking.infrastructureprovider import (
    LoggingInfrastructureProvider,
    SUMOInfrastructureProvider,
)
import asyncio
import traci
from interlocking.interlockinginterface import Interlocking


def create_geo_node(x, y):
    return EuclideanGeoNode(x, y)


def create_edge(node_a, node_b, inter_geo_nodes=None):
    return Edge(node_a, node_b, intermediate_geo_nodes=inter_geo_nodes)


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

    print(topology.nodes)
    print(topology.edges)
    print(topology.routes)
    print(topology.signals)
    RouteGenerator(topology).generate_routes()
    print("Routes", topology.routes)

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
        ]
    )
    interlocking.prepare(topology)

    train_id = "TRAIN_1"
    traci.vehicle.add(train_id, f"route_{signal_a.name}-{signal_b.name}", "regio")
    route = list(topology.routes.values())[0]
    route.maximum_speed = 50
    asyncio.run(interlocking.set_route(yaramo_route=route, train_id=train_id))
    # traci.vehicle.setSpeedMode(train_id, 32)

    while True:
        traci.simulationStep()
        sleep(1)


if __name__ == "__main__":
    create_simple_weiche()
