import os
import sys

from openai import OpenAI

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from keys import EMBEDDING_API_KEY, EMBEDDING_BASE_URL
from multi_model_selector import MultiModelSelector


def main() -> None:
    model_name = MultiModelSelector.EMBEDDING_MODEL
    if not EMBEDDING_API_KEY or not EMBEDDING_BASE_URL:
        raise ValueError("EMBEDDING_API_KEY / EMBEDDING_BASE_URL 未配置")

    client = OpenAI(
        api_key=EMBEDDING_API_KEY,
        base_url=EMBEDDING_BASE_URL,
        timeout=60,
    )

    response = client.embeddings.create(
        model=model_name,
        input="你好，今天天气怎么样.",
        dimensions=2,
    )

    embedding = response.data[0].embedding
    print(f"model={model_name}")
    print(f"embedding_dim={len(embedding)}")
    print(f"embedding_preview={embedding[:2]}")


if __name__ == "__main__":
    main()
