import jsonlines
import os
from typing import List, Dict

NEWS_FILE = os.path.join("data", "news_ordered.jsonl")
MAX_WORDS = 30


def _generate_summary(article: Dict[str, str]) -> str:
    """Create a deterministic <=30-word summary combining title and description/content."""
    candidates = [
        article.get("summary", ""),
        article.get("description", ""),
        article.get("content", ""),
        article.get("title", ""),
    ]
    text = next((c for c in candidates if c), "")
    text = text.replace("\n", " ").strip()
    if not text:
        return ""
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])
    return text


def main() -> None:
    # Load existing articles
    with jsonlines.open(NEWS_FILE) as reader:
        articles: List[Dict[str, str]] = list(reader)

    # Generate summaries
    for article in articles:
        summary = _generate_summary(article)
        if summary:
            article["summary"] = summary

    tmp_path = f"{NEWS_FILE}.tmp"
    try:
        with jsonlines.open(tmp_path, "w") as writer:
            for article in articles:
                writer.write(article)
        os.replace(tmp_path, NEWS_FILE)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
