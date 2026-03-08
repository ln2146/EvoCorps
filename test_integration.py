#!/usr/bin/env python3
"""
Health check script for moderation system and recommender integration
"""
import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

print("=" * 60)
print("Health Check: Moderation + Recommender Integration")
print("=" * 60)

# Test 1: Check control_flags
print("\n[1/5] Checking control_flags...")
try:
    import control_flags
    print(f"    - moderation_enabled: {control_flags.moderation_enabled}")
    print(f"    - Module loaded successfully")
    OK_1 = True
except Exception as e:
    print(f"    - ERROR: {e}")
    OK_1 = False

# Test 2: Check PostCandidate has moderation fields
print("\n[2/5] Checking PostCandidate moderation fields...")
try:
    from recommender.types import PostCandidate
    candidate = PostCandidate(
        post_id="test",
        content="test",
        author_id="user1",
        moderation_degradation_factor=0.5,
        moderation_label="Warning"
    )
    print(f"    - moderation_degradation_factor: {candidate.moderation_degradation_factor}")
    print(f"    - moderation_label: {candidate.moderation_label}")
    print(f"    - Fields exist and work correctly")
    OK_2 = True
except Exception as e:
    print(f"    - ERROR: {e}")
    OK_2 = False

# Test 3: Check ModerationFilter
print("\n[3/5] Checking ModerationFilter...")
try:
    from recommender.filters.moderation_filter import ModerationFilter
    filter_obj = ModerationFilter()
    print(f"    - ModerationFilter instantiated")
    print(f"    - Has _is_user_banned: {hasattr(filter_obj, '_is_user_banned')}")
    print(f"    - Has get_warning_label: {hasattr(filter_obj, 'get_warning_label')}")
    OK_3 = True
except Exception as e:
    print(f"    - ERROR: {e}")
    OK_3 = False

# Test 4: Check from_db_row loads moderation fields
print("\n[4/5] Checking PostCandidate.from_db_row()...")
try:
    from recommender.types import PostCandidate
    db_row = {
        'post_id': 'test1',
        'content': 'test content',
        'author_id': 'user1',
        'moderation_degradation_factor': 0.3,
        'moderation_label': 'Misinformation'
    }
    candidate = PostCandidate.from_db_row(db_row)
    print(f"    - moderation_degradation_factor loaded: {candidate.moderation_degradation_factor}")
    print(f"    - moderation_label loaded: {candidate.moderation_label}")
    assert candidate.moderation_degradation_factor == 0.3
    assert candidate.moderation_label == 'Misinformation'
    print(f"    - from_db_row() correctly loads moderation fields")
    OK_4 = True
except Exception as e:
    print(f"    - ERROR: {e}")
    OK_4 = False

# Test 5: Check experiment_config.json has author_credibility
print("\n[5/5] Checking experiment_config.json...")
try:
    import json
    config_path = os.path.join(script_dir, 'configs', 'experiment_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    assert 'author_credibility' in config['recommender']
    ac = config['recommender']['author_credibility']
    print(f"    - author_credibility section exists")
    print(f"    - enabled: {ac.get('enabled')}")
    print(f"    - high_credibility_threshold: {ac.get('high_credibility_threshold')}")
    print(f"    - low_credibility_penalty: {ac.get('low_credibility_penalty')}")
    print(f"    - Config loaded successfully")
    OK_5 = True
except Exception as e:
    print(f"    - ERROR: {e}")
    OK_5 = False

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
all_ok = OK_1 and OK_2 and OK_3 and OK_4 and OK_5
if all_ok:
    print("Result: ALL CHECKS PASSED")
    print("\nThe moderation system and recommender are properly integrated.")
    print("\nTo enable moderation:")
    print("  - Set control_flags.moderation_enabled = True")
    print("  - Or enable via CLI/HTTP control API")
    sys.exit(0)
else:
    print("Result: SOME CHECKS FAILED")
    print("\nPlease review errors above.")
    sys.exit(1)
