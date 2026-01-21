import json
import pandas as pd
from collections import Counter

# Read the JSONL file
def read_jsonl(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def analyze_user_demographics(data):
    demographics = {
        'age': Counter(),
        'gender': Counter(),
        'education': Counter(),
        'political_stance': Counter(),
        'type_of_residence': Counter()
    }
    
    for entry in data:
        for key in demographics:
            demographics[key][entry[key]] += 1
    
    return demographics

def analyze_social_interactions(data):
    feed_stats = {
        'social_feed_1': {'likes': 0, 'shares': 0, 'comments': 0, 'comment_texts': []},
        'social_feed_2': {'likes': 0, 'shares': 0, 'comments': 0, 'comment_texts': []}
    }
    
    # Print first entry to debug
    print("Sample data entry:")
    print(json.dumps(data[0], indent=2))
    
    for entry in data:
        # Check if the entry is a dictionary and has the expected structure
        if not isinstance(entry, dict):
            print(f"Unexpected entry type: {type(entry)}")
            continue
            
        for feed_type in ['social_feed_1', 'social_feed_2']:
            if feed_type not in entry:
                continue
                
            feed_data = entry[feed_type]
            if not isinstance(feed_data, dict) or 'actions' not in feed_data:
                continue
                
            for action in feed_data['actions']:
                action_type = action.get('action', '')
                if action_type == 'like-post':
                    feed_stats[feed_type]['likes'] += 1
                elif action_type == 'share-post':
                    feed_stats[feed_type]['shares'] += 1
                elif action_type == 'comment-post':
                    feed_stats[feed_type]['comments'] += 1
                    content = action.get('content')
                    if content:
                        feed_stats[feed_type]['comment_texts'].append(content)
    
    return feed_stats

def main():
    # Read the data
    data = read_jsonl('formatted_social_feed_reactions.jsonl')
    
    # Analyze demographics
    demographics = analyze_user_demographics(data)
    
    # Analyze social interactions
    interactions = analyze_social_interactions(data)
    
    # Print results
    print("\nDemographic Distribution:")
    for category, counts in demographics.items():
        print(f"\n{category.upper()}:")
        for value, count in counts.most_common():
            print(f"{value}: {count}")
    
    print("\nSocial Feed Interactions:")
    for feed_type, stats in interactions.items():
        print(f"\n{feed_type}:")
        print(f"Total likes: {stats['likes']}")
        print(f"Total shares: {stats['shares']}")
        print(f"Total comments: {stats['comments']}")
        if stats['comment_texts']:
            print("Sample comments:")
            for comment in stats['comment_texts'][:3]:
                print(f"- {comment}")

if __name__ == "__main__":
    main()
