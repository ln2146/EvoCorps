import json
import os
from tqdm import tqdm
from keys import OPENAI_API_KEY, OPENAI_BASE_URL
from openai import OpenAI
from agent_user import FeedReaction
from utils import Utils

def get_prompt():
    return """
You are a specialized parser that converts social media feed actions into a structured JSON format. Your task is to identify actions like likes, shares, comments, follows, etc. and their targets.

The output must follow this exact structure:
{{
    "actions": [
        {{
            "action": "<like-post|share-post|comment-post|ignore>",
            "target": "<post-id|null>",
            "content": "<comment-content|null>"
        }}
    ]
}}

Action types should be one of:
- "like-post" (for likes, upvotes, hearts)
- "share-post" (for reposts, retweets, sharing)
- "comment-post" (for replies, comments)
- "ignore" (when no clear action is found)

Examples:

Input: "I liked post #12345"
Output:
{{
    "actions": [
        {{
            "action": "like-post",
            "target": "post-12345"
        }}
    ]
}}

Input: "I liked post #12345 and commented 'This is a comment'"
Output:
{{
    "actions": [
        {{
            "action": "like-post",  
            "target": "post-12345",
        }},
        {{
            "action": "comment-post",
            "target": "post-12345",
            "content": "This is a comment"
        }}
    ]
}}

Input: "Nothing interesting here"
Output:
{{
    "actions": [
        {{
            "action": "ignore",
            "target": null
        }}
    ]
}}

Here is the content to parse:

{content}

IMPORTANT INSTRUCTIONS:
1. Return ONLY the JSON object, nothing else
2. Do not wrap the response in ```json``` or any other markdown/code blocks
3. Make sure the JSON is valid and can be parsed
4. No markdown formatting is allowed. Just simple JSON
"""

def process_feed_content(feed_content, client):
    try:
        # Get the completion from GPT
        response = Utils.generate_llm_response(
            openai_client=client,
            engine="gpt-4",
            prompt=get_prompt().format(content=feed_content),
            system_message="You are a helpful assistant that reformats social media feed actions into JSON format with an 'actions' array. Each action should have 'action' and 'target' fields.",
            temperature=0.0
        )
        
        # Parse the response as JSON
        if isinstance(response, str):
            try:
                parsed_response = json.loads(response)
                return parsed_response
            except json.JSONDecodeError:
                print(f"Failed to parse response as JSON: {response}")
                return {"actions": [{"action": "ignore", "target": None, "content": None}]}
        else:
            return {"actions": [{"action": "ignore", "target": None, "content": None}]}
            
    except Exception as e:
        print(f"Error processing content: {e}")
        return {"actions": [{"action": "ignore", "target": None, "content": None}]}

def main():
    # Initialize OpenAI client
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )

    input_file = 'human_study_data.jsonl'
    output_file = 'formatted_social_feeds.jsonl'

    # First, load already processed IDs from output file
    processed_prolific_ids = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    processed_prolific_ids.add(entry['prolific_id'])
                except:
                    continue

    print(f"Found {len(processed_prolific_ids)} already processed IDs")
    print(f"Reading input file: {input_file}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        # Read all lines first
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"Successfully read {len(lines)} lines")
            
        # Process each line
        with open(output_file, 'a', encoding='utf-8') as outfile:  # Changed to 'a' mode to append
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    print(f"Empty line at {i}")
                    continue
                    
                try:
                    print(f"Processing line {i}")
                    entry = json.loads(line)
                    
                    if entry['prolific_id'] in processed_prolific_ids:
                        print(f"Already processed: {entry['prolific_id']}")
                        continue
                        
                    # Process feeds
                    if entry.get('social_feed_1'):
                        entry['social_feed_1'] = process_feed_content(entry['social_feed_1'], client)
                        
                    if entry.get('social_feed_2'):
                        entry['social_feed_2'] = process_feed_content(entry['social_feed_2'], client)
                        
                    # Write to output
                    outfile.write(json.dumps(entry) + '\n')
                    outfile.flush()
                    
                    processed_prolific_ids.add(entry['prolific_id'])
                    print(f"Successfully processed line {i}")
                    
                except Exception as e:
                    print(f"Error on line {i}: {str(e)}")
                    continue
                    
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise

if __name__ == '__main__':
    main()

