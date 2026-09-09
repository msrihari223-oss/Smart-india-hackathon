"""
Link Analysis & Network Topology Engine
Constructs directed interaction graphs (mentions, retweets, replies, forwards),
computes Key Opinion Leader (KOL) centrality metrics (PageRank, Betweenness, Degree),
detects modular community clusters (Louvain), and models information cascade diffusion.
"""

import networkx as nx
from typing import Dict, Any, List, Tuple
import random

class NetworkTopologyEngine:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes_data: Dict[str, Dict[str, Any]] = {}
        self.edges_data: List[Dict[str, Any]] = []

    def add_interaction(self, source_user: str, target_user: str, interaction_type: str = "retweet", sentiment: float = 0.0, timestamp: float = 0.0):
        """
        Adds directed interaction edge to the network graph.
        """
        if not source_user or not target_user or source_user == target_user:
            return

        self.graph.add_node(source_user)
        self.graph.add_node(target_user)

        # Update or add edge
        if self.graph.has_edge(source_user, target_user):
            self.graph[source_user][target_user]['weight'] += 1
            self.graph[source_user][target_user]['last_sentiment'] = sentiment
        else:
            self.graph.add_edge(source_user, target_user, weight=1, interaction_type=interaction_type, last_sentiment=sentiment, timestamp=timestamp)

        self.edges_data.append({
            "from": source_user,
            "to": target_user,
            "type": interaction_type,
            "sentiment": sentiment,
            "timestamp": timestamp
        })

        try:
            from backend.database.postgres_repository import postgres_repo
            postgres_repo.insert_interaction(source_user, target_user, interaction_type, sentiment, timestamp)
        except Exception:
            pass

    def register_user_meta(self, username: str, display_name: str, avatar: str, role: str, followers: int, sentiment_bias: float = 0.0):
        self.nodes_data[username] = {
            "id": username,
            "label": f"@{username}",
            "name": display_name,
            "avatar": avatar,
            "role": role,
            "followers": followers,
            "sentiment_bias": sentiment_bias
        }

    def compute_network_metrics(self) -> Dict[str, Any]:
        """
        Calculates PageRank, Betweenness, Degree Centrality, and Community Clusters.
        """
        if len(self.graph.nodes) == 0:
            return {"nodes": [], "edges": [], "kols": [], "communities": []}

        # 1. PageRank for Key Opinion Leaders (KOLs)
        try:
            pageranks = nx.pagerank(self.graph, weight='weight', alpha=0.85)
        except Exception:
            pageranks = {n: 1.0 / len(self.graph.nodes) for n in self.graph.nodes}

        # 2. Betweenness Centrality (Information Bridges)
        try:
            betweenness = nx.betweenness_centrality(self.graph, weight='weight')
        except Exception:
            betweenness = {n: 0.0 for n in self.graph.nodes}

        # 3. Community Detection (Modularity / Greedy Communities)
        undirected_g = self.graph.to_undirected()
        try:
            communities_list = list(nx.community.greedy_modularity_communities(undirected_g))
            node_community_map = {}
            for idx, comm in enumerate(communities_list):
                for node in comm:
                    node_community_map[node] = idx
        except Exception:
            node_community_map = {n: 0 for n in self.graph.nodes}

        # Prepare Nodes payload
        nodes_payload = []
        community_colors = ["#00F0FF", "#A855F7", "#10B981", "#F59E0B", "#EC4899", "#3B82F6", "#8B5CF6"]

        for node_id in self.graph.nodes:
            in_deg = self.graph.in_degree(node_id)
            out_deg = self.graph.out_degree(node_id)
            pr = pageranks.get(node_id, 0.0)
            bw = betweenness.get(node_id, 0.0)
            comm_id = node_community_map.get(node_id, 0)
            
            user_info = self.nodes_data.get(node_id, {
                "name": node_id.capitalize(),
                "role": "Social Node",
                "followers": (in_deg + 1) * 1250,
                "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed={node_id}"
            })

            # Calculate influence score (0 - 100)
            influence_score = round(min(99.9, (pr * 450) + (in_deg * 4.5) + (bw * 150)), 1)
            
            # Node size scaled cleanly (prevents giant bubble overlaps)
            node_size = max(14, min(30, int(14 + influence_score * 0.15)))

            nodes_payload.append({
                "id": node_id,
                "label": f"@{node_id}",
                "name": user_info.get("name", node_id),
                "role": user_info.get("role", "Audience Node"),
                "influence_score": influence_score,
                "pagerank": round(pr, 4),
                "betweenness": round(bw, 4),
                "in_degree": in_deg,
                "out_degree": out_deg,
                "community": comm_id,
                "color": community_colors[comm_id % len(community_colors)],
                "size": node_size,
                "followers": user_info.get("followers", 1000)
            })

        # Prepare Edges payload
        edges_payload = []
        for u, v, data in self.graph.edges(data=True):
            edges_payload.append({
                "from": u,
                "to": v,
                "weight": data.get("weight", 1),
                "type": data.get("interaction_type", "interaction"),
                "sentiment": data.get("last_sentiment", 0.0)
            })

        # Top Key Opinion Leaders (KOLs)
        kols = sorted(nodes_payload, key=lambda x: x["influence_score"], reverse=True)[:10]

        # Community summaries
        community_counts = {}
        for n in nodes_payload:
            c = n["community"]
            community_counts[c] = community_counts.get(c, 0) + 1

        communities_summary = [
            {
                "id": c,
                "color": community_colors[c % len(community_colors)],
                "size": count,
                "label": f"Cluster #{c+1} ({'Tech Alpha' if c==0 else ('Finance/Crypto' if c==1 else ('Civic Discourse' if c==2 else 'Global News'))})"
            }
            for c, count in community_counts.items()
        ]

        return {
            "nodes": nodes_payload,
            "edges": edges_payload,
            "kols": kols,
            "communities": communities_summary,
            "total_nodes": len(nodes_payload),
            "total_edges": len(edges_payload)
        }

    def simulate_cascade(self, start_node: str, steps: int = 4) -> List[Dict[str, Any]]:
        """
        Simulates how an information/sentiment cascade diffuses from a seed influencer.
        """
        if start_node not in self.graph:
            if not self.graph.nodes:
                return []
            start_node = list(self.graph.nodes)[0]

        visited = {start_node}
        current_layer = [start_node]
        cascade_timeline = []

        for step in range(steps):
            next_layer = []
            layer_actions = []
            
            for node in current_layer:
                # Get outgoing neighbors (followers who saw and forwarded/replied)
                neighbors = list(self.graph.neighbors(node)) + list(self.graph.predecessors(node))
                for neighbor in neighbors:
                    if neighbor not in visited and random.random() > 0.35:
                        visited.add(neighbor)
                        next_layer.append(neighbor)
                        layer_actions.append({
                            "from_node": node,
                            "to_node": neighbor,
                            "step": step + 1,
                            "action": random.choice(["Retweeted", "Quoted", "Forwarded", "Amplified"])
                        })
            
            if layer_actions:
                cascade_timeline.append({
                    "step": step + 1,
                    "activated_count": len(next_layer),
                    "total_reached": len(visited),
                    "propagations": layer_actions
                })
            
            current_layer = next_layer
            if not current_layer:
                break

        return cascade_timeline

network_engine = NetworkTopologyEngine()
