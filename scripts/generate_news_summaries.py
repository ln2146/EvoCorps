import jsonlines
import os
from typing import List, Dict

NEWS_FILE = os.path.join("data", "news_ordered.jsonl")
BACKUP_FILE = os.path.join("data", "news_ordered_original.jsonl")
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

    # Backup original file before overwriting
    if not os.path.exists(BACKUP_FILE):
        os.rename(NEWS_FILE, BACKUP_FILE)
    else:
        os.remove(NEWS_FILE)

    with jsonlines.open(NEWS_FILE, "w") as writer:
        for article in articles:
            writer.write(article)


if __name__ == "__main__":
    main()
