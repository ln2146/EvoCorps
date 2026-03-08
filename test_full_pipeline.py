#!/usr/bin/env python3
"""
Comprehensive end-to-end test for recommender + moderation integration
"""
import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

print("=" * 60)
print("Comprehensive E2E Test: Recommender + Moderation")
print("=" * 60)

# Test 1: FeedPipeline instantiation
print("\n[1/6] Testing FeedPipeline instantiation...")
try:
    from recommender import FeedPipeline, FeedRequest, UserContext
    pipeline = FeedPipeline()
    print("    - FeedPipeline created successfully")
    print(f"    - Has moderation_filter: {hasattr(pipeline, 'moderation_filter')}")
    OK_1 = True
except Exception as e:
    print(f"    - ERROR: {e}")
    import traceback
    traceback.print_exc()
    OK_1 = False

# Test 2: Test moderation filter with control_flags disabled
print("\n[2/6] Testing moderation filter when control_flags.moderation_enabled=False...")
try:
    import control_flags
    control_flags.moderation_enabled = False

    from recommender.types import PostCandidate
    from recommender.filters.moderation_filter import ModerationFilter

    # Create test candidates
    candidates = [
        PostCandidate(
            post_id="test1",
            content="test post 1",
            author_id="user1",
            final_score=100.0,
            moderation_degradation_factor=0.5,
            moderation_label="Warning"
        ),
        PostCandidate(
            post_id="test2",
            content="test post 2",
            author_id="user2",
            final_score=80.0,
            status="taken_down"
        )
    ]

    filter_obj = ModerationFilter()
    # With control_flags.moderation_enabled=False and config.enabled=False,
    # the filter should return all candidates unchanged
    result = filter_obj.filter(candidates)
    print(f"    - Input: 2 candidates (1 with degradation, 1 taken_down)")
    print(f"    - Output: {len(result)} candidates (filter bypassed)")
    print(f"    - control_flags.moderation_enabled={control_flags.moderation_enabled}")
    OK_2 = len(result) == 2
except Exception as e:
    print(f"    - ERROR: {e}")
    import traceback
    traceback.print_exc()
    OK_2 = False

# Test 3: Test moderation filter with control_flags enabled
print("\n[3/6] Testing moderation filter when control_flags.moderation_enabled=True...")
try:
    control_flags.moderation_enabled = True

    candidates = [
        PostCandidate(
            post_id="test1",
            content="test post 1",
            author_id="user1",
            final_score=100.0,
            moderation_degradation_factor=0.5,
            moderation_label="Warning"
        ),
        PostCandidate(
            post_id="test2",
            content="test post 2",
            author_id="user2",
            final_score=80.0,
            status="taken_down"
        ),
        PostCandidate(
            post_id="test3",
            content="test post 3",
            author_id="user3",
            final_score=60.0,
            moderation_degradation_factor=1.0,
            moderation_label=None
        )
    ]

    filter_obj = ModerationFilter()
    # Create a config with filter_taken_down=True
    from moderation.types import ModerationFilterConfig
    config = ModerationFilterConfig(enabled=True, filter_taken_down=True)
    filter_obj.set_config(config)

    result = filter_obj.filter(candidates)
    print(f"    - Input: 3 candidates")
    print(f"    - Output: {len(result)} candidates")
    print(f"    - Expected: 2 (taken_down filtered out)")
    if len(result) >= 2:
        for c in result:
            print(f"      * {c.post_id}: score={c.final_score:.2f}, degradation={c.moderation_degradation_factor}, label={c.moderation_label}")
    OK_3 = len(result) == 2
except Exception as e:
    print(f"    - ERROR: {e}")
    import traceback
    traceback.print_exc()
    OK_3 = False

# Test 4: Test AuthorCredibilityScorer
print("\n[4/6] Testing AuthorCredibilityScorer...")
try:
    from recommender.config import AuthorCredibilityConfig
    from recommender.scorers.author_credibility_scorer import AuthorCredibilityScorer

    config = AuthorCredibilityConfig(enabled=True)
    scorer = AuthorCredibilityScorer(config)

    candidates = [
        PostCandidate(
            post_id="test1",
            content="test",
            author_id="user1",
            weighted_score=100.0,
            author_influence_score=0.9  # High credibility
        ),
        PostCandidate(
            post_id="test2",
            content="test",
            author_id="user2",
            weighted_score=100.0,
            author_influence_score=0.2  # Low credibility (bot)
        ),
        PostCandidate(
            post_id="test3",
            content="test",
            author_id="user3",
            weighted_score=100.0,
            author_influence_score=0.5  # Neutral
        )
    ]

    result = scorer.score(candidates)
    print(f"    - High influence (0.9): {result[0].final_score:.2f} (expected > 100)")
    print(f"    - Low influence (0.2): {result[1].final_score:.2f} (expected < 100)")
    print(f"    - Neutral influence (0.5): {result[2].final_score:.2f} (expected ~100)")

    OK_4 = (result[0].final_score > result[2].final_score and
             result[1].final_score < result[2].final_score)
except Exception as e:
    print(f"    - ERROR: {e}")
    import traceback
    traceback.print_exc()
    OK_4 = False

# Test 5: Test experiment config loading
print("\n[5/6] Testing experiment config loading...")
try:
    import json
    config_path = os.path.join(script_dir, 'configs', 'experiment_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    recommender_config = config.get('recommender', {})
    has_author_credibility = 'author_credibility' in recommender_config
    has_enabled = recommender_config.get('recommender', {}).get('enabled') if 'recommender' in config else False

    print(f"    - Recommender enabled: {recommender_config.get('enabled', 'NOT SET')}")
    print(f"    - author_credibility section exists: {has_author_credibility}")
    if has_author_credibility:
        ac = recommender_config['author_credibility']
        print(f"    - author_credibility.enabled: {ac.get('enabled')}")

    OK_5 = recommender_config.get('enabled') and has_author_credibility
except Exception as e:
    print(f"    - ERROR: {e}")
    OK_5 = False

# Test 6: Verify all components are wired in FeedPipeline
print("\n[6/6] Verifying FeedPipeline has all stages...")
try:
    from recommender import FeedPipeline
    pipeline = FeedPipeline()

    stages = {
        'Stage 1 (Query Hydration)': hasattr(pipeline, 'user_action_hydrator') and hasattr(pipeline, 'user_features_hydrator'),
        'Stage 2 (Sources)': hasattr(pipeline, 'in_network_source') and hasattr(pipeline, 'out_network_source'),
        'Stage 3 (Hydration)': hasattr(pipeline, 'core_data_hydrator') and hasattr(pipeline, 'author_hydrator'),
        'Stage 4 (Pre-Scoring Filters)': hasattr(pipeline, 'pre_scoring_filters'),
        'Stage 5 (Scorers)': hasattr(pipeline, 'weighted_scorer'),
        'Stage 5.35 (Author Credibility)': hasattr(pipeline, 'credibility_scorer'),
        'Stage 6 (Selector)': hasattr(pipeline, 'selector'),
        'Stage 7 (Post-Selection Filters)': hasattr(pipeline, 'moderation_filter'),
    }

    for stage, ok in stages.items():
        status = "OK" if ok else "MISSING"
        print(f"    - {stage}: {status}")

    OK_6 = all(stages.values())
except Exception as e:
    print(f"    - ERROR: {e}")
    import traceback
    traceback.print_exc()
    OK_6 = False

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
all_ok = OK_1 and OK_2 and OK_3 and OK_4 and OK_5 and OK_6
if all_ok:
    print("Result: ALL TESTS PASSED")
    print("\nThe X algorithm recommender and moderation system are")
    print("properly integrated and ready for use.")
    print("\nFeatures verified:")
    print("  - 7-stage recommendation pipeline")
    print("  - Author credibility scoring (Stage 5.35)")
    print("  - Moderation filtering (Stage 7)")
    print("  - Integration with control_flags")
    sys.exit(0)
else:
    print("Result: SOME TESTS FAILED")
    print("\nPlease review errors above.")
    sys.exit(1)
