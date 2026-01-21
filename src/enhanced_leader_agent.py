"""
Enhanced Leader Agent - uses an argument knowledge base to implement the full USC workflow.
Workflow: strategist instruction → search argument base → generate 5 candidates → score and select → output best copy.
"""

import json
import logging
import os
import random
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import OpenAI
from keys import OPENAI_API_KEY, OPENAI_BASE_URL
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'evidence_database'))
from enhanced_opinion_system import EnhancedOpinionSystem

# Create a standalone workflow logger
def get_workflow_logger():
    """Get or create the workflow logger."""
    try:
        # Try to import from coordination_system
        from agents.simple_coordination_system import workflow_logger
        return workflow_logger
    except ImportError:
        # If import fails, create a standalone logger
        logger = logging.getLogger('enhanced_leader_workflow')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

workflow_logger = get_workflow_logger()


class ArgumentDatabase:
    """Argument knowledge base manager - simplified version, direct SQLite access."""
    
    def __init__(self):
        self.db_path = "argument_knowledge_base/data/knowledge_base.db"
        self.connection = None
        self._connect_database()
    
    def _connect_database(self):
        """Connect to the argument knowledge base database."""
        try:
            if os.path.exists(self.db_path):
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row  # Allow access by column name
                workflow_logger.info(f"✅ Argument knowledge base connected: {self.db_path}")
                
                # Inspect database contents
                cursor = self.connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM arguments")
                count = cursor.fetchone()[0]
                workflow_logger.info(f"   Database contains {count} argument records")
                
            else:
                workflow_logger.warning(f"⚠️  Argument knowledge base file not found: {self.db_path}")
                workflow_logger.info("   Falling back to the default argument base")
                
        except Exception as e:
            workflow_logger.error(f"❌ Failed to connect to argument knowledge base: {e}")
            self.connection = None
    
    def search_relevant_arguments(self, task_description: str, max_results: int = 5) -> List[Dict]:
        """Search for core arguments related to the task using simple keyword matching."""
        if not self.connection:
            workflow_logger.warning("⚠️  Argument knowledge base unavailable, returning empty results")
            return []
            
        try:
            # Extract keywords for searching
            keywords = self._extract_keywords(task_description)
            
            if not keywords:
                print("⚠️  No valid keywords extracted, returning random samples")
                return self._get_random_arguments(max_results)
            
            relevant_arguments = []
            cursor = self.connection.cursor()
            
            # Search relevant arguments for each keyword
            for keyword in keywords[:3]:  # Limit to the first 3 keywords
                query = "SELECT * FROM arguments WHERE text LIKE ? LIMIT ?"
                cursor.execute(query, (f"%{keyword}%", max_results))
                results = cursor.fetchall()
                
                for row in results:
                    argument = {
                        'content': row['text'],
                        'type': row['type'],
                        'source_claim': row['source_claim'] if 'source_claim' in row.keys() else '',
                        'db_id': row['id'],
                        'relevance_score': 0.7,  # Simplified relevance score
                        'keyword_matched': keyword
                    }
                    
                    # Avoid duplicates
                    if not any(arg['db_id'] == argument['db_id'] for arg in relevant_arguments):
                        relevant_arguments.append(argument)
            
            # If nothing matches, return random samples
            if not relevant_arguments:
                workflow_logger.info("   No keyword-matched arguments found, returning random samples")
                return self._get_random_arguments(max_results)
            
            # Limit result count (already collected by keyword)
            relevant_arguments = relevant_arguments[:max_results]
            workflow_logger.info(f"   Retrieved {len(relevant_arguments)} relevant arguments from the knowledge base")
            
            return relevant_arguments
            
        except Exception as e:
            workflow_logger.error(f"⚠️  Argument search failed: {e}")
            return self._get_random_arguments(max_results)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords."""
        # Simplified keyword extraction
        import re
        
        # Remove punctuation and convert to lowercase
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        # Filter stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'of', 'already', 'at', 'is', 'i', 'have', 'and', 'then', 'not', 'person', 'all', 'one', 'need'
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords[:5]  # Return top 5 keywords
    
    def _get_random_arguments(self, count: int) -> List[Dict]:
        """Get random argument samples."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM arguments ORDER BY RANDOM() LIMIT ?", (count,))
            results = cursor.fetchall()
            
            arguments = []
            for row in results:
                argument = {
                    'content': row['text'][:200] + '...' if len(row['text']) > 200 else row['text'],
                    'type': row['type'],
                    'source_claim': row['source_claim'] if 'source_claim' in row.keys() else '',
                    'db_id': row['id'],
                    'relevance_score': 0.5,  # Default relevance for random samples
                    'keyword_matched': 'random_sample'
                }
                arguments.append(argument)
                
            return arguments
            
        except Exception as e:
            print(f"⚠️  Failed to get random argument samples: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("✅ Argument knowledge base connection closed")


class EnhancedLeaderAgent:
    """Enhanced Leader Agent - implements the full USC workflow."""
    
    def __init__(self, agent_id: str = "enhanced_leader_main"):
        self.agent_id = agent_id
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=120
        )
        # Use the new argument system
        self.evidence_system = EnhancedOpinionSystem()
        self.content_history = []
        
        # USC workflow parameters
        # Candidate count: one USC run generates 6 high-quality comment candidates
        self.candidate_count = 6
        self.evaluation_criteria = [
            "Persuasiveness", "Logic", "Readability", "Relevance", "Impact"
        ]
    
    async def generate_strategic_content(self, strategist_instruction: Dict[str, Any], 
                                       target_content: str = "") -> Dict[str, Any]:
        """Execute the full Leader Agent USC workflow."""
        try:
            workflow_logger.info("\n🎯 Leader Agent starting USC workflow")
            workflow_logger.info("=" * 60)
            
            # Step 1: Parse strategist instructions
            workflow_logger.info("📋 Step 1: Parse strategist instructions")
            core_viewpoint = self._extract_core_viewpoint(strategist_instruction)
            workflow_logger.info(f"   Core viewpoint: {core_viewpoint[:100]}...")
            
            # Step 2: Search argument knowledge base
            workflow_logger.info("\n📚 Step 2: Search cognitive memory core-viewpoint argument base")
            relevant_arguments = self._search_evidence_database(core_viewpoint)
            workflow_logger.info(f"   Retrieved {len(relevant_arguments)} relevant arguments")
            
            for i, arg in enumerate(relevant_arguments[:3], 1):
                workflow_logger.info(
                    f"   Argument {i}: {arg['content'][:50]}... (relevance: {arg['relevance_score']:.2f})"
                )
            
            # Step 3: USC-Generate - generate multiple candidate comments
            workflow_logger.info(
                f"\n✍️  Step 3: USC-Generate - generate {self.candidate_count} candidate comments"
            )
            candidates = await self._generate_candidates(
                strategist_instruction, target_content, relevant_arguments
            )
            workflow_logger.info(f"   Successfully generated {len(candidates)} candidates")
            
            # Step 4: USC-Vote - score and reflect, select the best version
            workflow_logger.info("\n🔍 Step 4: USC-Vote - score and select the best version")
            best_candidate = await self._evaluate_and_select(candidates, strategist_instruction)
            workflow_logger.info(
                f"   Best candidate score: {best_candidate.get('total_score', 0):.2f}/5.0"
            )

            # Select a second candidate for posting, distinct from the best one in content and angle
            import random
            alternative_candidates = [
                c for c in candidates
                if c.get("id") != best_candidate.get("id")
            ]
            if alternative_candidates:
                second_candidate = alternative_candidates[0]
            else:
                # If no other candidates exist, fall back to reusing the best candidate
                second_candidate = best_candidate
            
            # Step 5: Output final copy
            workflow_logger.info("\n📤 Step 5: Output final copy")
            final_result = self._format_final_output(best_candidate, strategist_instruction, relevant_arguments)

            # Attach the top two comments to the final result for the coordination system
            try:
                content_record = final_result.get("content", {})
                content_record["selected_comments"] = [
                    {
                        "id": best_candidate.get("id", "candidate_1"),
                        "content": best_candidate.get("content", "")
                    },
                    {
                        "id": second_candidate.get("id", "candidate_2"),
                        "content": second_candidate.get("content", "")
                    },
                ]
                final_result["content"] = content_record
            except Exception as e:
                logging.error(f"Failed to append selected_comments to USC result: {e}")

            workflow_logger.info(
                f"   Best comment length: {len(best_candidate.get('content', ''))} characters"
            )
            
            workflow_logger.info("=" * 60)
            workflow_logger.info("✅ USC workflow completed")
            
            return final_result
            
        except Exception as e:
            logging.error(f"Enhanced Leader Agent USC workflow failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_core_viewpoint(self, instruction: Dict[str, Any]) -> str:
        """Extract the core viewpoint from strategist output."""
        # Extract core_counter_argument directly
        if 'core_counter_argument' in instruction and instruction['core_counter_argument']:
            core_viewpoint = str(instruction['core_counter_argument'])
            workflow_logger.info(f"   Extracted core viewpoint: {core_viewpoint[:100]}...")
            return core_viewpoint
        
        # If core_counter_argument is missing, extract from leader_instruction.core_message
        if 'leader_instruction' in instruction and isinstance(instruction['leader_instruction'], dict):
            leader_instruction = instruction['leader_instruction']
            if 'core_message' in leader_instruction and leader_instruction['core_message']:
                core_viewpoint = str(leader_instruction['core_message'])
                workflow_logger.info(f"   Extracted from leader_instruction: {core_viewpoint[:100]}...")
                return core_viewpoint
        
        # If neither is found, log and return empty string
        workflow_logger.warning("   core_counter_argument or core_message not found")
        return ""
    
    def _search_evidence_database(self, core_viewpoint: str) -> List[Dict]:
        """Search for relevant arguments using the new argument system."""
        try:
            # Validate input
            if not core_viewpoint or not core_viewpoint.strip():
                workflow_logger.warning("⚠️ Core viewpoint is empty, using default arguments")
                return self._get_default_arguments()

            # Process viewpoint with EnhancedOpinionSystem
            result = self.evidence_system.process_opinion(core_viewpoint)

            if 'error' in result:
                workflow_logger.warning(f"⚠️ Argument system processing failed: {result['error']}")
                workflow_logger.info("   🔄 Trying backup argument generation")
                return self._get_backup_arguments(core_viewpoint)

            # Extract evidence info
            evidence_list = result.get('evidence', [])
            relevant_arguments = []

            for i, evidence in enumerate(evidence_list):
                argument = {
                    'content': evidence.get('evidence', ''),
                    'type': 'evidence',
                    'source_claim': core_viewpoint,
                    'db_id': f"evidence_{i}",
                    'relevance_score': evidence.get('acceptance_rate', 0.5),
                    'keyword_matched': result.get('keyword', ''),
                    'theme': result.get('theme', ''),
                    'source': evidence.get('source', 'Wikipedia')
                }
                relevant_arguments.append(argument)

            workflow_logger.info(f"   Argument system status: {result.get('status', 'unknown')}")
            workflow_logger.info(f"   Theme: {result.get('theme', 'unknown')}")
            workflow_logger.info(f"   Keyword: {result.get('keyword', 'unknown')}")

            # If no relevant arguments found, use backup
            if not relevant_arguments:
                workflow_logger.info("   🔄 No relevant arguments found, using backup generation")
                return self._get_backup_arguments(core_viewpoint)

            return relevant_arguments

        except Exception as e:
            workflow_logger.error(f"❌ Argument search failed: {e}")
            workflow_logger.info("   🔄 Using backup argument generation")
            return self._get_backup_arguments(core_viewpoint)

    def _get_default_arguments(self) -> List[Dict]:
        """Get default arguments for empty viewpoints."""
        default_arguments = [
            {
                'content': "Multiple perspectives exist on complex issues, and it's important to consider various viewpoints before forming conclusions.",
                'type': 'general_principle',
                'source_claim': 'balanced_discussion',
                'db_id': 'default_1',
                'relevance_score': 0.6,
                'keyword_matched': 'default',
                'theme': 'General Discussion',
                'source': 'Default Knowledge Base'
            },
            {
                'content': "Evidence-based approaches help us understand complex situations more clearly and make informed decisions.",
                'type': 'methodology',
                'source_claim': 'evidence_based',
                'db_id': 'default_2',
                'relevance_score': 0.6,
                'keyword_matched': 'default',
                'theme': 'Critical Thinking',
                'source': 'Default Knowledge Base'
            },
            {
                'content': "Open dialogue and respectful discussion are essential for addressing controversial topics effectively.",
                'type': 'communication',
                'source_claim': 'constructive_dialogue',
                'db_id': 'default_3',
                'relevance_score': 0.6,
                'keyword_matched': 'default',
                'theme': 'Communication',
                'source': 'Default Knowledge Base'
            }
        ]

        workflow_logger.info(f"   Using default arguments: {len(default_arguments)} general items")
        return default_arguments

    def _get_backup_arguments(self, core_viewpoint: str) -> List[Dict]:
        """Backup argument generation - create related arguments with the LLM."""
        try:
            workflow_logger.info(f"   Generating backup arguments for: {core_viewpoint[:50]}...")

            # Use LLM to generate related arguments
            response = self.client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a knowledge synthesis expert. Given a viewpoint, generate 3-5 relevant supporting arguments with diverse perspectives.

Requirements:
1. Each argument should be factual and well-reasoned
2. Arguments should come from different angles (logical, empirical, ethical, practical)
3. Each argument should be 100-200 words
4. Focus on balanced, evidence-based reasoning
5. CRITICAL: Generate content ONLY in English"""
                    },
                    {
                        "role": "user",
                        "content": f"""Viewpoint: {core_viewpoint}

Please generate 3-5 supporting arguments for this viewpoint from different perspectives. Each argument should be clear, factual, and well-reasoned. Generate content ONLY in English."""
                    }
                ],
                temperature=0.7
            )

            content = response.choices[0].message.content

            # Parse generated arguments
            arguments = self._parse_generated_arguments(content, core_viewpoint)

            workflow_logger.info(f"   Backup arguments generated: {len(arguments)} items")
            return arguments

        except Exception as e:
            workflow_logger.warning(f"   ⚠️  Backup argument generation failed: {e}")
            # Return default arguments
            return self._get_default_arguments()

    def _parse_generated_arguments(self, content: str, core_viewpoint: str) -> List[Dict]:
        """Parse LLM-generated arguments."""
        try:
            # Split by paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

            arguments = []
            for i, paragraph in enumerate(paragraphs[:5]):  # Take up to 5
                if len(paragraph) > 50:  # Filter out short content
                    argument = {
                        'content': paragraph,
                        'type': 'llm_generated',
                        'source_claim': core_viewpoint,
                        'db_id': f'backup_{i+1}',
                        'relevance_score': 0.7,
                        'keyword_matched': 'llm_generated',
                        'theme': 'LLM Generated',
                        'source': 'Language Model'
                    }
                    arguments.append(argument)

            # If parsing fails, return at least one basic argument
            if not arguments:
                arguments = [{
                    'content': f"Regarding the viewpoint '{core_viewpoint}', it's important to consider multiple perspectives and examine available evidence to form a well-reasoned understanding.",
                    'type': 'fallback',
                    'source_claim': core_viewpoint,
                    'db_id': 'fallback_1',
                    'relevance_score': 0.5,
                    'keyword_matched': 'fallback',
                    'theme': 'General Response',
                    'source': 'Fallback System'
                }]

            return arguments

        except Exception as e:
            workflow_logger.warning(f"   ⚠️  Argument parsing failed: {e}")
            return self._get_default_arguments()

    async def _generate_candidates(self, instruction: Dict[str, Any], 
                                 target_content: str, 
                                 arguments: List[Dict]) -> List[Dict]:
        """USC-Generate: generate multiple candidate comments with overall diversity."""
        candidates = []
        
        # Prepare argument text
        argument_texts = []
        for arg in arguments:
            argument_texts.append(f"- {arg['content'][:200]}...")
        
        arguments_context = "\n".join(argument_texts) if argument_texts else "No relevant arguments available"
        
        for i in range(self.candidate_count):
            try:
                # Design distinct creative angles for each candidate
                angles = [
                    "Rational analysis angle, focusing on logical argumentation",
                    "Emotional resonance angle, focusing on touching hearts", 
                    "Practical advice angle, focusing on providing solutions",
                    "Balanced perspective angle, focusing on showing multi-dimensional thinking",
                    "Authoritative professional angle, focusing on demonstrating expertise",
                    "Community engagement angle, focusing on fostering constructive dialogue and mutual understanding"
                ]
                
                # Ensure each candidate has a distinct angle
                if i < len(angles):
                    current_angle = angles[i]
                else:
                    # If candidates exceed angles, reuse the last angle with a variant
                    base_angle = angles[-1]
                    current_angle = f"{base_angle} (variant {i - len(angles) + 1})"
                
                response = self.client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are a top-tier content creation expert. Please create high-quality SOCIAL MEDIA COMMENT style content based on the following requirements:

Creation Angle: {current_angle}
Tone Style: {instruction.get('tone', 'rational and objective')}
Target Audience: {instruction.get('target_audience', 'rational users')}
Content Length: {instruction.get('content_length', '80-200 words')}

Requirements:
1. Content must be original, persuasive, and suitable as a standalone social media comment.
2. Keep the comment concise, focusing on 1–3 key points, not a long essay.
3. Match the specified creation angle while staying consistent with the strategist's overall stance.
4. Appropriately reference arguments to support viewpoints (no need to cite sources explicitly).
5. Across ALL candidates, ensure STRONG DIVERSITY in tone, structure, opening sentences, and examples.
6. This specific candidate should avoid reusing wording or structure from other possible candidates — imagine each is written by a different real person."""
                        },
                        {
                            "role": "user", 
                            "content": f"""Strategist Instructions: {instruction}

Target Content (content to respond to):
{target_content}

Available Argument Database:
{arguments_context}

Please create a high-quality response based on the above information, using the "{current_angle}" approach. Generate the response ONLY in English."""
                        }
                    ],
                    temperature=0.8 + (i * 0.05)  # Add some randomness per candidate
                )
                
                content = response.choices[0].message.content
                
                candidate = {
                    'id': f"candidate_{i+1}",
                    'content': content,
                    'creation_angle': current_angle,
                    'temperature': 0.8 + (i * 0.05),
                    'timestamp': datetime.now().isoformat()
                }
                
                candidates.append(candidate)
                workflow_logger.info(
                    f"   Candidate {i+1}: {content[:50]}... (angle: {current_angle})"
                )
                
            except Exception as e:
                workflow_logger.warning(f"   ⚠️  Candidate {i+1} generation failed: {e}")
                continue
        
        return candidates
    
    async def _evaluate_and_select(self, candidates: List[Dict], 
                                 instruction: Dict[str, Any]) -> Dict:
        """USC-Vote: score and reflect, select the best version."""
        evaluated_candidates = []
        
        for candidate in candidates:
            try:
                # Score each candidate across dimensions, adjusting focus by creative angle
                creation_angle = candidate.get('creation_angle', '')

                # Adjust evaluation focus by creative angle
                evaluation_focus = ""
                if "Rational analysis" in creation_angle:
                    evaluation_focus = "Pay special attention to logical reasoning and evidence-based arguments."
                elif "Emotional resonance" in creation_angle:
                    evaluation_focus = "Pay special attention to emotional appeal and persuasive power."
                elif "Practical advice" in creation_angle:
                    evaluation_focus = "Pay special attention to practical relevance and actionable solutions."
                elif "Balanced perspective" in creation_angle:
                    evaluation_focus = "Pay special attention to multi-dimensional thinking and balanced viewpoints."
                elif "Authoritative professional" in creation_angle:
                    evaluation_focus = "Pay special attention to expertise demonstration and professional credibility."

                response = self.client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are a professional content evaluation expert. Please evaluate the following content across multiple dimensions (1-5 points):

Evaluation Dimensions:
1. Persuasiveness - Whether the content is persuasive and compelling
2. Logic - Whether the argumentation is logically clear and well-structured
3. Readability - Whether the language is fluent and easy to understand
4. Relevance - Whether it targets specific situations and audiences
5. Impact - Whether it has positive social influence

{evaluation_focus}

Please score each dimension and provide overall evaluation and improvement suggestions.

Output Format:
Persuasiveness: X points - evaluation
Logic: X points - evaluation
Readability: X points - evaluation
Relevance: X points - evaluation
Impact: X points - evaluation
Total Score: X points
Overall Evaluation: [detailed evaluation]
Improvement Suggestions: [specific suggestions]"""
                        },
                        {
                            "role": "user",
                            "content": f"""Strategist Requirements: {instruction}

Content to Evaluate:
{candidate['content']}

Creation Angle: {candidate['creation_angle']}

Please conduct a professional evaluation with focus on the creation angle's strengths."""
                        }
                    ],
                    temperature=0.3 + (hash(candidate['id']) % 3) * 0.1  # Add evaluation randomness per candidate
                )
                
                evaluation = response.choices[0].message.content
                
                # Parse scoring results
                scores = self._parse_evaluation_scores(evaluation)
                total_score = sum(scores.values()) / len(scores) if scores else 0
                
                evaluated_candidate = {
                    **candidate,
                    'evaluation': evaluation,
                    'scores': scores,
                    'total_score': total_score
                }
                
                evaluated_candidates.append(evaluated_candidate)
                workflow_logger.info(f"   {candidate['id']}: total {total_score:.2f}/5.0")
                
            except Exception as e:
                workflow_logger.warning(f"   ⚠️  {candidate['id']} scoring failed: {e}")
                # Add default scores
                evaluated_candidate = {
                    **candidate,
                    'evaluation': f"Scoring failed: {e}",
                    'scores': {dim: 3.0 for dim in self.evaluation_criteria},
                    'total_score': 3.0
                }
                evaluated_candidates.append(evaluated_candidate)
        
        # Select the highest-scoring candidate
        if evaluated_candidates:
            best_candidate = max(evaluated_candidates, key=lambda x: x['total_score'])
            workflow_logger.info(
                f"   🏆 Best selection: {best_candidate['id']} (total: {best_candidate['total_score']:.2f})"
            )
            return best_candidate
        else:
            # If evaluation fails, return the first candidate
            return candidates[0] if candidates else {}
    
    def _parse_evaluation_scores(self, evaluation_text: str) -> Dict[str, float]:
        """Parse evaluation scores with multiple English variants."""
        scores = {}
        lines = evaluation_text.split('\n')

        # Criterion mapping
        criteria_mapping = {
            "Persuasiveness": ["Persuasiveness", "persuasiveness"],
            "Logic": ["Logic", "logic"],
            "Readability": ["Readability", "readability"],
            "Relevance": ["Relevance", "relevance"],
            "Impact": ["Impact", "impact"]
        }

        for line in lines:
            line = line.strip()
            for criterion, english_variants in criteria_mapping.items():
                # Check whether the line contains any relevant label
                for variant in english_variants:
                    if variant in line:
                        try:
                            # Try multiple score extraction patterns
                            import re

                            # Pattern 1: "Persuasiveness: 4 points"
                            pattern1 = rf"{variant}:\s*(\d+(?:\.\d+)?)\s*point"
                            match1 = re.search(pattern1, line, re.IGNORECASE)

                            # Pattern 2: "Persuasiveness: 4 points"
                            pattern2 = rf"{variant}:\s*(\d+(?:\.\d+)?)\s*(?:points?)?"
                            match2 = re.search(pattern2, line, re.IGNORECASE)

                            # Pattern 3: "4 points - evaluation" or "4/5"
                            pattern3 = r"(\d+(?:\.\d+)?)\s*(?:points?|/5)"
                            match3 = re.search(pattern3, line, re.IGNORECASE)

                            score = None
                            if match1:
                                score = float(match1.group(1))
                            elif match2:
                                score = float(match2.group(1))
                            elif match3 and variant.lower() in line.lower():
                                score = float(match3.group(1))

                            if score is not None:
                                scores[criterion] = min(5.0, max(1.0, score))  # Clamp to 1-5 range
                                break

                        except (ValueError, AttributeError):
                            continue

                if criterion in scores:
                    break

        # If parsing is incomplete, try to extract "Total Score"
        if not scores or len(scores) < 3:
            import re
            total_pattern = r"Total\s*Score:\s*(\d+(?:\.\d+)?)"
            total_match = re.search(total_pattern, evaluation_text, re.IGNORECASE)
            if total_match:
                total_score = float(total_match.group(1))
                # If total score exists, distribute similar scores across dimensions
                base_score = min(5.0, max(1.0, total_score))
                for criterion in self.evaluation_criteria:
                    if criterion not in scores:
                        # Add small randomness to avoid identical values
                        import random
                        variation = random.uniform(-0.3, 0.3)
                        scores[criterion] = min(5.0, max(1.0, base_score + variation))

        # Final fallback: assign default scores with randomness
        for criterion in self.evaluation_criteria:
            if criterion not in scores:
                import random
                scores[criterion] = round(random.uniform(2.5, 4.0), 1)  # Random 2.5-4.0

        return scores
    
    def _format_final_output(self, best_candidate: Dict, 
                           instruction: Dict[str, Any], 
                           arguments: List[Dict]) -> Dict[str, Any]:
        """Format the final output."""
        content_record = {
            "content_id": f"enhanced_leader_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "final_content": best_candidate.get('content', ''),
            "usc_process": {
                "strategist_instruction": instruction,
                "retrieved_arguments": len(arguments),
                "candidates_generated": self.candidate_count,
                "selected_candidate": {
                    "id": best_candidate.get('id', ''),
                    "creation_angle": best_candidate.get('creation_angle', ''),
                    "total_score": best_candidate.get('total_score', 0),
                    "scores": best_candidate.get('scores', {}),
                    "evaluation": best_candidate.get('evaluation', '')
                }
            },
            "timestamp": datetime.now(),
            # Include for reward-driven knowledge refinement
            "relevant_arguments": arguments,
            "best_candidate": best_candidate
        }
        
        # Record to history
        self.content_history.append(content_record)
        
        return {
            "success": True,
            "content_generated": True,
            "content": content_record,
            "process_details": {
                "arguments_used": len(arguments),
                "candidates_evaluated": self.candidate_count,
                "winning_score": best_candidate.get('total_score', 0)
            }
        }


    async def _reward_driven_knowledge_refinement(self, 
                                                 best_candidate: Dict, 
                                                 relevant_arguments: List[Dict],
                                                 effectiveness_score: float) -> None:
        """
        Reward-driven knowledge refinement - update argument scores based on actual intervention effectiveness
        
        Formula: s_i ← s_i + η · R(s_t, a_t) · I[k_i ∈ a_t]
        Where:
        - η = 0.01 (learning rate)
        - R(s_t, a_t) = actual intervention effectiveness score (from _analyst_monitor_effectiveness)
        - I[k_i ∈ a_t] = indicator function, whether argument k_i was used in action a_t
        """
        try:
            # Set learning rate to 0.01
            learning_rate = 0.01
            
            # Reward value is the actual effectiveness score (already in 0-1 range)
            reward = effectiveness_score  # Directly use effectiveness score
            
            final_content = best_candidate.get('content', '')
            
            workflow_logger.info(f"   Learning rate η = {learning_rate}")
            workflow_logger.info(f"   Reward value R = {reward:.4f} (based on actual effectiveness score {effectiveness_score:.4f})")
            workflow_logger.info(f"   Starting to check usage of {len(relevant_arguments)} arguments...")
            
            # Track update information
            updated_arguments = []
            unused_arguments = []
            
            for argument in relevant_arguments:
                arg_content = argument.get('content', '')
                arg_id = argument.get('db_id', '')
                old_score = argument.get('relevance_score', 0.5)
                
                # Check if argument was used in final content - using multiple matching strategies
                is_used = self._check_argument_usage(arg_content, final_content)
                
                if is_used:
                    # Calculate new score: s_i ← s_i + η · R · I[k_i ∈ a_t]
                    # When argument is used, I[k_i ∈ a_t] = 1
                    score_update = learning_rate * reward
                    new_score = min(1.0, old_score + score_update)  # Upper limit 1.0
                    
                    updated_arguments.append({
                        'id': arg_id,
                        'old_score': old_score,
                        'new_score': new_score,
                        'update': score_update,
                        'status': 'used'
                    })
                    
                    workflow_logger.info(
                        f"   ✅ Argument {arg_id} used: "
                        f"{old_score:.4f} + {score_update:.6f} = {new_score:.4f}"
                    )
                    
                    # Update score in database
                    self._update_argument_score_in_db(arg_id, new_score, 'used', effectiveness_score)
                else:
                    # When argument not used, I[k_i ∈ a_t] = 0, no score update
                    unused_arguments.append({
                        'id': arg_id,
                        'old_score': old_score,
                        'status': 'unused'
                    })
                    
                    workflow_logger.info(
                        f"   ⊘ Argument {arg_id} not used (keep score {old_score:.4f})"
                    )
            
            # Output statistics
            used_count = len(updated_arguments)
            unused_count = len(unused_arguments)
            
            workflow_logger.info(f"\n   📊 Knowledge refinement statistics:")
            workflow_logger.info(f"      Arguments used: {used_count}")
            workflow_logger.info(f"      Arguments not used: {unused_count}")
            
            if updated_arguments:
                avg_update = sum(arg['update'] for arg in updated_arguments) / len(updated_arguments)
                workflow_logger.info(f"      Average update value: {avg_update:.6f}")
            
            # Record in final result
            self._last_refinement_result = {
                'timestamp': datetime.now().isoformat(),
                'learning_rate': learning_rate,
                'reward': reward,
                'updated_arguments': updated_arguments,
                'unused_arguments': unused_arguments,
                'total_used': used_count,
                'total_unused': unused_count
            }
            
        except Exception as e:
            workflow_logger.error(f"❌ Knowledge refinement process failed: {e}")
            import traceback
            workflow_logger.error(traceback.format_exc())
    
    def _check_argument_usage(self, argument_content: str, final_content: str) -> bool:
        """
        Check if the argument is used in the final content
        Use LLM to determine
        """
        if not argument_content or not final_content:
            return False
        
        # 使用LLM进行语义理解判断
        try:
            return self._llm_check_argument_usage(argument_content, final_content)
        except Exception as e:
            workflow_logger.warning(f"   ⚠️  LLM检查失败: {e}")
            # 如果LLM失败，默认认为未使用
            return False
    
    def _llm_check_argument_usage(self, argument_content: str, final_content: str) -> bool:
        """
        Use LLM to determine whether the argument is used in the final content
        """
        try:
            response = self.client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert content analyzer. Your task is to determine whether the given argument/evidence is used or reflected in the final content.

Consider:
1. Direct usage: The argument text appears directly (with minor wording variations)
2. Conceptual usage: The core idea/concept of the argument is used even if wording is different
3. Not used: The argument is not present or referenced in the final content

Respond with ONLY "YES" or "NO":
- YES: The argument is used or reflected in the final content
- NO: The argument is not used in the final content"""
                    },
                    {
                        "role": "user",
                        "content": f"""Argument/Evidence:
{argument_content}

Final Content:
{final_content}

Is the argument used or reflected in the final content? Respond with only YES or NO."""
                    }
                ],
                temperature=0.2  # Low temperature to ensure stable judgment
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            # Parse LLM response
            is_used = "YES" in result
            
            workflow_logger.debug(f"   LLM judgment: {'used' if is_used else 'not used'} (response: {result})")
            
            return is_used
            
        except Exception as e:
            workflow_logger.warning(f"   LLM judgment failed: {e}")
            raise
    
    def _update_argument_score_in_db(self, arg_id: str, new_score: float, 
                                     usage_status: str, reward: float) -> None:
        """
        Update the score record of the argument in the database
        """
        try:
            # Check if database connection exists
            if not hasattr(self, 'evidence_system') or not self.evidence_system:
                workflow_logger.warning(f"⚠️  Evidence system unavailable, cannot update database")
                return
            
            # If the evidence system has an update method, use it
            if hasattr(self.evidence_system, 'update_argument_score'):
                self.evidence_system.update_argument_score(
                    arg_id=arg_id,
                    new_score=new_score,
                    usage_status=usage_status,
                    reward=reward,
                    timestamp=datetime.now()
                )
                workflow_logger.info(f"   📝 Database updated: {arg_id} = {new_score:.4f}")
            else:
                workflow_logger.warning(f"   ⚠️  Evidence system does not support score update method")
        
        except Exception as e:
            workflow_logger.warning(f"   ⚠️  Database update failed: {e}")        

    def get_process_analytics(self) -> Dict[str, Any]:
        """Get USC process analytics."""
        if not self.content_history:
            return {
                "total_executions": 0,
                "average_arguments_used": 0,
                "average_winning_score": 0,
                "evidence_system_connected": hasattr(self, 'evidence_system') and self.evidence_system is not None,
                "last_execution": None
            }

        total_executions = len(self.content_history)
        avg_arguments_used = sum(record['usc_process']['retrieved_arguments']
                                for record in self.content_history) / total_executions

        all_scores = []
        for record in self.content_history:
            score = record['usc_process']['selected_candidate']['total_score']
            if isinstance(score, (int, float)):
                all_scores.append(score)

        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        return {
            "total_executions": total_executions,
            "average_arguments_used": avg_arguments_used,
            "average_winning_score": avg_score,
            "evidence_system_connected": hasattr(self, 'evidence_system') and self.evidence_system is not None,
            "last_execution": self.content_history[-1]['timestamp'].isoformat() if self.content_history else None
        }
