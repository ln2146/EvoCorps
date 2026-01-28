import os
import sys
from types import SimpleNamespace


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class DummyEmbeddings:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])])


class DummyChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"theme":"Society & Ethics","keywords_full":"general","keyword":"general"}'
                    )
                )
            ]
        )


class DummyClient:
    def __init__(self, embeddings=None, chat_completions=None):
        self.embeddings = embeddings or DummyEmbeddings()
        self.chat = SimpleNamespace(completions=chat_completions or DummyChatCompletions())


class DummySelector:
    def __init__(self):
        self.embedding_client = DummyClient()
        self.chat_client = DummyClient()

    def create_embedding_client(self, model_name=None):
        return self.embedding_client, "dummy-embed"

    def create_openai_client_with_base_url(self, base_url=None, api_key=None, model_name=None, role=None):
        return self.chat_client, "dummy-chat"


def test_enhanced_opinion_system_uses_selector_clients(monkeypatch, tmp_path):
    import evidence_database.enhanced_opinion_system as eos

    dummy_selector = DummySelector()
    monkeypatch.setattr(eos, "multi_model_selector", dummy_selector)
    monkeypatch.setattr(eos, "configure_network_for_wikipedia", lambda: True)
    monkeypatch.setattr(eos, "test_wikipedia_connection", lambda: True)

    system = eos.EnhancedOpinionSystem(db_path=str(tmp_path / "opinion.db"))

    assert system.embedding_model_name == "dummy-embed"
    assert system.llm_model_name == "dummy-chat"

    system._get_embedding_from_api("hello")
    assert dummy_selector.embedding_client.embeddings.calls[0]["model"] == "dummy-embed"

    result = system._llm_classify_and_extract("test opinion")
    assert result["theme"] == "Society & Ethics"
    assert result["keyword"] == "general"
