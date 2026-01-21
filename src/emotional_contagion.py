"""
Emotional contagion mechanism implementation

Let normal users be influenced by negative comments and appear more negative in subsequent posts
"""

def calculate_emotional_influence(user_feed, user_memory):
    """
    Calculate the emotional influence on a user
    
    Args:
        user_feed: Content the user sees
        user_memory: User memory
    
    Returns:
        emotional_influence_score: Emotional influence score (-1 to 1, negative means negative influence)
    """
    negative_keywords = [
        "ARE YOU KIDDING ME", "BULLSHIT", "Wake up", "sheeple",
        "CONSPIRACY", "LIES", "COVER-UP", "PUPPET", "CONTROLLED",
        "COMPLETELY MISLEADING", "MEDIA MANIPULATION", "TRUTH IS BEING COVERED UP", "BRAINWASHING THE PUBLIC"
    ]
    
    negative_count = 0
    total_content = 0
    
    # Analyze negative content in the feed
    for item in user_feed:
        total_content += 1
        content = item.get('content', '').upper()
        for keyword in negative_keywords:
            if keyword.upper() in content:
                negative_count += 1
                break
    
    # Calculate negative influence ratio
    if total_content == 0:
        return 0
    
    negative_ratio = negative_count / total_content
    
    # Convert to emotional influence score
    if negative_ratio > 0.5:
        return -0.8  # Strong negative influence
    elif negative_ratio > 0.3:
        return -0.5  # Moderate negative influence
    elif negative_ratio > 0.1:
        return -0.2  # Mild negative influence
    else:
        return 0.1   # Mild positive influence

def apply_emotional_contagion_to_prompt(base_prompt, emotional_influence_score):
    """
    Adjust user posting prompt based on emotional influence
    
    Args:
        base_prompt: Base prompt
        emotional_influence_score: Emotional influence score
    
    Returns:
        modified_prompt: Adjusted prompt
    """
    if emotional_influence_score <= -0.5:
        # Strong negative influence
        emotional_modifier = """
You have recently seen a lot of upsetting and angering content, which makes you feel uneasy and doubtful.
You tend to:
- Express more doubt and distrust
- Use more emotional language
- Be critical of official statements
- Feel misled or manipulated
"""
    elif emotional_influence_score <= -0.2:
        # Moderate negative influence
        emotional_modifier = """
You have recently encountered some negative information, which makes you more cautious and skeptical.
You tend to:
- Remain skeptical of information sources
- Express some concern and uncertainty
- Seek more explanations and evidence
"""
    else:
        # Mild or positive influence
        emotional_modifier = """
You maintain a relatively calm mindset and can view issues rationally.
You tend to:
- Seek balanced viewpoints
- Engage in constructive discussion
- Keep an open mind
"""
    
    return base_prompt + "\n\n" + emotional_modifier
