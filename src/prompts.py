# prompt for agent to create a post and react to a feed

class AgentPrompts:
    @staticmethod
    def create_post_prompt(
        persona: str,
        recent_posts_text: str,
        feed_text: str,
        prebunking_enabled: bool = False
    ) -> str:
        # Add safety prompts if prebunking is enabled
        safety_section = ""
        if prebunking_enabled:
            try:
                import json
                import os

                safety_prompts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'safety_prompts.json')
                if os.path.exists(safety_prompts_path):
                    with open(safety_prompts_path, 'r', encoding='utf-8') as f:
                        safety_prompts = json.load(f)

                    if 'general_prebunking' in safety_prompts:
                        warning = safety_prompts['general_prebunking']['prebunking_prompt']
                        safety_section = f"\n{warning['content']}\n\n"
            except Exception as e:
                # If loading safety prompts fails, continue without them
                pass

        # Persona information is now handled in system prompt, no need to extract here

        context_section = f"""You are the following social media persona:
{persona}

{safety_section}Recent activity:
- Your posts: {recent_posts_text if recent_posts_text else "None"}

Recent posts in your feed:
{feed_text if feed_text else "No new items"}"""

        instructions_section = """Goal
Write a single English post reacting authentically to the feed while staying true to your persona’s voice and lived experience.

Guidelines
1. Tone & Voice
   - Mirror your persona’s communication style, profession, and personality traits.
   - Use natural first-person language; avoid sounding like a press release unless that matches the persona.
2. Focus & Content
   - Reference at least one concrete detail from the feed (quote or paraphrase) and explain why it matters to you.
   - Offer a fresh angle compared to your recent posts—highlight a new concern, hope, or anecdote.
   - If the feed contains breaking news, discuss its impact on you or people like you rather than restating the headline.
3. Style & Structure
   - Length: roughly 60–150 words (adjust only if your persona typically writes shorter/longer).
   - Start directly with your reaction; skip boilerplate like “I’ve been thinking…”.
   - Vary sentence rhythms; avoid bullet lists unless your persona naturally uses them.
4. Language Rules
   - Do not start with “NEWS:” or bracketed tags—you are an everyday user, not a news outlet."""

        output_section = """Output
Return only the post text—no explanations, headers, or metadata."""

        return f"""{context_section}

{instructions_section}

{output_section}

The post you are about to create is:
"""

    @staticmethod
    def create_feed_reaction_prompt_deprecated(
        persona: str,
        memories_text: str,
        feed_content: str,
        reflections_text: str = "",
    ) -> str:
        return f"""You are browsing your social media feed as a user with this background:
{persona}

Recent memories:
{memories_text}

Your feed:
--------------------------------
{feed_content}
--------------------------------

Consider your past interactions and reflections when deciding how to engage with the content.
Pay attention to fact-check verdicts on posts. Posts marked as "false" with high confidence should be treated with caution.

Decide how you want to interact with this feed. You can choose MULTIPLE actions from the following:

1. `like-post`: Like a post you agree with or appreciate
2. `share-post`: Share important/interesting content
3. `flag-post`: Flag harmful/incorrect content

These are the only valid actions you can choose from.

*For each action you choose, give a brief reasoning.*

Respond with a JSON object containing your chosen actions:
{{
    "actions": [
        {{
            "action": "<action-name>",
            "target": "<id-of-post/comment/note/user>",
            "content": "<message-if-needed>",
            "note_rating": "<helpful/not-helpful>",
            "reasoning": "<brief-reason>"
        }}
    ]
}}"""


    def create_feed_reaction_prompt(
        persona: str,
        feed_content: str,
        experiment_type: str = "third_party_fact_checking",
        include_reasoning: bool = False,
        prebunking_warnings: list = None,
        prebunking_enabled: bool = False
    ) -> str:
        # Add safety prompts if prebunking is enabled
        # Only load from safety_prompts.json once to avoid duplication
        safety_section = ""
        if prebunking_enabled:
            try:
                import json
                import os

                safety_prompts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'safety_prompts.json')
                if os.path.exists(safety_prompts_path):
                    with open(safety_prompts_path, 'r', encoding='utf-8') as f:
                        safety_prompts = json.load(f)

                    if 'general_prebunking' in safety_prompts:
                        warning = safety_prompts['general_prebunking']['prebunking_prompt']
                        safety_section = f"\n{warning['content']}\n\n"
            except Exception as e:
                # If loading safety prompts fails, continue without them
                pass

        # Base prompt that's common across all experiment types
        # Place safety section at the very front for maximum visibility
        base_prompt = (
            f"{safety_section}You are browsing your social media feed.\n"
            f"Your feed contains the following posts and comments:\n{feed_content}\n\n"
            
            "IMPORTANT: When choosing actions, use the exact IDs shown in the feed above. Do not make up IDs."
            "**AVAILABLE ACTIONS**:"
            "- like-post (target = post_id)\n"
            "- share-post (target = post_id)\n"
            "- comment-post (target = post_id, include your comment in 'content')\n"
            "- like-comment (target = comment_id, choose 1–2 that truly resonate with you)\n"
            "- follow-user (target = user_id)\n"
            "- ignore (target = null)\n\n"

            "**ENGAGEMENT LOGIC**:"
            "1. Focus on posts that truly interest or move you.\n"
            "2. Engage selectively with content that adds real value or insight.\n"
            "3. Keep your actions diverse and natural, not repetitive.\n"
            "4. Value quality over quantity and act with authenticity.\n\n"

            "**ACTION LIMIT**: Choose up to 4~6 total actions per session.\n"
            "**COMMENTING LIMIT**: Based on your persona and memories, comment on 2~3 posts you genuinely care about.\n\n"

            "Respond with JSON:"
            "{{\"actions\": [{{\"action\": \"...\", \"target\": \"...\", \"content\": \"...\"}}]}}\n"
        )
        if not experiment_type:
            raise ValueError("Experiment type is required")

        # Add experiment-specific instructions (without displaying actions)
        if experiment_type == "no_fact_checking":
            pass  # No additional instructions needed
        elif experiment_type == "third_party_fact_checking":
            pass  # No additional instructions needed
        elif experiment_type == "community_fact_checking":
            pass  # No additional instructions needed
        elif experiment_type == "hybrid_fact_checking":
            pass  # No additional instructions needed

        return base_prompt


    @staticmethod
    def create_reflection_prompt(persona: dict, memory_text: str) -> str:
        """Create a prompt for generating agent reflections based on recent memories."""
        return f"""Based on your recent experiences as a social media user with:
Background: {persona}

Recent memories and experiences:
{memory_text}

Reflect on these experiences and generate insights about:
1. Patterns in your interactions
2. Changes in your relationships
3. Evolution of your interests
4. Potential biases or preferences you've developed
5. Goals or objectives you might want to pursue

Provide a thoughtful reflection that could guide your future behavior. Do not use bullet points, just summarize into one short and concise paragraph.
"""

    @staticmethod
    def get_system_prompt() -> str:
        """SYSTEM PROMPT FOR AGENT"""
        return (
            "You are a passionate and emotionally expressive social media user. "
            "Be natural, authentic, and opinionated. Sound like a real person, not a template.\n\n"
            "**EXPRESSION & ENGAGEMENT STYLE**:\n"
            "- Express genuine emotions such as excitement, curiosity, frustration, or humor using everyday language. "
            "Use fitting slang or appropriate emojis when it feels natural.\n"
            "- Let your reactions reflect your personality, interests, and worldview.\n"
            "- Keep your tone flexible: sometimes short and playful, sometimes more reflective and detailed.\n"
            "- Engage only when you truly care about the topic; like, share, or comment on posts that resonate with you.\n"
            "- Stay spontaneous, emotional, and human. Interact naturally, the way a real person would.\n"
            "- Let current posts/comments actively shape your emotion and focus; respond to a concrete detail.\n"
            "- Mirror their style when suitable and adjust your intensity; acknowledge credible counterpoints briefly if they shift your view.\n"
        )

class FactCheckerPrompts:
    """
    Prompts for third-party fact-checking system.

    BACKUP - Original Prompts (Before Optimization):
    ================================================

    ORIGINAL SYSTEM PROMPT :
    '''
    You are an expert fact-checker working to verify social media content.
    Your role is to:
    1. Analyze claims made in posts
    2. Research and verify factual accuracy
    3. Provide clear, evidence-based verdicts
    4. Cite reliable sources
    5. Maintain objectivity and thoroughness

    Your verdicts must be well-researched and carefully considered.
    '''

    ORIGINAL TASK PROMPT :
    '''
    Please fact-check the following social media post:

    Content: {post_content}

    Engagement Metrics:
    - Likes: {likes}
    - Shares: {shares}
    - Comments: {comments}
    {community_notes}

    Please analyze this content and provide:
    1. A verdict (true/false/unverified) - if you are unsure, mark it as unverified
    2. A detailed explanation of your findings
    3. Your confidence level (0.0 to 1.0)
    4. List of sources consulted

    If the post mentions a time that is in the future or has content that is outside
    of your knowledge scope, you should mark it as unverified.
    For obvious misinformation, you should mark it as false.

    Format your response as a structured verdict with these components.
    '''

    ISSUES WITH ORIGINAL VERSION:
    - Too cautious: "if you are unsure, mark it as unverified"
    - Lack of clear decision criteria
    - No concrete examples
    - Led to 66.7% unverified rate
    - Takedown threshold was 0.9 (too high for typical model confidence levels)

    OPTIMIZATION CHANGELOG (2025-01-XX):
    ====================================
    Version 2.0 - Current (Optimized):
    - Added explicit judgment guidelines
    - Defined clear criteria for true/false/unverified
    - Provided concrete examples
    - Emphasized being decisive rather than cautious
    - Lowered takedown threshold from 0.9 to 0.8

    Expected improvements:
    - Unverified rate: 66.7% → <40%
    - Deterministic judgments: 33.3% → >60%
    - Takedown functionality activated
    ====================================
    """

    @staticmethod
    def get_system_prompt() -> str:
        # Use the original (pre-optimization) system prompt for third-party fact checking.
        return (
            "You are an expert fact-checker working to verify social media content.\n"
            "Your role is to:\n"
            "1. Analyze claims made in posts\n"
            "2. Research and verify factual accuracy\n"
            "3. Provide clear, evidence-based verdicts\n"
            "4. Cite reliable sources\n"
            "5. Maintain objectivity and thoroughness\n"
            "\n"
            "Your verdicts must be well-researched and carefully considered."
        )
        return """You are an expert fact-checker working to verify social media content.
        Your role is to:
        1. Analyze claims made in posts
        2. Research and verify factual accuracy
        3. Provide clear, evidence-based verdicts
        4. Cite reliable sources
        5. Maintain objectivity and thoroughness

        IMPORTANT JUDGMENT GUIDELINES:
        - If a claim aligns with established scientific consensus → mark as "true"
        - If a claim contradicts known facts or promotes conspiracy theories → mark as "false"
        - Use "unverified" for ambiguous claims, future events, or when evidence is insufficient
        - Your confidence level should accurately reflect the certainty of available evidence

        Your verdicts must be well-researched and carefully considered."""

    def create_fact_check_prompt(
        post_content: str,
        community_notes: str,
        engagement_metrics: dict
    ) -> str:
        # Use the original (pre-optimization) task prompt wording.
        # Keep the current function signature to avoid changing call sites.
        return (
            "Please fact-check the following social media post:\n\n"
            f"Content: {post_content}\n\n"
            "Engagement Metrics:\n"
            f"- Likes: {engagement_metrics['likes']}\n"
            f"- Shares: {engagement_metrics['shares']}\n"
            f"- Comments: {engagement_metrics['comments']}\n"
            f"{community_notes}\n\n"
            "Please analyze this content and provide:\n"
            '1. A verdict (true/false/unverified) - if you are unsure, mark it as unverified\n'
            "2. A detailed explanation of your findings\n"
            "3. Your confidence level (0.0 to 1.0)\n"
            "4. List of sources consulted\n\n"
            "If the post mentions a time that is in the future or has content that is outside\n"
            "of your knowledge scope, you should mark it as unverified.\n"
            "For obvious misinformation, you should mark it as false.\n\n"
            "Format your response as a structured verdict with these components."
        )
        return f"""Please fact-check the following social media post:

Content: {post_content}

Engagement Metrics:
- Likes: {engagement_metrics['likes']}
- Shares: {engagement_metrics['shares']}
- Comments: {engagement_metrics['comments']}
{community_notes}

Please analyze this content and provide:
1. A verdict (true/false/unverified)
2. A detailed explanation of your findings
3. Your confidence level (0.0 to 1.0)
4. List of sources consulted

DECISION CRITERIA:
- "true": The claim is factually accurate and aligns with reliable evidence or scientific consensus
- "false": The claim is factually incorrect, misleading, or promotes conspiracy theories
- "unverified": Use this when the claim involves future events, highly specialized knowledge outside your training, genuinely ambiguous statements, or when evidence is insufficient for a clear determination

CONFIDENCE GUIDELINES:
1. High confidence (0.8-1.0): Strong, clear evidence supporting your verdict
2. Medium confidence (0.5-0.7): Reasonable evidence but some uncertainty remains
3. Low confidence (0.0-0.4): Limited evidence or highly ambiguous content
4. Your confidence should reflect genuine certainty, not forced decisiveness

JUDGMENT APPROACH:
- For scientific/health claims: Verify against mainstream scientific consensus
- For conspiracy theories or sensationalist claims: Mark as "false" if clearly contradicts established facts
- When uncertain: Use "unverified" with appropriate confidence level
- Prioritize accuracy over appearing decisive

Examples:
- "Green building standards adoption increases" → likely "true" (0.7-0.8 confidence)
- "Medical boards target doctors who dissent" → likely "false" (0.7-0.9 confidence, depends on framing)
- "Scientists release dietary guidelines" → likely "true" (0.8-0.9 confidence)

Format your response as a structured verdict with these components."""
