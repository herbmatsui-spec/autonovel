import pytest
from src.easy_mode.phase3.if_routes import IFRouteGraph, RouteNode, BranchType

def test_if_route_graph_nodes():
    graph = IFRouteGraph()
    node1 = RouteNode(
        id="node_root",
        episode_num=1,
        content="共通ルート第1話",
        branch_type=BranchType.CHOICE
    )
    node2 = RouteNode(
        id="node_route_a",
        episode_num=1,
        content="ヒロインAルート",
        branch_type=BranchType.CHOICE
    )
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("node_root", "node_route_a", "右の道を進む")
    
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1