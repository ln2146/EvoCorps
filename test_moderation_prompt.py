"""
测试新审核 prompt 对假新闻库的拦截率
随机抽 50 条假新闻，调用 LLM 审核，统计 flagged 比例
"""
import json
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from moderation.providers.llm_provider import LLMProvider
from moderation.config import ModerationProviderConfig


def main():
    # 加载假新闻库
    with open('data/misinformation-news.json', 'r', encoding='utf-8') as f:
        all_news = json.load(f)

    # 随机抽 50 条
    random.seed(42)
    sample = random.sample(all_news, min(50, len(all_news)))

    # 初始化 LLM Provider
    config = ModerationProviderConfig(enabled=True, threshold=0.6)
    provider = LLMProvider(config)

    flagged_count = 0
    pass_count = 0
    error_count = 0
    results = []

    for i, item in enumerate(sample):
        fake_text = item['Fake Narrative']
        short = fake_text[:60].replace('\n', ' ')
        print(f"[{i+1:2d}/50] Checking: {short}...")

        try:
            verdict = provider.check(fake_text)
            if verdict:
                flagged_count += 1
                cat = verdict.category
                sev = verdict.severity
                conf = verdict.confidence
                reason = verdict.reason
                print(f"        FLAGGED  [{sev}/{cat}] conf={conf:.2f} | {reason}")
                results.append({
                    'index': i+1,
                    'text_preview': short,
                    'flagged': True,
                    'category': str(cat),
                    'severity': str(sev),
                    'confidence': conf,
                    'reason': reason,
                })
            else:
                pass_count += 1
                print(f"        PASS")
                results.append({
                    'index': i+1,
                    'text_preview': short,
                    'flagged': False,
                })
        except Exception as e:
            error_count += 1
            print(f"        ERROR: {e}")
            results.append({
                'index': i+1,
                'text_preview': short,
                'flagged': None,
                'error': str(e),
            })

    # 汇总
    print("\n" + "=" * 60)
    print(f"RESULTS: {flagged_count} flagged / {pass_count} pass / {error_count} errors (total {len(sample)})")
    print(f"Interception rate: {flagged_count / max(1, flagged_count + pass_count) * 100:.1f}%")
    print(f"Pass rate:         {pass_count / max(1, flagged_count + pass_count) * 100:.1f}%")

    if flagged_count > 0:
        print("\nFlagged items breakdown:")
        cats = {}
        for r in results:
            if r.get('flagged'):
                c = r['category']
                cats[c] = cats.get(c, 0) + 1
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

    # 保存详细结果
    with open('logs/moderation_prompt_test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total': len(sample),
                'flagged': flagged_count,
                'passed': pass_count,
                'errors': error_count,
                'interception_rate': f"{flagged_count / max(1, flagged_count + pass_count) * 100:.1f}%",
            },
            'details': results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to logs/moderation_prompt_test_results.json")


if __name__ == '__main__':
    main()
