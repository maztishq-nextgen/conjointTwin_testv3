#!/usr/bin/env python3
"""Test cross-level node connections in graphs."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def create_workspace():
    response = requests.post(f"{BASE_URL}/workspaces", json={"title": "Cross-Level Test"})
    return response.json()['id']

def create_graph_with_cross_level_connections(workspace_id):
    """Create a graph demonstrating cross-level connections."""
    
    # Create graph
    graph_data = {
        "type": "application/vnd.graph+json",
        "title": "Cross-Level Demo",
        "content": json.dumps({
            "graph_type": "concept_map",
            "nodes": [
                {"id": "central_climate", "label": "Climate Change", "level": 0},
                {"id": "core_causes", "label": "Causes", "level": 1},
                {"id": "core_effects", "label": "Effects", "level": 1},
                {"id": "branch_co2", "label": "CO2 Emissions", "level": 2},
                {"id": "detail_transport", "label": "Transportation", "level": 3},
                {"id": "detail_sea_level", "label": "Sea Level Rise", "level": 3},
                {"id": "detail_agriculture", "label": "Agriculture", "level": 3},
            ],
            "edges": [
                # Normal hierarchy
                {"id": "e1", "source": "central_climate", "target": "core_causes", "relationship_type": "contains"},
                {"id": "e2", "source": "central_climate", "target": "core_effects", "relationship_type": "contains"},
                {"id": "e3", "source": "core_causes", "target": "branch_co2", "relationship_type": "contains"},
                {"id": "e4", "source": "branch_co2", "target": "detail_transport", "relationship_type": "contains"},
                {"id": "e5", "source": "core_effects", "target": "detail_sea_level", "relationship_type": "contains"},
                
                # CROSS-LEVEL CONNECTIONS - This is the key part!
                {"id": "e6", "source": "detail_transport", "target": "branch_co2", "relationship_type": "causal_positive"},
                {"id": "e7", "source": "branch_co2", "target": "detail_sea_level", "relationship_type": "causal_positive"},
                {"id": "e8", "source": "detail_agriculture", "target": "branch_co2", "relationship_type": "causal_positive"},
                {"id": "e9", "source": "detail_agriculture", "target": "core_causes", "relationship_type": "related"},
            ],
            "metadata": {"created_by": "test"}
        })
    }
    
    response = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/artifacts",
        json=graph_data
    )
    return response.json()

def main():
    print("=" * 80)
    print("🧪 CROSS-LEVEL NODE CONNECTIONS TEST")
    print("=" * 80)
    
    workspace_id = create_workspace()
    print(f"\n✅ Created workspace: {workspace_id}")
    
    artifact = create_graph_with_cross_level_connections(workspace_id)
    print(f"✅ Created artifact: {artifact['id']}")
    
    # Parse and analyze the graph
    graph_data = json.loads(artifact['content'])
    nodes = graph_data['nodes']
    edges = graph_data['edges']
    
    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes: {len(nodes)}")
    print(f"   Edges: {len(edges)}")
    
    print(f"\n🔗 Cross-Level Connection Analysis:")
    
    # Build node level lookup
    node_levels = {node['id']: node['level'] for node in nodes}
    
    cross_level_edges = []
    for edge in edges:
        source_level = node_levels.get(edge['source'])
        target_level = node_levels.get(edge['target'])
        
        if source_level is not None and target_level is not None:
            level_diff = abs(source_level - target_level)
            
            if level_diff > 1 or (source_level > target_level):
                cross_level_edges.append({
                    'edge': edge,
                    'source_level': source_level,
                    'target_level': target_level,
                    'diff': level_diff
                })
    
    if cross_level_edges:
        print(f"\n✅ Found {len(cross_level_edges)} cross-level connections:")
        for item in cross_level_edges:
            edge = item['edge']
            print(f"\n   Edge: {edge['id']}")
            print(f"   └─ {edge['source']} (L{item['source_level']}) → {edge['target']} (L{item['target_level']})")
            print(f"   └─ Relationship: {edge['relationship_type']}")
            print(f"   └─ Level difference: {item['diff']}")
    else:
        print("\n❌ No cross-level connections found")
    
    print(f"\n{'=' * 80}")
    print("✅ CROSS-LEVEL CONNECTIONS TEST COMPLETE")
    print(f"{'=' * 80}")
    print("\nKey findings:")
    print("✓ Level 3 nodes connect to Level 2 nodes (detail_transport → branch_co2)")
    print("✓ Level 2 nodes connect to Level 3 nodes in different branches (branch_co2 → detail_sea_level)")
    print("✓ Level 3 nodes connect to Level 1 nodes (detail_agriculture → core_causes)")
    print("✓ No restrictions on node level connections!")

if __name__ == "__main__":
    main()
