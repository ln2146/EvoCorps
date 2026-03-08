import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from recommender.feed_pipeline import FeedPipeline
from recommender.config import RecommenderConfig
from recommender.types import FeedRequest, PipelineContext, UserContext, PostCandidate, FeedSource


def make_candidate(post_id: str, source: FeedSource) -> PostCandidate:
    return PostCandidate(
        post_id=post_id,
        content=f"content-{post_id}",
        author_id=f"author-{post_id}",
        source=source,
        is_news=(source == FeedSource.OUT_NETWORK),
    )


class Stage2RatioRoutingTest(unittest.TestCase):
    def setUp(self):
        FeedPipeline.configure_parallel(False)
        cfg = RecommenderConfig.from_dict({
            "embedding": {"enabled": False},
            "source": {
                "in_network_ratio": 0.25,
                "out_network_ratio": 0.75,
                "max_candidates_per_source": 20
            }
        })
        self.pipeline = FeedPipeline(cfg)

    def _new_ctx(self) -> PipelineContext:
        return PipelineContext(
            request=FeedRequest(user_id="u1", time_step=1),
            user_context=UserContext(user_id="u1", followed_ids={"f1"}),
            candidates=[],
            post_timesteps={},
            metadata={}
        )

    def test_stage2_should_apply_source_ratio_within_budget(self):
        in_pool = [make_candidate(f"in-{i}", FeedSource.IN_NETWORK) for i in range(50)]
        out_pool = [make_candidate(f"out-{i}", FeedSource.OUT_NETWORK) for i in range(50)]

        self.pipeline.in_network_source.retrieve = lambda user_context, max_candidates=100: in_pool[:max_candidates]
        self.pipeline.out_network_source.retrieve = lambda user_context, max_candidates=100, time_step=None: out_pool[:max_candidates]

        ctx = self.pipeline._stage2_candidate_retrieval(self._new_ctx())

        in_count = sum(1 for c in ctx.candidates if c.source == FeedSource.IN_NETWORK)
        out_count = sum(1 for c in ctx.candidates if c.source == FeedSource.OUT_NETWORK)

        self.assertEqual(20, len(ctx.candidates))
        self.assertEqual(5, in_count)
        self.assertEqual(15, out_count)
        self.assertEqual(5, ctx.metadata.get("in_network_target"))
        self.assertEqual(15, ctx.metadata.get("out_network_target"))

    def test_stage2_should_backfill_when_one_side_insufficient(self):
        in_pool = [make_candidate(f"in-{i}", FeedSource.IN_NETWORK) for i in range(2)]
        out_pool = [make_candidate(f"out-{i}", FeedSource.OUT_NETWORK) for i in range(50)]

        self.pipeline.in_network_source.retrieve = lambda user_context, max_candidates=100: in_pool[:max_candidates]
        self.pipeline.out_network_source.retrieve = lambda user_context, max_candidates=100, time_step=None: out_pool[:max_candidates]

        ctx = self.pipeline._stage2_candidate_retrieval(self._new_ctx())

        in_count = sum(1 for c in ctx.candidates if c.source == FeedSource.IN_NETWORK)
        out_count = sum(1 for c in ctx.candidates if c.source == FeedSource.OUT_NETWORK)

        self.assertEqual(20, len(ctx.candidates))
        self.assertEqual(2, in_count)
        self.assertEqual(18, out_count)


if __name__ == "__main__":
    unittest.main()
