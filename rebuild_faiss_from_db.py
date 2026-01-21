"""
Rebuilds the FAISS indexes in evidence_database so they stay synchronized with the current SQLite database.
Ensure the network is available and the API configuration in evidence_database/config.py is valid before running.
"""

import os
import sqlite3
import importlib.util
import sys

BASE = "evidence_database"

# Ensure config.py can be found
sys.path.insert(0, os.path.abspath(BASE))

# Remove existing index files first to avoid stale data
for name in ["faiss_viewpoint_index.bin", "faiss_keyword_index.bin", "viewpoint_ids.json"]:
    path = os.path.join(BASE, name)
    if os.path.exists(path):
        os.remove(path)
        print("deleted", path)
    else:
        print("not found", path)

# Dynamically load EnhancedOpinionSystem to avoid other dependencies in __init__
spec = importlib.util.spec_from_file_location(
    "enhanced_opinion_system", os.path.join(BASE, "enhanced_opinion_system.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
EnhancedOpinionSystem = module.EnhancedOpinionSystem

system = EnhancedOpinionSystem()

# Fetch viewpoints from the database
conn = sqlite3.connect(os.path.join(BASE, "opinion_database.db"))
cur = conn.cursor()
rows = cur.execute("SELECT id, viewpoint, key_words FROM viewpoints ORDER BY id").fetchall()
conn.close()

print("rebuilding", len(rows), "viewpoints")

for vid, vp, kw in rows:
    try:
        system._add_vector_to_faiss(vid, vp, kw)
    except Exception as e:
        print("fail", vid, e)

print("done", system.get_cache_stats())

