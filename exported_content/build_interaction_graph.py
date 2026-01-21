#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build a directed interaction graph from the simulation SQLite database.
- Nodes: users
- Directed edges:
  - like: user_actions.action_type IN ('like', 'like_post') -> edge (liker -> post_author)
  - share_post: user_actions.action_type == 'share_post' -> edge (sharer -> post_author)
  - comment_post: user_actions.action_type == 'comment_post' -> edge (commenter -> post_author)
  - like_comment: user_actions.action_type == 'like_comment' -> edge (liker -> comment_author)
  - follow: user_actions.action_type == 'follow_user' OR follows table -> edge (follower -> followed)
  - comment: comments table -> edge (comment_author -> post_author)
  - note_rating: note_ratings JOIN community_notes -> edge (rater -> post_author)

Edges are aggregated by (src, dst, interaction_type) with a weight count.
Outputs:
- exported_content/graphs/interaction_graph.gexf
- exported_content/graphs/communities.csv
- exported_content/graphs/betweenness_centrality.csv
Prints summary stats.
"""

import os
import sqlite3
from collections import defaultdict
from pathlib import Path
import csv
import statistics

try:
    import networkx as nx
except Exception as e:
    raise SystemExit("NetworkX is required. Install with: pip install networkx\n" + str(e))

DB_PATH = "./database/simulation.db"
OUTPUT_DIR = "./exported_content/graphs"
OUTPUT_GEXF = os.path.join(OUTPUT_DIR, "interaction_graph.gexf")
OUTPUT_COMMUNITIES_CSV = os.path.join(OUTPUT_DIR, "communities.csv")
OUTPUT_CENTRALITY_CSV = os.path.join(OUTPUT_DIR, "betweenness_centrality.csv")


def connect_readonly(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_post_authors(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT post_id, author_id FROM posts")
    return {row[0]: row[1] for row in cur.fetchall()}


def fetch_users(conn: sqlite3.Connection) -> dict:
    # Return dict user_id -> basic attributes if needed later (persona, influence)
    cur = conn.cursor()
    cur.execute("SELECT user_id, persona, influence_score FROM users")
    users = {}
    for uid, persona, influence in cur.fetchall():
        users[uid] = {
            "persona": persona,
            "influence_score": influence,
        }
    return users


def build_edges(conn: sqlite3.Connection):
    post_author = fetch_post_authors(conn)

    # aggregator: (src, dst, type) -> weight
    agg = defaultdict(int)

    # 1) user_actions: comprehensive action types from database
    cur = conn.cursor()
    try:
        # Get all action types that can create interactions between users
        cur.execute(
            """
            SELECT user_id, action_type, target_id
            FROM user_actions
            WHERE action_type IN (
                'like', 'like_post', 'like_comment', 
                'share_post', 'comment_post', 
                'follow_user', 'post'
            )
            """
        )
        for user_id, action_type, target_id in cur.fetchall():
            # Handle different action types
            if action_type in ['like', 'like_post', 'share_post', 'comment_post']:
                # These target posts, so we map to post author
                dst = post_author.get(target_id)
                if dst:
                    # Normalize action names for consistency
                    normalized_action = 'like' if action_type in ['like', 'like_post'] else action_type
                    agg[(user_id, dst, normalized_action)] += 1
            elif action_type == 'like_comment':
                # This targets comments, need to find comment author
                try:
                    cur2 = conn.cursor()
                    cur2.execute("SELECT author_id FROM comments WHERE comment_id = ?", (target_id,))
                    comment_author = cur2.fetchone()
                    if comment_author:
                        dst = comment_author[0]
                        agg[(user_id, dst, 'like_comment')] += 1
                except sqlite3.Error:
                    pass
            elif action_type == 'follow_user':
                # Direct user-to-user interaction
                if target_id:
                    agg[(user_id, target_id, 'follow')] += 1
            elif action_type == 'post':
                # This is a post creation, doesn't create interaction edge
                pass
    except sqlite3.Error:
        pass

    # 2) comments table
    try:
        cur.execute("SELECT author_id, post_id FROM comments")
        for author_id, post_id in cur.fetchall():
            dst = post_author.get(post_id)
            if dst:
                agg[(author_id, dst, 'comment')] += 1
    except sqlite3.Error:
        pass

    # 3) follows table
    try:
        cur.execute("SELECT follower_id, followed_id FROM follows")
        for follower_id, followed_id in cur.fetchall():
            agg[(follower_id, followed_id, 'follow')] += 1
    except sqlite3.Error:
        pass

    # 4) note_ratings -> community_notes -> posts
    try:
        cur.execute(
            """
            SELECT r.user_id, n.post_id
            FROM note_ratings r
            JOIN community_notes n ON r.note_id = n.note_id
            """
        )
        for rater_id, post_id in cur.fetchall():
            dst = post_author.get(post_id)
            if dst:
                agg[(rater_id, dst, 'note_rating')] += 1
    except sqlite3.Error:
        pass

    return agg


def build_graph(conn: sqlite3.Connection) -> nx.DiGraph:
    users = fetch_users(conn)
    edges = build_edges(conn)

    G = nx.DiGraph()

    # Add nodes with attributes
    for uid, attrs in users.items():
        G.add_node(uid, **{k: ('' if v is None else v) for k, v in attrs.items()})

    # Also ensure nodes that appear only in edges are added
    for (src, dst, _), _w in edges.items():
        if src not in G:
            G.add_node(src)
        if dst not in G:
            G.add_node(dst)

    # Aggregate weights per (src, dst). Keep breakdown by type as attribute
    pair_weights = defaultdict(int)
    pair_types = defaultdict(lambda: defaultdict(int))

    for (src, dst, etype), w in edges.items():
        pair_weights[(src, dst)] += w
        pair_types[(src, dst)][etype] += w

    for (src, dst), total_w in pair_weights.items():
        breakdown = dict(pair_types[(src, dst)])
        # if multiple interactions exist, keep strongest as 'primary_type'
        primary_type = max(breakdown.items(), key=lambda kv: kv[1])[0]
        G.add_edge(
            src,
            dst,
            weight=total_w,
            primary_type=primary_type,
            breakdown=";".join(f"{k}:{v}" for k, v in sorted(breakdown.items())),
        )

    return G


def compute_communities_and_modularity(G: nx.DiGraph):
    """Project to weighted undirected graph, run greedy modularity communities, compute modularity.
    Returns (communities_list, modularity_value, undirected_graph).
    communities_list is a list of sets of nodes.
    """
    # Build undirected weighted graph by summing weights of both directions
    Gu = nx.Graph()
    for u, v, data in G.edges(data=True):
        w = float(data.get("weight", 1.0))
        if Gu.has_edge(u, v):
            Gu[u][v]["weight"] += w
        else:
            Gu.add_edge(u, v, weight=w)

    from networkx.algorithms import community as nx_comm

    if Gu.number_of_edges() == 0 or Gu.number_of_nodes() == 0:
        return [], 0.0, Gu

    comms = list(nx_comm.greedy_modularity_communities(Gu, weight="weight"))
    try:
        Q = nx_comm.modularity(Gu, comms, weight="weight")
    except Exception:
        Q = 0.0
    return comms, Q, Gu


def compute_betweenness(G: nx.DiGraph):
    """Compute weighted betweenness centrality on directed graph."""
    return nx.betweenness_centrality(G, weight="weight", normalized=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        conn = connect_readonly(DB_PATH)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    with conn:
        G = build_graph(conn)

    nx.write_gexf(G, OUTPUT_GEXF)

    # Summary
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    print("Graph built.")
    print(f"Nodes: {num_nodes}")
    print(f"Edges: {num_edges}")

    # Top 10 by out-degree weight
    out_strength = []
    for u in G.nodes:
        s = 0
        for _, _, data in G.out_edges(u, data=True):
            s += int(data.get('weight', 1))
        out_strength.append((u, s))
    out_strength.sort(key=lambda x: x[1], reverse=True)

    print("Top 10 nodes by out-strength (sum of outgoing edge weights):")
    for u, s in out_strength[:10]:
        print(f"  {u}: {s}")

    print(f"GEXF written to: {OUTPUT_GEXF}")

    # 1) Community detection + modularity (network fragmentation)
    comms, Q, Gu = compute_communities_and_modularity(G)
    print("\n[Modularity / Fragmentation]")
    print(f"Communities detected: {len(comms)}")
    print(f"Modularity (Q): {Q:.4f}")
    if comms:
        sizes = sorted([len(c) for c in comms], reverse=True)
        print(f"Largest community sizes: {sizes[:5]}")

        # Export communities assignment
        node2comm = {}
        for cid, cset in enumerate(comms):
            for n in cset:
                node2comm[n] = cid
        with open(OUTPUT_COMMUNITIES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "community_id"])
            for n in G.nodes:
                writer.writerow([n, node2comm.get(n, -1)])
        print(f"Communities CSV written to: {OUTPUT_COMMUNITIES_CSV}")

    # 2) Betweenness centrality (network integration)
    print("\n[Integration / Betweenness Centrality]")
    bc = compute_betweenness(G)
    # export
    with open(OUTPUT_CENTRALITY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "betweenness_centrality"])
        for n, v in sorted(bc.items(), key=lambda kv: kv[1], reverse=True):
            writer.writerow([n, f"{v:.8f}"])
    print(f"Betweenness centrality CSV written to: {OUTPUT_CENTRALITY_CSV}")

    # summary stats
    values = list(bc.values())
    if values:
        avg_bc = statistics.mean(values)
        med_bc = statistics.median(values)
        print(f"Average betweenness: {avg_bc:.6f}")
        print(f"Median betweenness: {med_bc:.6f}")
        print("Top 10 by betweenness:")
        for n, v in sorted(bc.items(), key=lambda kv: kv[1], reverse=True)[:10]:
            print(f"  {n}: {v:.6f}")


if __name__ == "__main__":
    main()
