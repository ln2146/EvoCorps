import pathlib


FILES_TO_CHECK = [
    "src/agent_user.py",
    "src/agents/simple_coordination_system.py",
    "src/auto_export_manager.py",
    "src/interview_agents.py",
    "src/news_manager.py",
    "src/opinion_balance_launcher.py",
    "src/process_human_data.py",
    "src/scenario_export_manager.py",
]

HARD_CODED_MODELS = [
    "gemini-2.0-flash",
    "gpt-4.1-nano",
    "deepseek-chat",
    "gpt-4",
]


def test_no_hardcoded_model_defaults_in_app_files() -> None:
    for path in FILES_TO_CHECK:
        content = pathlib.Path(path).read_text(encoding="utf-8")
        for model in HARD_CODED_MODELS:
            assert model not in content, f"{path} still hardcodes {model}"
