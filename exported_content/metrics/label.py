#!/usr/bin/env python3

import os
import sys
import json
import re
import asyncio
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from src.keys import OPENAI_API_KEY, OPENAI_BASE_URL
from tqdm.asyncio import tqdm_asyncio

# ==============================================================================
# 🚀 CONFIGURATION SECTION
# ==============================================================================

class Config:
    # --- File path configuration ---
    ENV_PATH: Optional[str] = "exported_content/.env"
    INPUT_FILE_PATH: str = 'exported_content/data/output.jsonl'
    OUTPUT_FILE_PATH: str = 'exported_content/data/output_with_label.jsonl' # New output filename to reflect format change

    # --- API & model configuration ---
    API_KEY_ENV_VAR: str = "DEEPSEEK_API_KEY"
    BASE_URL_ENV_VAR: str = "DEEPSEEK_BASE_URL"
    MODEL_NAME: str = "DeepSeek-R1"
    MAX_TOKENS: int = 500
    TEMPERATURE: float = 0.5

    # --- Concurrent processing configuration ---
    NUM_LINES_TO_PROCESS: Optional[int] = 10
    MAX_CONCURRENT_REQUESTS: int = 50

    # --- System prompt (English) ---
    SYSTEM_PROMPT: str = """
Task Instructions：
You are a professional computational social scientist tasked with analyzing the emotion expressed in a text. Follow the General Rules for Judgment and the Emotion Definitions below to identify one primary emotion and one optional secondary emotion for the text.

General Rules for Judgment：
Primary Emotion: This is the author's core intent for writing the text. It is the most dominant and clearly expressed feeling that defines the overall tone.
Secondary Emotion: Only label a secondary emotion if a second, different emotion is also clearly present and provides important context or nuance to the primary emotion.
Guiding Principle: If you are uncertain about the secondary emotion, or if it is only a weak hint, you must set it to null. It is better to omit than to be inaccurate.

Emotion Label Definitions & Judgment Criteria：
This is a glossary of emotions to use for identifying the specific types.
1.Anger
Judgment Criteria: The text contains accusations, complaints, aggressive language, or expresses disappointment or a sense of being wronged. Examples: "This is outrageous," "That's going too far," "unacceptable."
2.Contempt / Derision
Judgment Criteria: The text includes personal attacks, sarcasm, negative labels for others (e.g., "stupid," "ignorant"), or shows a dismissive attitude, signaling intellectual or moral superiority.
3.Sadness / Disappointment
Judgment Criteria: The text reveals a sense of helplessness, nostalgia for something lost, or frustration over an outcome that didn't meet expectations. Examples: "What a shame," "I thought it would be better," "heartbreaking."
4.Anxiety / Worry
Judgment Criteria: The text focuses on "what if" scenarios and expresses nervousness, tension, and unease about an uncertain future. Examples: "I'm so worried it will fail," "I hope everything turns out okay."
5.Joy / Elation
Judgment Criteria: The text uses positive, high-energy words to express celebration, satisfaction, or excitement. Examples: "This is awesome!," "So happy!," "The best news."
6.Gratitude / Appreciation
Judgment Criteria: The text explicitly expresses thanks, praise, or admiration toward an entity (a person or organization). Examples: "Thank you so much," "You did an amazing job," "A tribute to the heroes."
7.Hope / Optimism
Judgment Criteria: The text looks to the future, expresses a belief that things will improve, or encourages others not to give up. Examples: "Tomorrow will be a better day," "We can definitely overcome this," "full of hope."
8.Curiosity / Confusion
Judgment Criteria: The text is primarily composed of questions intended to gather information or clarify facts, rather than being rhetorical or aggressive. Examples: "What does this mean?," "Could you explain that in more detail?."
9.Neutral / Factual
Judgment Criteria: The text consists of data, news reporting, or objective descriptions without personal emotional adjectives or exclamations. This label should not be used if any other discernible emotion is present.

Output Format：
Your output must be in strict JSON format, containing only the following two keys:
primary_emotion: [An emotion label from the list above]
secondary_emotion: [An emotion label from the list above] or null
Example Output:
{
"primary_emotion": "Contempt / Derision",
"secondary_emotion": "Anger"
}
or
{
"primary_emotion": "Hope / Optimism",
"secondary_emotion": null
}
"""

# ==============================================================================
# Helper Functions
# ==============================================================================

def setup_async_environment() -> AsyncOpenAI:
    """Set up the asynchronous OpenAI client."""
    load_dotenv(dotenv_path=Config.ENV_PATH)
    api_key = OPENAI_API_KEY
    base_url = OPENAI_BASE_URL
    try:
        return AsyncOpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        print(f"Error creating AsyncOpenAI client: {e}")
        sys.exit(1)

# ==============================================================================
# Main Async Logic Function
# ==============================================================================

async def get_structured_emotion_async(
    prompt: str, client: AsyncOpenAI, semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    Asynchronously call the API to extract emotions and return a dict containing status and prediction results.
    """
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": Config.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            if not content:
                return {"status": "error", "message": "API returned empty content."}

            try:
                data = json.loads(content)
                return {
                    "status": "success",
                    "prediction": {
                        "primary_emotion": data.get("primary_emotion"),
                        "secondary_emotion": data.get("secondary_emotion")
                    }
                }
            except json.JSONDecodeError:
                return {"status": "error", "message": "API returned invalid JSON.", "raw_output": content}

        except Exception as e:
            return {"status": "error", "message": f"API call or processing failed: {e}"}

# ==============================================================================
# Main Execution Block (Async)
# ==============================================================================

async def main():
    api_client = setup_async_environment()
    semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)

    print("=" * 80)
    print("      JSONL Emotion Labeling Program (Simple Output Format)")
    print("=" * 80)
    print(f"Reading input file: '{Config.INPUT_FILE_PATH}'")
    print(f"Writing to output file: '{Config.OUTPUT_FILE_PATH}'")
    print("-" * 80)

    try:
        with open(Config.INPUT_FILE_PATH, 'r', encoding='utf-8') as infile:
            jobs = [json.loads(line) for line in infile if line.strip()]
    except FileNotFoundError:
        print(f"Error: Input file not found at '{Config.INPUT_FILE_PATH}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSONL file. Please check the file format.")
        sys.exit(1)

    if Config.NUM_LINES_TO_PROCESS is not None:
        jobs = jobs[:Config.NUM_LINES_TO_PROCESS]

    tasks = []
    valid_jobs = []
    for job in jobs:
        user_query = job.get('user_query')
        if user_query:
            task = get_structured_emotion_async(user_query, api_client, semaphore)
            tasks.append(task)
            valid_jobs.append(job) # Only keep jobs that include a user_query

    print(f"Preparing to process {len(tasks)} valid records...")
    results = await tqdm_asyncio.gather(*tasks)

    successful_predictions = 0
    os.makedirs(os.path.dirname(Config.OUTPUT_FILE_PATH), exist_ok=True)
    with open(Config.OUTPUT_FILE_PATH, 'w', encoding='utf-8') as outfile:
        for original_data, result in zip(valid_jobs, results):
            # Only write records when the API call succeeds
            if result.get('status') == 'success':
                successful_predictions += 1
                prediction = result.get('prediction', {})
                
                # === Core modification: build the output format you requested ===
                output_record = {
                    "user_query": original_data.get('user_query'),
                    "primary_emotion": prediction.get('primary_emotion'),
                    "secondary_emotion": prediction.get('secondary_emotion')
                }
                
                outfile.write(json.dumps(output_record, ensure_ascii=False) + '\n')

    print("\n" + "=" * 80)
    print("Processing complete!")
    print(f"Total records processed: {len(tasks)}")
    print(f"Successful predictions saved: {successful_predictions}")
    print(f"Failed / Errors (not saved): {len(tasks) - successful_predictions}")
    print(f"Results saved to '{Config.OUTPUT_FILE_PATH}'")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
