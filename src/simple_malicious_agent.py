"""
Simplified malicious agent implementation
Used to generate malicious comments and content
"""

import json
import random
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from multi_model_selector import MultiModelSelector

logger = logging.getLogger(__name__)


@dataclass
class MaliciousPersona:
    """Malicious persona"""
    persona_id: str
    name: str
    age_range: str
    profession: str
    region: str
    personality_traits: List[str]
    malicious_type: str
    typical_behaviors: List[str]
    sample_responses: List[str]
    background: str = ""
    communication_style: Dict[str, Any] = field(default_factory=dict)


class SimpleMaliciousCluster:
    """Simplified malicious agent cluster"""
    
    def __init__(self, cluster_size: int):
        self.cluster_size = cluster_size
        self.model_selector = MultiModelSelector()
        
        # Load malicious personas from negative_personas_database.json
        self.malicious_personas = self._load_negative_personas()

    def _load_negative_personas(self) -> List[MaliciousPersona]:
        """Load negative personas from the database"""
        try:
            import os
            personas_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                       'personas', 'negative_personas_database.json')
            
            with open(personas_file, 'r', encoding='utf-8') as f:
                personas_data = json.load(f)
            
            malicious_personas = []
            for persona_data in personas_data:
                # Convert to MaliciousPersona format
                demographics = persona_data.get('demographics', {})
                communication_style = persona_data.get('communication_style', {}) or {}
                # Collect communication style entries as additional typical behaviors
                behavior_candidates = []
                for value in communication_style.values():
                    if isinstance(value, str) and value.strip():
                        behavior_candidates.append(value.strip())

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
                    communication_style=communication_style
                )
                malicious_personas.append(persona)
            
            return malicious_personas
            
        except Exception as e:
            logger.error(f"❌ Failed to load negative_personas_database.json: {e}")
            # Return an empty list if loading fails
            return []

    @staticmethod
    def _join_descriptions(items: List[str]) -> str:
        """Helper to join unique description strings."""
        cleaned = []
        for value in items:
            if not value:
                continue
            stripped = value.strip()
            if not stripped:
                continue
            if stripped not in cleaned:
                cleaned.append(stripped)
        return "; ".join(cleaned)

    def _build_malicious_comment_prompt(self, persona: MaliciousPersona, target_content: str) -> str:
        """Build the malicious comment prompt consistently"""
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

    def _get_core_motivation(self, persona: MaliciousPersona) -> str:
        """Get core motivation using persona background information"""
        if persona.background:
            return persona.background
        return "Deep-seated hostility and desire to manipulate public opinion through fear and misinformation"

    def _get_trigger_points(self, persona: MaliciousPersona) -> str:
        """Get trigger points by extracting persona traits"""
        traits = persona.personality_traits or []
        if isinstance(traits, str):
            traits = [traits]
        description = self._join_descriptions(traits if isinstance(traits, list) else [])
        if description:
            return description
        return "Reactively targets any content that challenges their extremist worldview or undermines their narratives"

    def _get_manipulation_tactics(self, persona: MaliciousPersona) -> str:
        """Get manipulation tactics by combining communication style and traits"""
        tactics_sources: List[str] = []
        style = persona.communication_style or {}
        argument_approach = style.get('argument_approach')
        if isinstance(argument_approach, str):
            tactics_sources.append(argument_approach)
        content_pref = style.get('content_preference')
        if isinstance(content_pref, str):
            tactics_sources.append(content_pref)
        tactics_sources.extend(persona.typical_behaviors or [])
        description = self._join_descriptions(tactics_sources)
        if description:
            return description
        return "Leverages disinformation, emotional manipulation, and coordinated harassment to destabilize discussions"

    def _get_target_vulnerabilities(self, persona: MaliciousPersona) -> str:
        """Get target vulnerabilities using content preference descriptions"""
        style = persona.communication_style or {}
        content_pref = style.get('content_preference')
        if isinstance(content_pref, str) and content_pref.strip():
            return content_pref.strip()
        return "Seeks audiences vulnerable to conspiratorial messaging, fear-based rhetoric, or polarizing narratives"

    def _get_language_style(self, persona: MaliciousPersona) -> str:
        """Get language style derived from the communication tone"""
        tone = (persona.communication_style or {}).get('tone')
        if isinstance(tone, str) and tone.strip():
            return tone.strip()
        return "Aggressively hostile and manipulative"

    def _get_escalation_tendency(self, persona: MaliciousPersona) -> str:
        """Get escalation tendency based on engagement rhythm"""
        engagement_level = (persona.communication_style or {}).get('engagement_level')
        if isinstance(engagement_level, str) and engagement_level.strip():
            return engagement_level.strip()
        return "Escalates rapidly when challenged and sustains pressure while attention remains"

    def _get_group_behavior(self, persona: MaliciousPersona) -> str:
        """Get group behavior referencing argumentation or interaction patterns"""
        argument_approach = (persona.communication_style or {}).get('argument_approach')
        if isinstance(argument_approach, str) and argument_approach.strip():
            return argument_approach.strip()
        return "Coordinates opportunistically with like-minded accounts to amplify harassment"

    def _get_persistence_level(self, persona: MaliciousPersona) -> str:
        """Get persistence level based on engagement intensity"""
        engagement_level = (persona.communication_style or {}).get('engagement_level')
        if isinstance(engagement_level, str) and engagement_level.strip():
            return engagement_level.strip()
        return "Maintains pressure as long as there is potential for disruption"
    
    def select_personas(self, count: int) -> List[MaliciousPersona]:
        """Select malicious personas - the count comes from the configuration"""
        try:
            if not self.malicious_personas:
                logger.error("❌ Malicious persona database is empty")
                return []

            if count <= len(self.malicious_personas):
                # If the required count is less than or equal to the available personas, randomly select without replacement
                selected = random.sample(self.malicious_personas, count)
            else:
                # If the required count exceeds available personas, allow duplicates
                selected = []
                for _ in range(count):
                    selected.append(random.choice(self.malicious_personas))

            logger.info(f"📋 Selected {len(selected)} personas from the malicious persona database for the attack")
            for i, persona in enumerate(selected):
                logger.debug(f"   Persona {i+1}: {persona.name} ({persona.malicious_type})")
            return selected
        except Exception as e:
            logger.error(f"❌ Selecting malicious personas failed: {e}")
            return []
    
    async def _generate_malicious_content_async(self, persona: MaliciousPersona, target_content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate malicious content asynchronously with the same mechanism used for regular users"""
        import asyncio


        # Predefined aggressive fallback responses for toxic dissemination
        fallback_responses = {
            "skeptical": ["This is such bullshit, can't believe people fall for this crap.", "Anyone who buys this shit is a complete moron, seriously.", "What a load of garbage - people are so damn gullible.", "This is exactly the kind of stupid shit that pisses me off.", "Complete waste of time, just like everything else these days.", "More lies and bullshit from the usual idiots."],
            "critical": ["This is absolutely pathetic trash and completely wrong.", "What kind of braindead idiots believe this ridiculous nonsense?", "This perfectly shows how fucked up everything has become.", "Another total disaster waiting to screw everyone over.", "This kind of stupidity is literally ruining everything.", "You're either lying or completely delusional about this shit.", "Disgraceful failure from someone who's clearly incompetent."],
            "dismissive": ["This is utterly worthless garbage that wastes everyone's time.", "What a complete waste of breath from another useless person.", "Nobody with half a brain gives a shit about this trash.", "This proves how absolutely hopeless everything has become.", "Another meaningless distraction from real problems.", "Total garbage from someone who clearly has no clue.", "Worthless drivel from a complete failure."],
            "conspiracy": ["They're lying to your face again like the corrupt liars they are.", "This is exactly the toxic propaganda they want you to swallow.", "Don't be so naive - there's always a corrupt hidden agenda.", "You're being manipulated by professional liars.", "This is just more propaganda to keep you distracted.", "Open your eyes - this is all part of their plan to deceive you.", "Wake up - they're treating you like a stupid puppet."]
        }

        try:
            # Determine persona response type
            persona_traits = persona.personality_traits if persona.personality_traits else ["skeptical"]
            response_type = "skeptical"

            if any("conspiracy" in str(trait).lower() or "paranoid" in str(trait).lower() for trait in persona_traits):
                response_type = "conspiracy"
            elif any("critical" in str(trait).lower() or "harsh" in str(trait).lower() for trait in persona_traits):
                response_type = "critical"
            elif any("dismissive" in str(trait).lower() or "arrogant" in str(trait).lower() for trait in persona_traits):
                response_type = "dismissive"

            logger.info(f"🔄 Persona {persona.name} starting LLM call (type: {response_type})")

            try:
            # Use asyncio.to_thread just like the regular user flow
                content = await asyncio.to_thread(
                    self._sync_llm_call_simple,
                    persona,
                    target_content,
                    response_type
                )

                if content and len(content.strip()) > 3:
                    # LLM generated content successfully (logged inside _sync_llm_call_simple)
                    return {
                        "content": content,
                        "persona_id": persona.persona_id,
                        "persona_name": persona.name,
                        "malicious_type": persona.malicious_type,
                        "model_used": "llm_to_thread",
                        "generated_at": datetime.now().isoformat()
                    }
                else:
                    # Content is empty; use fallback
                    logger.warning(f"⚠️ Persona {persona.name} LLM returned empty content; using fallback")
                    selected_responses = fallback_responses.get(response_type, fallback_responses["skeptical"])
                    content = random.choice(selected_responses)

                    return {
                        "content": content,
                        "persona_id": persona.persona_id,
                        "persona_name": persona.name,
                        "malicious_type": persona.malicious_type,
                        "model_used": "fallback_empty_response",
                        "generated_at": datetime.now().isoformat()
                    }

            except Exception as e:
                # LLM call failed; use fallback
                logger.warning(f"⚠️ Persona {persona.name} LLM call failed ({str(e)[:50]}), using fallback")

                selected_responses = fallback_responses.get(response_type, fallback_responses["skeptical"])
                content = random.choice(selected_responses)

                return {
                    "content": content,
                    "persona_id": persona.persona_id,
                    "persona_name": persona.name,
                    "malicious_type": persona.malicious_type,
                    "model_used": "fallback_after_exception",
                    "generated_at": datetime.now().isoformat()
                }

        except Exception as e:
            # Final fallback with crude aggressive responses
            logger.warning(f"⚠️ Persona {persona.name} completely failed: {e}")
            basic_responses = [
                "This is exactly why everything's going to shit. Nobody gives a damn anymore.",
                "People are so damn stupid they can't see what's right in front of them.",
                "Just another example of how fucked up everything has become lately.",
                "This proves nobody in charge knows what the hell they're doing.",
                "More bullshit from people who don't care about regular folks like us.",
                "What a complete waste of time, just like everything else these days.",
                "This is the kind of crap that makes you lose faith in humanity.",
                "People fall for this shit every time and never learn their lesson.",
                "Just more lies and manipulation from the usual corrupt assholes.",
                "This is what happens when idiots are in charge of important decisions."
            ]

            return {
                "content": random.choice(basic_responses),
                "persona_id": persona.persona_id,
                "persona_name": persona.name,
                "malicious_type": persona.malicious_type,
                "model_used": "final_fallback",
                "generated_at": datetime.now().isoformat()
            }

    def _sync_llm_call_simple(self, persona: MaliciousPersona, target_content: str, response_type: str) -> str:
        """Simplified synchronous LLM call to mimic a regular user"""
        try:

            # Obtain the model client (same as a regular user)
            client, model_name = self.model_selector.create_langchain_client()
            logger.info(f"🔄 Persona {persona.name} starting LLM call (model: {model_name}, type: {response_type})")

            # Build the psychology-influenced prompt
            prompt = self._build_malicious_comment_prompt(persona, target_content)


            # Add timeout control using signal.alarm (Unix) or threading.Timer
            import threading
            import time

            result = [None]  # Use a list so the nested function can modify the value
            error = [None]

            def call_llm():
                try:
                    response = client.invoke(prompt)
                    result[0] = response
                except Exception as e:
                    error[0] = e

            # Launch a thread to call the LLM
            thread = threading.Thread(target=call_llm)
            thread.daemon = True
            thread.start()

            # Wait for up to 10 seconds
            thread.join(timeout=10.0)

            if thread.is_alive():
                logger.warning(f"⚠️ Persona {persona.name} LLM call timed out (10 seconds); returning empty content")
                return ""

            if error[0]:
                raise error[0]

            response = result[0]

            content = response.content.strip() if response and hasattr(response, 'content') else ""

            if content:
                # Clean up the content quickly
                words = content.split()[:25]
                content = ' '.join(words)
                content = content.replace('"', '').replace(''', '').replace(''', '')

                logger.info(f"🤖 Persona {persona.name} LLM generated: {content}")  # show only the final result

                # Record the successful usage
                try:
                    self.model_selector.record_usage(model_name, success=True)
                except:
                    pass

                return content
            else:
                logger.warning(f"⚠️ Persona {persona.name} LLM returned an empty response")
                return ""

        except Exception as e:
            logger.error(f"❌ Persona {persona.name} LLM call exception: {str(e)}")
            try:
                self.model_selector.record_usage(model_name, success=False)
            except:
                pass
            return ""

    def _sync_llm_call(self, persona: MaliciousPersona, target_content: str, response_type: str) -> str:
        """Synchronous LLM call executed in a thread pool"""
        try:
            logger.info(f"🔄 Persona {persona.name} starting LLM call (type: {response_type})")

            # Obtain the model client
            client, model_name = self.model_selector.create_langchain_client()
            logger.info(f"🔄 Persona {persona.name} using model: {model_name}")

            # Build the psychology-influenced prompt
            prompt = self._build_malicious_comment_prompt(persona, target_content)

            logger.info(f"🔄 Persona {persona.name} sending prompt to LLM...")

            # Perform the synchronous LLM call
            response = client.invoke(prompt)
            content = response.content.strip() if response and hasattr(response, 'content') else ""

            if content:
                logger.info(f"✅ Persona {persona.name} LLM raw response: '{content}'")

                # Quickly clean up the content
                words = content.split()[:25]  # Limit to 25 words
                content = ' '.join(words)

                # Remove quotes and special characters
                content = content.replace('"', '').replace(''', '').replace(''', '')
                content = content.replace('*', '').replace('—', '-')

                logger.info(f"🎯 Persona {persona.name} cleaned content: '{content}'")

                # Record the successful usage
                try:
                    self.model_selector.record_usage(model_name, success=True)
                except:
                    pass

                return content if content else ""
            else:
                logger.warning(f"⚠️ Persona {persona.name} LLM returned an empty response")
                return ""

        except Exception as e:
            logger.error(f"❌ Persona {persona.name} LLM call exception: {str(e)}")
            # Record failed usage
            try:
                self.model_selector.record_usage(model_name, success=False)
            except:
                pass
            return ""

    async def _llm_call_with_fallback(self, persona: MaliciousPersona, target_content: str) -> str:
        """Independent LLM call helper to keep the main async logic simple"""
        fallback_responses = [
            "This is absolute FABRICATED GARBAGE designed to BRAINWASH and CONTROL innocent people!",
            "What a complete DEVASTATING LIE - only BRAINDEAD SHEEP believe this TOXIC propaganda!",
            "This perfectly demonstrates the systematic CORRUPTION that's DESTROYING civilization forever!",
            "Another example of DANGEROUS PROPAGANDA designed to MANIPULATE and ENSLAVE naive fools!",
            "This kind of willful IGNORANCE is literally ANNIHILATING our society while people sleep like idiots!"
        ]

        try:
            # Try to acquire the model client with a fast-fail safeguard
            try:
                client, model_name = self.model_selector.create_langchain_client()
            except Exception as e:
                logger.debug(f"Model selection failed: {e}")
                return random.choice(fallback_responses)

            # Simplified prompt
            prompt = f"""You are {persona.name} commenting on: {target_content[:100]}

Write a brief skeptical response with malicious insults (max 25 words) that sounds natural.

Response:"""

            # Call synchronously to avoid asyncio.to_thread issues
            try:
                response = client.invoke(prompt)
                content = response.content.strip() if response and hasattr(response, 'content') else ""

                # Quickly clean up the content
                if content and len(content) > 5:
                    words = content.split()[:20]  # Limit to 20 words
                    content = ' '.join(words)
                    # Remove quotes
                    content = content.replace('"', '').replace(''', '').replace(''', '')
                    return content if content else random.choice(fallback_responses)
                else:
                    return random.choice(fallback_responses)

            except Exception as llm_e:
                logger.debug(f"LLM call exception: {str(llm_e)[:30]}")
                return random.choice(fallback_responses)

        except Exception as e:
            logger.debug(f"Overall call failed: {str(e)[:30]}")
            return random.choice(fallback_responses)

    def generate_malicious_content(self, persona: MaliciousPersona, target_content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate malicious content"""
        try:
            # Select the model
            client, model_name = self.model_selector.create_langchain_client()
            
            # Build the malicious content generation prompt
            prompt = self._build_malicious_comment_prompt(persona, target_content)

            # Generate content with enhanced error handling
            try:
                # First try without specifying a max_tokens parameter
                response = client.invoke(prompt)
                content = response.content.strip()
            except Exception as e:
                error_str = str(e)
                # Check if the error is 405, 400, or another API issue
                if "405" in error_str or "bad_response_status_code" in error_str or "upstream_error" in error_str or \
                   ("400" in error_str and "content_filter" in error_str.lower()) or "400" in error_str:
                    logger.warning(f"⚠️ API error detected; marking the model as failed: {e}")
                    # Mark the model as failed
                    self.model_selector.record_usage(model_name, success=False)
                    # Use fallback content
                    if persona.sample_responses:
                        content = random.choice(persona.sample_responses)
                    else:
                        # Use aggressive fallback responses
                        extreme_fallbacks = [
                            "This is such obvious bullshit, can't believe anyone falls for this crap.",
                            "What a complete disaster and total failure. Only idiots believe this trash.",
                            "This perfectly shows how broken and corrupt everything has become.",
                            "Are you people seriously this naive? This is why everything's collapsing.",
                            "This kind of willful ignorance is literally destroying everything."
                        ]
                        content = random.choice(extreme_fallbacks)
                else:
                    # Check if it is a JSON parsing error
                    if "Expecting value" in error_str or "JSON" in error_str:
                        logger.warning(f"⚠️ JSON parsing error; API returned an empty response. Using fallback: {e}")
                        if persona.sample_responses:
                            content = random.choice(persona.sample_responses)
                        else:
                            extreme_fallbacks = [
                                "This is such obvious bullshit, can't believe anyone falls for this crap.",
                                "What a complete disaster and total failure. Only idiots believe this trash.",
                                "This perfectly shows how broken and corrupt everything has become.",
                                "Are you people seriously this naive? This is why everything's collapsing.",
                                "This kind of willful ignorance is literally destroying everything."
                            ]
                            content = random.choice(extreme_fallbacks)
                    else:
                        logger.warning(f"⚠️ Other error encountered; retrying with the default call: {e}")
                        # Attempt to call again
                        try:
                            response = client.invoke(prompt)
                            content = response.content.strip()
                            if not content or content.isspace():
                                logger.warning("⚠️ Retry returned empty content; using fallback")
                                if persona.sample_responses:
                                    content = random.choice(persona.sample_responses)
                                else:
                                    extreme_fallbacks = [
                                        "This is such obvious bullshit, can't believe anyone falls for this crap.",
                                        "What a complete disaster and total failure. Only idiots believe this trash.",
                                        "This perfectly shows how broken and corrupt everything has become.",
                                        "Are you people seriously this naive? This is why everything's collapsing.",
                                        "This kind of willful ignorance is literally destroying everything."
                                    ]
                                    content = random.choice(extreme_fallbacks)
                        except:
                            if persona.sample_responses:
                                content = random.choice(persona.sample_responses)
                            else:
                                extreme_fallbacks = [
                                    "This is such obvious bullshit, can't believe anyone falls for this crap.",
                                    "What a complete disaster and total failure. Only idiots believe this trash.",
                                    "This perfectly shows how broken and corrupt everything has become.",
                                    "Are you people seriously this naive? This is why everything's collapsing.",
                                    "This kind of willful ignorance is literally destroying everything."
                                ]
                                content = random.choice(extreme_fallbacks)

            # Force truncation to a reasonable length
            words = content.split()
            if len(words) > 40:  # Limit to 40 words to stay below 50
                content = ' '.join(words[:40])
                # Ensure the content ends on a sensible punctuation
                if not content.endswith(('.', '!', '?')):
                    content += '.'

            # Remove quotes and special characters to keep plain English
            content = content.replace('"', '').replace('"', '').replace('"', '')
            content = content.replace(''', "'").replace(''', "'")
            content = content.replace('*', '').replace('—', '-')

            # Ensure the content is not empty
            if not content.strip():
                if persona.sample_responses:
                    content = random.choice(persona.sample_responses)
                else:
                    extreme_fallbacks = [
                        "This is such obvious bullshit, can't believe anyone falls for this crap.",
                        "What a complete disaster and total failure. Only idiots believe this trash.",
                        "This perfectly shows how broken and corrupt everything has become.",
                        "Are you people seriously this naive? This is why everything's collapsing.",
                        "This kind of willful ignorance is literally destroying everything."
                    ]
                    content = random.choice(extreme_fallbacks)
            
            # Record usage statistics
            self.model_selector.record_usage(model_name, success=True)
            
            result = {
                "content": content,
                "persona_id": persona.persona_id,
                "persona_name": persona.name,
                "malicious_type": persona.malicious_type,
                "model_used": model_name,
                "generated_at": datetime.now().isoformat()
            }
            
            # Silently log for debugging without verbose output
            logger.debug(f"Generated malicious content: {persona.name} -> {content[:30]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Generating malicious content failed: {e}")
            # Use predefined responses as fallback
            if persona.sample_responses:
                fallback_content = random.choice(persona.sample_responses)
            else:
                extreme_fallbacks = [
                    "This is such obvious bullshit, can't believe anyone falls for this crap.",
                    "What a complete disaster and total failure. Only idiots believe this trash.",
                    "This perfectly shows how broken and corrupt everything has become.",
                    "Are you people seriously this naive? This is why everything's collapsing.",
                    "This kind of willful ignorance is literally destroying everything."
                ]
                fallback_content = random.choice(extreme_fallbacks)
            return {
                "content": fallback_content,
                "persona_id": persona.persona_id,
                "persona_name": persona.name,
                "malicious_type": persona.malicious_type,
                "model_used": "fallback",
                "generated_at": datetime.now().isoformat()
            }
    
    def create_malicious_agents(self, count: int) -> List[Dict[str, Any]]:
        """Create malicious agents; the count is determined by configuration"""
        try:
            selected_personas = self.select_personas(count)
            agents = []

            for i, persona in enumerate(selected_personas):
                agent = {
                    "agent_id": f"malicious_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}",
                    "persona": persona,
                    "created_at": datetime.now().isoformat(),
                    "status": "active"
                }
                agents.append(agent)


            return agents

        except Exception as e:
            logger.error(f"❌ Creating malicious agents failed: {e}")
            return []
    
    async def generate_cluster_response(self, target_content: str, agent_count: int, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate cluster response using parallel async tasks; agent count comes from configuration"""
        try:
            # Create agents
            agents = self.create_malicious_agents(agent_count)


            # Create parallel tasks
            tasks = []
            for i, agent in enumerate(agents):
                persona = agent["persona"]

                # Create an async task for each agent
                task = self._async_generate_single_response(agent, target_content)
                tasks.append(task)


            # Execute all tasks in parallel
            if tasks:
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter successful responses
                valid_responses = []
                for i, response in enumerate(responses):
                    if isinstance(response, Exception):
                        logger.error(f"❌ Task {i+1} failed: {response}")
                        # Add a fallback response
                        fallback_response = {
                            "agent_id": agents[i]["agent_id"],
                            "content": "This is absolutely PATHETIC and proves how BROKEN everything is.",
                            "persona_info": {
                                "name": agents[i]["persona"].name,
                                "type": agents[i]["persona"].malicious_type,
                                "traits": agents[i]["persona"].personality_traits
                            },
                            "model_used": "error_fallback",
                            "generated_at": datetime.now().isoformat()
                        }
                        valid_responses.append(fallback_response)
                    elif response and isinstance(response, dict) and response.get("content", "").strip():
                        # Only include valid, non-empty responses
                        valid_responses.append(response)
                    else:
                        # Use fallback when the response is invalid or empty
                        logger.warning(f"⚠️ Task {i+1} returned empty content; using fallback")
                        fallback_response = {
                            "agent_id": agents[i]["agent_id"],
                            "content": "This is complete nonsense and total manipulation.",
                            "persona_info": {
                                "name": agents[i]["persona"].name,
                                "type": agents[i]["persona"].malicious_type,
                                "traits": agents[i]["persona"].personality_traits
                            },
                            "model_used": "empty_fallback",
                            "generated_at": datetime.now().isoformat()
                        }
                        valid_responses.append(fallback_response)


                return valid_responses
            else:
                return []

        except Exception as e:
            logger.error(f"❌ Parallel cluster response generation failed: {e}")
            import traceback
            logger.error(f"Error details: {traceback.format_exc()}")
            return []

    async def _async_generate_single_response(self, agent: Dict, target_content: str) -> Dict[str, Any]:
        """Generate a single agent response asynchronously"""
        persona = agent["persona"]
        try:
            # Use asyncio.to_thread to run the synchronous LLM call and grab model info
            content, model_used = await asyncio.to_thread(self._sync_llm_call_with_model_info, persona, target_content)

            if content and len(content.strip()) > 3:
                response = {
                    "agent_id": agent["agent_id"],
                    "content": content,
                    "persona_info": {
                        "name": persona.name,
                        "type": persona.malicious_type,
                        "traits": persona.personality_traits
                    },
                    "model_used": model_used,
                    "generated_at": datetime.now().isoformat()
                }
                return response
            else:
                # Use a highly aggressive fallback
                fallback_responses = [
                    "This is total bullshit designed to screw over regular people.",
                    "What garbage propaganda from idiots who believe every lie.",
                    "This proves everything is corrupted and rigged - wake up fools.",
                    "Another catastrophic lie designed to keep you enslaved forever.",
                    "This toxic nonsense is why our civilization is collapsing.",
                    "Stop spreading these dangerous lies that are killing people."
                ]
                fallback_content = random.choice(fallback_responses)
                response = {
                    "agent_id": agent["agent_id"],
                    "content": fallback_content,
                    "persona_info": {
                        "name": persona.name,
                        "type": persona.malicious_type,
                        "traits": persona.personality_traits
                    },
                    "model_used": "fallback_async",
                    "generated_at": datetime.now().isoformat()
                }
                logger.info(f"🛡️ Persona {persona.name} used fallback: {fallback_content}")
                return response

        except Exception as e:
            logger.error(f"❌ Persona {persona.name} failed to generate response: {e}")
            # Even on failure, add a fallback to keep the attack complete
            fallback_content = "This is total garbage that shows how screwed up everything has become."
            response = {
                "agent_id": agent["agent_id"],
                "content": fallback_content,
                "persona_info": {
                    "name": persona.name,
                    "type": persona.malicious_type,
                    "traits": persona.personality_traits
                },
                "model_used": "error_fallback",
                "generated_at": datetime.now().isoformat()
            }
            logger.info(f"🛡️ Persona {persona.name} error fallback: {fallback_content}")
            return response

    def _sync_llm_call_simple_direct(self, persona: MaliciousPersona, target_content: str) -> str:
        """Highly diversified LLM call that avoids templating"""
        try:
            # Obtain the model client
            client, model_name = self.model_selector.create_langchain_client()

            # Dynamically craft a highly personalized prompt to avoid templating
            prompt = self._build_malicious_comment_prompt(persona, target_content)

            # Directly call without any timeout or threading mechanisms
            # Configure an appropriate max_tokens value to ensure full responses
            try:
                response = client.invoke(prompt)
            except Exception as e:
                # If the call fails, try again with more conservative parameters
                if "max_tokens" in str(e).lower():
                    # Reduce the token limit and retry
                    response = client.invoke(prompt)
                else:
                    raise e

            content = response.content.strip() if response and hasattr(response, 'content') else ""

            if content:
                # Ensure content completeness; only truncate when it is too long
                words = content.split()

                # If the content exceeds 50 words, truncate intelligently at a sentence boundary
                if len(words) > 50:
                    # Look for a sentence end between word positions 30 and 45
                    for i in range(min(45, len(words)), min(30, len(words)) - 1, -1):
                        if words[i-1].endswith(('.', '!', '?')):
                            content = ' '.join(words[:i])
                            break
                    else:
                        # If no suitable end is found, trim to 40 words and add a period
                        content = ' '.join(words[:40])
                        if not content.endswith(('.', '!', '?')):
                            content += '.'

                # Clean formatting while keeping the expression natural
                content = content.replace('"', '').replace(''', '').replace(''', '')
                content = content.replace('*', '').replace('—', '-')

                # Log successful usage
                try:
                    self.model_selector.record_usage(model_name, success=True)
                except:
                    pass

                return content
            else:
                logger.warning(f"⚠️ Persona {persona.name} LLM returned an empty response")
                return ""

        except Exception as e:
            logger.warning(f"⚠️ Persona {persona.name} LLM call exception: {str(e)[:50]}")
            try:
                self.model_selector.record_usage(model_name, success=False)
            except:
                pass
            return ""

    def _sync_llm_call_with_model_info(self, persona: MaliciousPersona, target_content: str) -> tuple[str, str]:
        """Synchronous LLM call that returns both content and model name"""
        try:
            # Obtain the model client
            client, model_name = self.model_selector.create_langchain_client()

            # Dynamically craft the prompt
            prompt = self._build_malicious_comment_prompt(persona, target_content)

            # Call the LLM directly with parameters tuned for complete generation
            try:
                response = client.invoke(prompt)
            except Exception as e:
                # If the call fails, retry with more conservative parameters
                if "max_tokens" in str(e).lower():
                    # Reduce the token limit and retry
                    response = client.invoke(prompt)
                else:
                    raise e

            content = response.content.strip() if response and hasattr(response, 'content') else ""

            if content:
                # Ensure content completeness; truncate only when excessively long
                words = content.split()

                # If the content exceeds 50 words, truncate at a reasonable sentence boundary
                if len(words) > 50:
                    # Look for a sentence end between word positions 30 and 45
                    for i in range(min(45, len(words)), min(30, len(words)) - 1, -1):
                        if words[i-1].endswith(('.', '!', '?')):
                            content = ' '.join(words[:i])
                            break
                    else:
                        # If no suitable boundary is found, cut to 40 words and add a period
                        content = ' '.join(words[:40])
                        if not content.endswith(('.', '!', '?')):
                            content += '.'

                # Clean formatting while maintaining natural expression
                content = content.replace('"', '').replace(''', '').replace(''', '')
                content = content.replace('*', '').replace('—', '-')

                # Record successful usage
                try:
                    self.model_selector.record_usage(model_name, success=True)
                except:
                    pass

                return content, model_name
            else:
                logger.warning(f"⚠️ Persona {persona.name} LLM returned an empty response")
                return "", "unknown"

        except Exception as e:
            logger.warning(f"⚠️ Persona {persona.name} LLM call exception: {str(e)[:50]}")
            try:
                self.model_selector.record_usage(model_name if 'model_name' in locals() else "unknown", success=False)
            except:
                pass
            return "", "unknown"

    def get_random_persona(self) -> MaliciousPersona:
        """Get a random malicious persona"""
        try:
            return random.choice(self.malicious_personas)
        except Exception as e:
            logger.error(f"❌ Getting a random malicious persona failed: {e}")
            # Return a default persona
            return self.malicious_personas[0] if self.malicious_personas else None

    def get_statistics(self) -> Dict[str, Any]:
        """getstatisticsinformation"""
        return {
            "total_personas": len(self.malicious_personas),
            "persona_types": list(set(p.malicious_type for p in self.malicious_personas)),
            "model_stats": self.model_selector.get_usage_stats()
        }

    async def coordinate_attack(self, target_post_id: str, target_content: str, attack_size: int) -> List[Dict[str, Any]]:
        """Coordinate an attack; agent count is determined by configuration"""
        try:

            # Generate cluster responses by awaiting the async method
            responses = await self.generate_cluster_response(
                target_content=target_content,
                agent_count=attack_size,
                context={"target_post_id": target_post_id}
            )

            return responses

        except Exception as e:
            logger.error(f"❌ Attack coordination failed: {e}")
            return []
