import pytest
from src.easy_mode.phase3.if_routes import IFRouteGraph, RouteNode, RouteChoice, BranchType

def test_if_route_graph_nodes():
    graph = IFRouteGraph()
    
    # Create nodes
    node_root = RouteNode(
        id="node_root",
        episode_num=1,
        content="共通ルート第1話",
        branch_type=BranchType.CHOICE,
        choices=[
            RouteChoice(
                id="choice_1",
                text="右の道を進む",
                target_node_id="node_route_a"
            )
        ]
    )
    
    node_route_a = RouteNode(
        id="node_route_a",
        episode_num=2,
        content="ヒロインAルート",
        branch_type=BranchType.CHOICE
    )
    
    graph.add_node(node_root)
    graph.add_node(node_route_a)
    graph.entry_node_id = "node_root"
    
    assert len(graph.nodes) == 2
    # Check that the edge (choice) exists
    assert len(node_root.choices) == 1
    assert node_root.choices[0].target_node_id == "node_route_a"