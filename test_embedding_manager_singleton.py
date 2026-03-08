import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from recommender.config import EmbeddingConfig
from recommender.scorers.embedding_scorer import EmbeddingScorer


class EmbeddingManagerSingletonTest(unittest.TestCase):
    def test_same_config_should_share_one_embedding_manager(self):
        cfg = EmbeddingConfig(
            enabled=True,
            model_name='paraphrase-MiniLM-L6-v2',
            use_openai_embedding=False,
            cache_embeddings=True,
            max_cache_size=10000,
        )

        manager_ids = []

        def create_and_get_id(_):
            scorer = EmbeddingScorer(cfg)
            self.assertIsNotNone(scorer.embedding_manager)
            return id(scorer.embedding_manager)

        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = [ex.submit(create_and_get_id, i) for i in range(30)]
            for f in as_completed(futures):
                manager_ids.append(f.result())

        self.assertEqual(
            1,
            len(set(manager_ids)),
            msg=f"Expected one shared manager, got {len(set(manager_ids))}: {set(manager_ids)}"
        )


if __name__ == '__main__':
    unittest.main()
