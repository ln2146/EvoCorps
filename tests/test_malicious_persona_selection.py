import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from simple_malicious_agent import SimpleMaliciousCluster, MaliciousPersona


def test_select_personas_returns_requested_count() -> None:
    cluster = SimpleMaliciousCluster(3)
    cluster.malicious_personas = [
        MaliciousPersona(
            persona_id="p1",
            name="Test Persona",
            age_range="20-30",
            profession="Tester",
            region="Testland",
            malicious_type="negative",
            typical_behaviors=["aggressive"],
            sample_responses=["bad response"],
            background="",
            communication_style={},
            personality_traits=[]
        )
    ]

    selected = cluster.select_personas(1)
    assert len(selected) == 1
