from yaramo.model import Edge, Node, Topology

from yaramo.model import Edge, EuclideanGeoNode, Node
from yaramo.route import Route
from yaramo.signal import SignalFunction, Signal, SignalDirection, SignalKind
from railwayroutegenerator.routegenerator import RouteGenerator
from sumoexporter import SUMOExporter
from yaramo.operations import Split


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

    end_b = Node(name="b", geo_node=create_geo_node(150, 0))
    topology.add_node(end_b)

    end_c = Node(name="c", geo_node=create_geo_node(150, 50))
    topology.add_node(end_c)

    weiche = Node(name="w", geo_node=create_geo_node(50, 0))
    topology.add_node(weiche)

    a2weiche = create_edge(end_a, weiche)
    topology.add_edge(a2weiche)

    weiche2b = create_edge(weiche, end_b)
    topology.add_edge(weiche2b)

    geo_node_weiche2c = create_geo_node(100, 50)
    weiche2c = create_edge(weiche, end_c, inter_geo_nodes=[geo_node_weiche2c])
    topology.add_edge(weiche2c)

    signal_a = Signal(
        name="sa",
        edge=a2weiche,
        direction=SignalDirection.IN,
        kind=SignalKind.Hauptsignal,
        function=SignalFunction.Block_Signal,
        distance_edge=1.0,
    )
    topology.add_signal(signal_a)
    a2weiche.signals.append(signal_a)

    signal_b = Signal(
        name="sb",
        edge=weiche2b,
        direction=SignalDirection.IN,
        kind=SignalKind.Hauptsignal,
        function=SignalFunction.Block_Signal,
        distance_edge=1.0,
        additional_signals=[signal_a],
    )
    topology.add_signal(signal_b)
    weiche2b.signals.append(signal_b)

    signal_c = Signal(
        name="sc",
        edge=weiche2c,
        direction=SignalDirection.IN,
        kind=SignalKind.Hauptsignal,
        function=SignalFunction.Block_Signal,
        distance_edge=1.0,
        additional_signals=[signal_a],
    )
    topology.add_signal(signal_c)
    weiche2c.signals.append(signal_c)

    print(topology.nodes)
    print(topology.edges)
    print(topology.routes)
    print(topology.signals)
    RouteGenerator(topology).generate_routes()
    print("Routes", topology.routes)

    sumo_exporter = SUMOExporter(topology)
    sumo_exporter.convert()
    sumo_exporter.write_output()


if __name__ == "__main__":
    create_simple_weiche()
