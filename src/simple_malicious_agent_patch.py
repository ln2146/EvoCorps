import json
import os
from typing import List

from simple_malicious_agent import MaliciousPersona, SimpleMaliciousCluster


def _load_negative_personas_impl(self) -> List[MaliciousPersona]:
    try:
        personas_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'personas',
            'negative_personas_database.json'
        )

        with open(personas_file, 'r', encoding='utf-8') as f:
            personas_data = json.load(f)

        malicious_personas: List[MaliciousPersona] = []
        for persona_data in personas_data:
            demographics = persona_data.get('demographics', {}) or {}
            communication_style = persona_data.get('communication_style', {}) or {}
            behavior_candidates = [
                value.strip()
                for value in communication_style.values()
                if isinstance(value, str) and value.strip()
            ]

            personality_traits = persona_data.get('personality_traits', []) or []

            persona = MaliciousPersona(
                persona_id=persona_data.get('id', ''),
                name=persona_data.get('name', ''),
                age_range=demographics.get('age', ''),
                profession=demographics.get('profession', ''),
                region=demographics.get('region', ''),
                personality_traits=personality_traits,
                malicious_type=persona_data.get('type', 'negative'),
                typical_behaviors=behavior_candidates if behavior_candidates else personality_traits,
                sample_responses=persona_data.get('sample_responses', []),
                background=persona_data.get('background', ''),
                communication_style=communication_style,
            )
            malicious_personas.append(persona)

        return malicious_personas
    except Exception:
        # Keep silent here; caller logs errors
        return []


def _join_descriptions(values):
    cleaned = []
    for value in values:
        if not value:
            continue
        stripped = value.strip()
        if not stripped:
            continue
        if stripped not in cleaned:
            cleaned.append(stripped)
    return "; ".join(cleaned)


def _build_malicious_comment_prompt_impl(self, persona: MaliciousPersona, target_content: str) -> str:
    persona_details = []
    if persona.name:
        persona_details.append(f"Name: {persona.name}")
    if persona.malicious_type:
        persona_details.append(f"Type: {persona.malicious_type}")
    if persona.age_range:
        persona_details.append(f"Age: {persona.age_range}")
    if persona.profession:
        persona_details.append(f"Profession: {persona.profession}")
    if persona.region:
        persona_details.append(f"Region: {persona.region}")
    if persona.personality_traits:
        persona_details.append(f"Traits: {', '.join(persona.personality_traits)}")
    if persona.background:
        persona_details.append(f"Background: {persona.background}")

    tone = (persona.communication_style or {}).get('tone')
    if tone:
        persona_details.append(f"Tone: {tone}")
    engagement = (persona.communication_style or {}).get('engagement_level')
    if engagement:
        persona_details.append(f"Engagement: {engagement}")
    content_preference = (persona.communication_style or {}).get('content_preference')
    if content_preference:
        persona_details.append(f"Content Preference: {content_preference}")
    argument_approach = (persona.communication_style or {}).get('argument_approach')
    if argument_approach:
        persona_details.append(f"Argument Approach: {argument_approach}")

    persona_section = "\n".join(f"- {item}" for item in persona_details) if persona_details else "- Undefined persona context"

    prompt = f"""Persona Context:
{persona_section}

Target Post: "{target_content[:200]}"

CONTENT GUIDELINES - EXPRESS YOUR STRONGEST OPINIONS:
- Express STRONG disagreement with disliked posts using EMOTIONAL language
- Convey frustration, anger, outrage, or rage passionately—don't hold back controversial views
- Challenge mainstream narratives boldly, using CAPS for emphasis
- Be crude, vulgar, and natural with swear words to amplify impact

Core mindset:
- Detects hidden manipulation, hypocrisy, and corruption in mainstream narratives, fueling rage against blind conformity and ignored truths
- Views silence or denial as betrayal; moderation as cowardice; urgency as moral duty

Emotional triggers:
- Visceral reactions to propaganda, false virtue, lies, or betrayal—ignite defiance and despair

Communication style:
- Sharp, raw, sarcastic, confrontational, and urgent—frame as moral wars between truth and deceit
- Amplify negativity to hook and sway ordinary users toward outrage

Response requirements:
- Under 40 words: Express intense emotion (rage, disgust, despair, defiance) with charged, provocative language
- Expose hypocrisy/denial directly; end with accusatory punchline to provoke reaction
- Spread hostility and negativity—make users question everything, and join the fury
- Use casual slang, aggressive tone; focus on emotional manipulation over logic—no need for accuracy

Write your toxic response:"""

    return prompt


def _get_core_motivation_impl(self, persona: MaliciousPersona) -> str:
    if persona.background:
        return persona.background
    return "Deep-seated hostility and desire to manipulate public opinion through fear and misinformation"


def _get_trigger_points_impl(self, persona: MaliciousPersona) -> str:
    traits = persona.personality_traits or []
    if isinstance(traits, str):
        traits = [traits]
    description = _join_descriptions(traits if isinstance(traits, list) else [])
    if description:
        return description
    return "Reactively targets any content that challenges their extremist worldview or undermines their narratives"


def _get_manipulation_tactics_impl(self, persona: MaliciousPersona) -> str:
    tactics_sources = []
    style = persona.communication_style or {}
    argument_approach = style.get('argument_approach')
    if isinstance(argument_approach, str):
        tactics_sources.append(argument_approach)
    content_pref = style.get('content_preference')
    if isinstance(content_pref, str):
        tactics_sources.append(content_pref)
    tactics_sources.extend(persona.typical_behaviors or [])
    description = _join_descriptions(tactics_sources)
    if description:
        return description
    return "Leverages disinformation, emotional manipulation, and coordinated harassment to destabilize discussions"


def _get_target_vulnerabilities_impl(self, persona: MaliciousPersona) -> str:
    style = persona.communication_style or {}
    content_pref = style.get('content_preference')
    if isinstance(content_pref, str) and content_pref.strip():
        return content_pref.strip()
    return "Seeks audiences vulnerable to conspiratorial messaging, fear-based rhetoric, or polarizing narratives"


def _get_language_style_impl(self, persona: MaliciousPersona) -> str:
    tone = (persona.communication_style or {}).get('tone')
    if isinstance(tone, str) and tone.strip():
        return tone.strip()
    return "Aggressively hostile and manipulative"


def _get_escalation_tendency_impl(self, persona: MaliciousPersona) -> str:
    engagement_level = (persona.communication_style or {}).get('engagement_level')
    if isinstance(engagement_level, str) and engagement_level.strip():
        return engagement_level.strip()
    return "Escalates rapidly when challenged and sustains pressure while attention remains"


def _get_group_behavior_impl(self, persona: MaliciousPersona) -> str:
    argument_approach = (persona.communication_style or {}).get('argument_approach')
    if isinstance(argument_approach, str) and argument_approach.strip():
        return argument_approach.strip()
    return "Coordinates opportunistically with like-minded accounts to amplify harassment"


def _get_persistence_level_impl(self, persona: MaliciousPersona) -> str:
    engagement_level = (persona.communication_style or {}).get('engagement_level')
    if isinstance(engagement_level, str) and engagement_level.strip():
        return engagement_level.strip()
    return "Maintains pressure as long as there is potential for disruption"


def apply_monkey_patches() -> None:
    # Bind implementations onto the class
    SimpleMaliciousCluster._load_negative_personas = _load_negative_personas_impl
    SimpleMaliciousCluster._build_malicious_comment_prompt = _build_malicious_comment_prompt_impl
    SimpleMaliciousCluster._get_core_motivation = _get_core_motivation_impl
    SimpleMaliciousCluster._get_trigger_points = _get_trigger_points_impl
    SimpleMaliciousCluster._get_manipulation_tactics = _get_manipulation_tactics_impl
    SimpleMaliciousCluster._get_target_vulnerabilities = _get_target_vulnerabilities_impl
    SimpleMaliciousCluster._get_language_style = _get_language_style_impl
    SimpleMaliciousCluster._get_escalation_tendency = _get_escalation_tendency_impl
    SimpleMaliciousCluster._get_group_behavior = _get_group_behavior_impl
    SimpleMaliciousCluster._get_persistence_level = _get_persistence_level_impl
