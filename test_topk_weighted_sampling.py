import os
import sys
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from recommender.config import SelectionConfig
from recommender.selectors.top_k_selector import TopKSelector
from recommender.types import FeedSource, PostCandidate


def make_candidate(idx: int, is_news: bool, score: float) -> PostCandidate:
    return PostCandidate(
        post_id=f"post-{idx}",
        content=f"content-{idx}",
        author_id=f"author-{idx}",
        source=FeedSource.OUT_NETWORK,
        is_news=is_news,
        news_type="real" if is_news else None,
        final_score=score,
    )


class TopKWeightedSamplingTest(unittest.TestCase):
    def test_select_should_not_drop_count_due_to_duplicate_sampling(self):
        cfg = SelectionConfig(
            news_top_k=10,
            news_pick_n=5,
            news_secondary_offset=10,
            news_secondary_top_k=10,
            news_secondary_pick_n=3,
            non_news_top_k=10,
            non_news_pick_n=2,
            include_ties=False,
        )
        selector = TopKSelector(cfg)

        news = [make_candidate(i, True, 200 - i) for i in range(25)]
        non_news = [make_candidate(100 + i, False, 100 - i) for i in range(25)]
        candidates = news + non_news

        # Simulate the previous with-replacement behavior always returning duplicates.
        with patch(
            "recommender.selectors.top_k_selector.random.choices",
            side_effect=lambda population, weights=None, k=1: [population[0]] * k
        ):
            selected = selector.select(candidates)

        self.assertEqual(10, len(selected), "Expected full selection size when candidate pools are sufficient")
        self.assertEqual(10, len({c.post_id for c in selected}), "Selected posts should be unique")


if __name__ == "__main__":
    unittest.main()

