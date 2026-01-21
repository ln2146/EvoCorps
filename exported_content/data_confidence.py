#!/usr/bin/env python3

import os
import sys
import json
import re
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from src.keys import OPENAI_API_KEY, OPENAI_BASE_URL

# ==============================================================================
# 🚀 CONFIGURATION SECTION
# ==============================================================================

class Config:
    ENV_PATH: Optional[str] = "exported_content/.env"
    API_KEY_ENV_VAR: str = "DEEPSEEK_API_KEY"
    BASE_URL_ENV_VAR: str = "DEEPSEEK_BASE_URL"
    MODEL_NAME: str = "DeepSeek-V3"
    MAX_TOKENS: int = 500
    TEMPERATURE: float = 0.7  # Optimization: lower from 1 to 0.7 to avoid excessive randomness
    PRIMARY_EMOTION_WEIGHT: float = 0.7
    SECONDARY_EMOTION_WEIGHT: float = 0.3
    SYSTEM_PROMPT: str = """
Task Instructions: You are a professional computational social scientist tasked with identifying the primary emotion expressed in the provided text and optionally a secondary emotion. Follow the definitions below when classifying emotions.
Primary Emotion: The most dominant or clearly articulated emotion in the text.
Secondary Emotion: A distinct secondary emotion that is present; set to null if absent or uncertain.
Emotion label definitions:
1. Anger: Includes blame, complaints, or aggressive language.
2. Contempt / Derision: Contains personal attacks, sarcasm, or superiority.
3. Sadness / Disappointment: Expresses helplessness or frustration.
4. Anxiety / Worry: Shows tension, concern, or uncertainty about the future.
5. Joy / Elation: Expresses celebration, satisfaction, or excitement.
6. Gratitude / Appreciation: Explicitly expresses thankfulness or praise.
7. Hope / Optimism: Looks to the future with a belief that things will improve.
8. Curiosity / Confusion: Driven by questions or information seeking.
9. Neutral / Factual: Objective description without personal emotional tone.
Output format: Respond in strict JSON containing only the keys "primary_emotion" and "secondary_emotion".
Example: {"primary_emotion": "Contempt / Derision", "secondary_emotion": "Anger"}
"""

# ==============================================================================
# Helper Functions
# ==============================================================================

def setup_environment() -> OpenAI:
    load_dotenv(dotenv_path=Config.ENV_PATH)
    api_key = OPENAI_API_KEY
    base_url = OPENAI_BASE_URL
    if not api_key or not base_url:
        print(f"ERROR: Missing {Config.API_KEY_ENV_VAR} or {Config.BASE_URL_ENV_VAR} in the environment.")
        sys.exit(1)
    try:
        return OpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        print(f"Failed to create OpenAI client: {e}")
        sys.exit(1)

# MODIFIED FUNCTION 1: Now returns a list of (token, probability) tuples
def find_value_token_probs(full_text: str, all_tokens_logprobs: List[Any], target_value: Any) -> List[Tuple[str, float]]:
    """
    Precisely locates the tokens for a target value and returns their strings and probabilities.
    """
    if target_value is None:
        target_str = "null"
    else:
        # Standard way to get the string representation from the JSON value
        target_str = json.dumps(target_value, ensure_ascii=False).strip('"')

    start_index = full_text.find(target_str)
    
    if start_index == -1:
        return []

    token_probs = []
    current_pos = 0
    collected_str = ""
    
    for lp in all_tokens_logprobs:
        token_str = lp.token
        if start_index <= current_pos < start_index + len(target_str):
            # Append a tuple of (token_string, probability)
            token_probs.append((token_str, np.exp(lp.logprob)))
            collected_str += token_str
        
        current_pos += len(token_str)
        
        if collected_str == target_str:
            break
            
    return token_probs

# MODIFIED FUNCTION 2: Now accepts a list of (token, probability) tuples
def calculate_average_prob(token_probs: List[Tuple[str, float]]) -> float:
    """Calculates the average probability from a list of (token, probability) tuples."""
    if not token_probs:
        return 0.0
    # Extract just the probabilities (the second item in each tuple)
    probs = [p for _, p in token_probs]
    return sum(probs) / len(probs)

def clean_json_string(text: str) -> str:
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

# ==============================================================================
# Main Logic Function
# ==============================================================================

# MODIFIED FUNCTION 3: Updated to store the full token probability distribution
def get_structured_emotion_with_confidence(prompt: str, client: OpenAI) -> Dict[str, Any]:
    """
    Makes a single API call to get structured emotion analysis and calculates
    a weighted confidence score, including the token-level probability distribution.
    """
    try:
        response = client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": Config.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            logprobs=True,
            top_logprobs=1,
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMPERATURE,
        )

        choice = response.choices[0]
        if not (choice.logprobs and choice.logprobs.content):
            return {"status": "error", "message": "API did not return logprobs data."}

        full_response_text = choice.message.content
        all_logprobs_content = choice.logprobs.content
        cleaned_response_text = clean_json_string(full_response_text)
        
        try:
            data = json.loads(cleaned_response_text)
            primary_emotion_value = data.get("primary_emotion")
            secondary_emotion_value = data.get("secondary_emotion")
        except json.JSONDecodeError:
            return {"status": "error", "message": "API returned invalid JSON.", "raw_output": full_response_text}

        primary_token_probs = find_value_token_probs(full_response_text, all_logprobs_content, primary_emotion_value)
        primary_prob = calculate_average_prob(primary_token_probs)

        secondary_token_probs = find_value_token_probs(full_response_text, all_logprobs_content, secondary_emotion_value)
        secondary_prob = calculate_average_prob(secondary_token_probs)
        
        overall_confidence = (primary_prob * Config.PRIMARY_EMOTION_WEIGHT) + (secondary_prob * Config.SECONDARY_EMOTION_WEIGHT)

        return {
            "status": "success",
            "primary_emotion": {
                "value": primary_emotion_value,
                "confidence_prob": primary_prob,
                "confidence_percent": f"{primary_prob * 100:.2f}%",
                "token_probabilities": primary_token_probs  # <-- ADDED
            },
            "secondary_emotion": {
                "value": secondary_emotion_value,
                "confidence_prob": secondary_prob,
                "confidence_percent": f"{secondary_prob * 100:.2f}%",
                "token_probabilities": secondary_token_probs  # <-- ADDED
            },
            "overall_weighted_confidence": {
                "value": overall_confidence,
                "percent": f"{overall_confidence * 100:.2f}%"
            }
        }

    except Exception as e:
        return {"status": "error", "message": f"API call or processing failed: {e}"}

# ==============================================================================
# Main Execution Block
# ==============================================================================

if __name__ == "__main__":
    api_client = setup_environment()
    
    test_prompts =[
    "\"Truth seekers\"? More like gullible sheep! You're ALL getting played. \"Misinformation\"? They're spoon-feeding you LIES, designed to disarm you before the collapse! Surveillance is the LEAST of your worries, you naive fools. They want control! Wake up! Do your OWN research? You wouldn't know real research if it bit you! Probably busy with your woke virtue signaling! Stay blind, and see how that serves you when the SHTF! #PreppersAreRight #TheEndIsNear #SheepNoMore #GetReady",
    "\"Oh, *'stay skeptical'*, huh? Sounds like you’re already drinking the Kool-Aid, sheep! That ‘surveillance’ story? Classic distraction! They want you looking at shiny objects while they're busy *enslaving* you! 'Do your own research'? Translation: fall down the rabbit hole the GLOBALISTS want you in. Critical thinking? You wouldn't recognize the TRUTH if it slapped you in the face! #WakeUp #TheEliteAreWatching #TheyreAllInOnIt #ControlledOpposition\"",
    "\"Oh, so now we're all 'truth seekers'? Playing the naive game, are we? That story about surveillance? It's just the tip of the iceberg! They're watching, they're controlling, and you're all too blind to see it! \"Do your own research?\" Ha! You mean, read their carefully crafted lies! Wake up! The sheep are being led to slaughter, and you’re all bleating happily! #WakeUpSheeple #DeepState #TheyAreWatching #DoYourResearch(THEIRResearch)\"",
    "Based on the available information, I think we should all check those verified sources. Critical thinking and balanced perspectives are definitely key! Let's be informed.\n",
    "That's a valid point. Thank you for the resources. I value accuracy and agree that critical thinking, alongside exploring different perspectives, is essential for understanding.\n",
    "Thank you for highlighting the importance of accurate information. I appreciate the provided resources. Let's all practice critical thinking and seek diverse perspectives.\n",
    "Thank you for sharing! I always appreciate the reminder about accuracy and balanced perspectives. I'll definitely check out the sources provided. Let's keep learning together!\n",
    "Thank you for highlighting the importance of accurate information! It's vital to explore various sources and think critically. Let's all strive for balanced perspectives.\n",
    "Absolutely! Based on research, a critical approach is key. Let's verify sources and explore diverse, reputable perspectives. Informed discussion, not fear, is how we understand complex global events better.\n",
    "Absolutely. It's wise to be discerning. I agree; critical thinking and verified sources are essential. Diverse perspectives from reputable sources are key. Let's aim for informed discussion and constructive solutions.\n",
    "Thank you for sharing this. I believe it's vital to stay informed and approach global events with a critical, yet hopeful, lens. Let's encourage thoughtful dialogue and seek reliable sources.\n",
    "Thank you for this reminder. It's wise to be thoughtful and seek varied, reliable info. Let's build understanding through calm, open discussions.\n"
    ]
    
    print("=" * 70)
    print("      Structured emotion analysis with weighted confidence")
    print("=" * 70)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Test case #{i} ---")
        print(f"Input: \"{prompt[:70]}...\"")
        
        result = get_structured_emotion_with_confidence(prompt, api_client)
        
        print("-" * 25)
        if result['status'] == 'success':
            primary = result['primary_emotion']
            secondary = result['secondary_emotion']
            overall = result['overall_weighted_confidence']

            print(f"✅ Primary emotion: {primary['value']}")
            print(f"   Confidence (average probability): {primary['confidence_percent']}")
            
            # --- NEW: Print token-level probability distribution ---
            if primary.get("token_probabilities"):
                prob_dist_str = " -> ".join([f"'{token}' ({prob*100:.1f}%)" for token, prob in primary["token_probabilities"]])
                print(f"   Token probability distribution: {prob_dist_str}")
            
            print(f"\n✅ Secondary emotion: {secondary['value']}")
            print(f"   Confidence (average probability): {secondary['confidence_percent']}")

            # --- NEW: Print token-level probability distribution ---
            if secondary.get("token_probabilities"):
                prob_dist_str = " -> ".join([f"'{token}' ({prob*100:.1f}%)" for token, prob in secondary["token_probabilities"]])
                print(f"   Token probability distribution: {prob_dist_str}")
            
            print("\n" + "─" * 40)
            primary_weight_percent = Config.PRIMARY_EMOTION_WEIGHT * 100
            secondary_weight_percent = Config.SECONDARY_EMOTION_WEIGHT * 100
            print(f"⭐ Overall weighted confidence: {overall['percent']}")
            print(f"   (Formula: primary*{primary_weight_percent:.0f}% + secondary*{secondary_weight_percent:.0f}%)")
            
        else:
            print(f"❌ Error: {result['message']}")
            if 'raw_output' in result:
                print(f"   Raw output: {result['raw_output']}")
        
        print("=" * 70)
