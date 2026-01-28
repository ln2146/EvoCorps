import pathlib


FILES_TO_CHECK = [
    "src/agent_user.py",
    "src/advanced_rag_system.py",
    "src/news_manager.py",
    "src/prolific_replication_experiment.py",
    "src/interview_agents.py",
    "src/model_selector.py",
    "src/fact_checker.py",
    "src/simulation.py",
    "src/enhanced_leader_agent.py",
    "src/agents/simple_coordination_system.py",
]


def test_no_direct_openai_clients_for_llm_paths() -> None:
    for path in FILES_TO_CHECK:
        content = pathlib.Path(path).read_text(encoding="utf-8")
        assert "OpenAI(" not in content
