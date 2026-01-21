from datetime import datetime
import json
import time

import uuid
import logging
import networkx as nx
import matplotlib.pyplot as plt
import sqlite3
import os
import pandas as pd
from typing import Optional, Type, Union, Dict
from openai import OpenAI
from pydantic import BaseModel
import matplotlib
from tenacity import retry, stop_after_attempt, wait_exponential
from deprecated import deprecated

# Global rate limiting controls
_last_request_time = {}
# Model failure counters
_model_failure_count = {}
_min_request_interval = {
    "grok-3-mini": 5.0,      # grok models have a 5-second interval
    "DeepSeek-V3": 30.0,     # DeepSeek has a 30-second interval (increase to avoid rate limits)
    "default": 2.0           # Default models have a 2-second interval (more conservative)
}

def _wait_for_rate_limit(engine: str):
    """Smart request delay control to avoid 502 errors"""
    global _last_request_time, _min_request_interval, _model_failure_count

    current_time = time.time()
    base_interval = _min_request_interval.get(engine, _min_request_interval["default"])

    # Adjust the interval dynamically based on failure count
    failure_count = _model_failure_count.get(engine, 0)
    if failure_count > 0:
        # More failures lead to a longer wait (up to 5x the base interval)
        multiplier = min(1 + failure_count * 0.8, 5.0)
        interval = base_interval * multiplier
        logging.info(f"⚠️ Model {engine} had {failure_count} failures; adjusting interval to {interval:.1f} seconds")
    else:
        interval = base_interval

    if engine in _last_request_time:
        time_since_last = current_time - _last_request_time[engine]
        if time_since_last < interval:
            sleep_time = interval - time_since_last
            # Removed verbose model wait logging
            time.sleep(sleep_time)

    _last_request_time[engine] = time.time()

def _record_model_failure(engine: str):
    """Record that the model failed"""
    global _model_failure_count
    _model_failure_count[engine] = _model_failure_count.get(engine, 0) + 1
    logging.warning(f"🚫 Model {engine} failure count: {_model_failure_count[engine]}")

def _record_model_success(engine: str):
    """Record a successful model response and reset failure count"""
    global _model_failure_count
    if engine in _model_failure_count:
        _model_failure_count[engine] = 0

class Utils:
    @staticmethod
    def configure_logging(engine: str):
        """Configure logging for the simulation."""
        root_logger = logging.getLogger()
        # If logging is already configured (handlers present), avoid reconfiguration
        if root_logger.handlers:
            # Still silence noisy third-party loggers
            for logger_name in ["httpx", "requests", "urllib3"]:
                logging.getLogger(logger_name).setLevel(logging.CRITICAL)
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Resolve paths relative to the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Public-opinion-balance directory
        log_dir = os.path.join(project_root, 'experiment_outputs', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'{timestamp}-{engine}.log')
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            filename=log_file,
                            filemode='w')

        # Add a stream handler to also print to console (only once)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        # Silence web request related loggers
        for logger_name in ["httpx", "requests", "urllib3"]:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)

    @staticmethod
    def generate_formatted_id(prefix: str, conn: Optional[sqlite3.Connection] = None) -> str:
        """Generate a formatted ID with the given prefix and last 6 digits of a UUID.
        Handles UUID collisions if a database connection is provided."""

        # Map of prefixes to their corresponding tables
        prefix_table_map = {
            "user": "users",
            "post": "posts",
            "comment": "comments",
            "note": "community_notes",
            "memory": "agent_memories",
        }

        if conn is None:
            # If no connection provided, just return a new ID (original behavior)
            full_uuid = uuid.uuid4()
            last_6_digits = str(full_uuid)[-6:]
            return f"{prefix}-{last_6_digits}"

        # Get the corresponding table name for the prefix
        table_name = prefix_table_map.get(prefix)
        if not table_name:
            logging.warning(f"Unknown prefix '{prefix}', collision detection disabled")
            full_uuid = uuid.uuid4()
            last_6_digits = str(full_uuid)[-6:]
            return f"{prefix}-{last_6_digits}"

        # Keep trying until we find a unique ID
        while True:
            full_uuid = uuid.uuid4()
            last_6_digits = str(full_uuid)[-6:]
            new_id = f"{prefix}-{last_6_digits}"

            # Check if ID exists in the corresponding table
            cursor = conn.cursor()
            id_column = f"{prefix}_id"
            cursor.execute(f"SELECT 1 FROM {table_name} WHERE {id_column} = ?", (new_id,))

            if cursor.fetchone() is None:
                # ID is unique, we can use it
                return new_id

            logging.warning(f"UUID collision detected for {prefix}, generating new ID...")

    @staticmethod
    @deprecated(reason="We no longer need to visualize the network in this way.")
    def visualize_network(conn, action: str, timestamp: str):
        """Visualize the network graph of users and their follow relationships."""
        # Set up matplotlib
        matplotlib.use('Agg', force=True)
        plt.clf()
        plt.close('all')

        # Get users and create graph
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = [row[0] for row in cursor.fetchall()]

        if not users:
            logging.warning("No users found in database - skipping visualization")
            return

        # Create and populate graph
        G = nx.DiGraph()
        G.add_nodes_from(users)

        cursor.execute("""
            SELECT user_id, target_id
            FROM user_actions
            WHERE action_type = 'follow'
        """)
        edges = [(follower, followed)
                for follower, followed in cursor.fetchall()
                if follower in users and followed in users]
        G.add_edges_from(edges)

        # Create and configure plot
        fig, ax = plt.subplots(figsize=(12, 8))
        pos = nx.spring_layout(G, k=2, iterations=50)

        # Draw network elements
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1000)
        nx.draw_networkx_edges(G, pos,
                              edge_color='gray',
                              arrows=True,
                              arrowsize=10,
                              width=2,
                              min_target_margin=15,
                              connectionstyle='arc3,rad=0.2')

        # Add labels
        labels = {node: str(node) for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=10, font_weight='bold')

        # Configure plot
        ax.set_title("User Network Graph", pad=20)
        ax.margins(0.2)

        # Add border box
        ax.spines['top'].set_visible(True)
        ax.spines['right'].set_visible(True)
        ax.spines['bottom'].set_visible(True)
        ax.spines['left'].set_visible(True)
        ax.set_frame_on(True)

        # Save as PNG only
        output_dir = f'experiment_outputs/plots/{timestamp}'
        os.makedirs(output_dir, exist_ok=True)
        filename = f'{output_dir}/network_graph-{action}.png'

        plt.savefig(filename, format='png', dpi=300, bbox_inches='tight', pad_inches=0.5)
        plt.close('all')


    @staticmethod
    def _clean_llm_response(json_response, response_model):
        """Clean the JSON response to fix common LLM errors before validation."""
        try:
            model_name = response_model.__name__ if hasattr(response_model, '__name__') else str(type(response_model))
            logging.debug(f"Cleaning LLM response for model: {model_name}")

            # Check if this is a FeedReaction or similar model with actions
            # Handle both static and dynamic model classes
            has_actions_field = False
            if hasattr(response_model, 'model_fields'):
                has_actions_field = 'actions' in response_model.model_fields
            elif hasattr(response_model, '__annotations__'):
                has_actions_field = 'actions' in response_model.__annotations__

            if has_actions_field and 'actions' in json_response and isinstance(json_response['actions'], list):
                logging.debug(f"Found {len(json_response['actions'])} actions to clean")
                for i, action_data in enumerate(json_response['actions']):
                    if isinstance(action_data, dict) and 'action' in action_data:
                        original_action = action_data['action']
                        # Fix common invalid actions
                        if action_data['action'] == 'comment':
                            logging.warning(f"Fixing invalid action 'comment' -> 'comment-post' in action {i}")
                            action_data['action'] = 'comment-post'
                        # Add more action fixes as needed
                        if original_action != action_data['action']:
                            logging.info(f"Action {i} changed from '{original_action}' to '{action_data['action']}'")
            else:
                logging.debug(f"Model {model_name} does not have actions field or no actions in response")

            return json_response
        except Exception as e:
            logging.error(f"Error cleaning LLM response: {e}")
            import traceback
            traceback.print_exc()
            return json_response


    @staticmethod
    @retry(
        stop=stop_after_attempt(2),  # Retry twice to give rate limits another chance
        wait=wait_exponential(multiplier=5, min=15, max=120),  # Longer waits, especially for rate limits
        reraise=True,
        before_sleep=lambda retry_state: logging.warning(
            f"Retry attempt {retry_state.attempt_number} after error: {retry_state.outcome.exception()}"
        )
    )
    def generate_llm_response(
        openai_client: OpenAI,
        engine: str,
        prompt: str,
        system_message: str,
        temperature: float,
        response_model: Optional[Type[BaseModel]] = None,
        max_tokens: int = 4096,
        # stop: list[str] = ['\n']
    ) -> Union[str, BaseModel]:
        """Generate a response from the LLM."""
        # Smart rate limit control
        _wait_for_rate_limit(engine)

        # Force English output by enhancing system message
        enhanced_system_message = system_message + """

CRITICAL LANGUAGE REQUIREMENT:
- You MUST respond ONLY in English
- Do NOT use Chinese characters
- Do NOT use Japanese characters
- Do NOT use Korean characters
- Do NOT use any non-English language
- Use only English alphabet and punctuation
- If you accidentally use non-English, you FAIL the task
- Every single word must be in English"""

        messages = [
            {"role": "system", "content": enhanced_system_message},
            {"role": "user", "content": prompt}
        ]

        # Use parse for structured output if model is provided
        if response_model:
            if "gpt" in engine: # Only GPT models support structured output reliably
                # Build parameters; some models do not support penalty parameters
                # Smart timeout settings - adjust based on model and request size
                request_size = sum(len(str(msg)) for msg in messages)
                if request_size > 5000:  # Large request
                    timeout_seconds = 180
                else:
                    timeout_seconds = 60

                params = {
                    "model": engine,
                    "messages": messages,
                    "response_format": response_model,
                    "temperature": temperature,
                    "timeout": timeout_seconds,
                }

                # Only add penalty parameters for supported models
                if "gpt-4" in engine or "gpt-3.5" in engine:
                    params["frequency_penalty"] = 1.6
                    params["presence_penalty"] = 1.6

                try:
                    completion = openai_client.beta.chat.completions.parse(**params)
                    _record_model_success(engine)  # recordsuccessful

                    # Check if parsing failed due to validation errors
                    if completion.choices[0].message.parsed is None:
                        # Parse failed, try manual parsing with cleaning
                        logging.warning("OpenAI structured output parsing failed (parsed=None), trying manual parsing with cleaning")
                        raw_content = completion.choices[0].message.content
                        if raw_content:
                            json_response = json.loads(raw_content)
                            json_response = Utils._clean_llm_response(json_response, response_model)
                            return response_model.model_validate(json_response)
                        else:
                            raise ValueError("No content to parse")

                    return completion.choices[0].message.parsed

                except Exception as parse_error:
                    # If structured parsing fails entirely, try manual parsing
                    logging.warning(f"OpenAI structured output parsing failed with error: {parse_error}")
                    logging.warning("Attempting manual parsing with cleaning...")

                    try:
                        # Try to make a regular completion call to get raw content
                        regular_params = params.copy()
                        regular_params.pop('response_format', None)  # Remove structured output format

                        regular_completion = openai_client.chat.completions.create(**regular_params)
                        raw_content = regular_completion.choices[0].message.content

                        if raw_content:
                            import json
                            import re
                            # Try to extract JSON from the raw content
                            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                            if json_match:
                                json_response = json.loads(json_match.group())
                                json_response = Utils._clean_llm_response(json_response, response_model)
                                return response_model.model_validate(json_response)
                            else:
                                raise ValueError("No JSON found in raw content")
                        else:
                            raise ValueError("No content in regular completion")

                    except Exception as manual_error:
                        logging.error(f"Manual parsing also failed: {manual_error}")
                        raise parse_error  # Re-raise the original error
            elif "deepseek" in engine.lower() or "grok" in engine.lower(): # DeepSeek and Grok - use JSON format
                # Add JSON format instruction to the prompt
                json_instruction = f"\n\nPlease respond in valid JSON format according to this schema:\n{response_model.model_json_schema()}\n\nIMPORTANT: Return ONLY the JSON object, without any markdown formatting, code blocks, or ```json``` tags. Just the raw JSON."
                modified_messages = messages.copy()
                modified_messages[-1]["content"] += json_instruction

                # Smart timeout settings
                request_size = sum(len(str(msg)) for msg in modified_messages)
                if request_size > 5000:  # Large request
                    timeout_seconds = 180
                elif "grok" in engine.lower() or "deepseek" in engine.lower():  # Models prone to issues
                    timeout_seconds = 90
                else:
                    timeout_seconds = 60

                completion = openai_client.chat.completions.create(
                    model=engine,
                    messages=modified_messages,
                    temperature=temperature,
                    timeout=timeout_seconds,
                    response_format={"type": "json_object"}  # Use simple JSON format
                )

                # Parse the JSON response into the response model
                try:
                    import json
                    content = completion.choices[0].message.content.strip()

                    # Clean up markdown formatting if present
                    if content.startswith('```json'):
                        content = content[7:]  # Remove ```json
                    if content.endswith('```'):
                        content = content[:-3]  # Remove ```
                    content = content.strip()

                    json_response = json.loads(content)
                    json_response = Utils._clean_llm_response(json_response, response_model)
                    _record_model_success(engine)  # recordsuccessful
                    return response_model.model_validate(json_response)
                except (json.JSONDecodeError, ValueError) as e:
                    # Fallback: try to extract JSON from the response
                    content = completion.choices[0].message.content
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            json_response = json.loads(json_match.group())
                            json_response = Utils._clean_llm_response(json_response, response_model)
                            return response_model.model_validate(json_response)
                        except:
                            pass
                    raise ValueError(f"Failed to parse JSON response from {engine}: {content}")
            elif "gemini" in engine: # Gemini models - use JSON format instead of structured output
                # Add JSON format instruction to the prompt
                json_instruction = f"\n\nPlease respond in valid JSON format according to this schema:\n{response_model.model_json_schema()}\n\nIMPORTANT: Return ONLY the JSON object, without any markdown formatting, code blocks, or ```json``` tags. Just the raw JSON."
                modified_messages = messages.copy()
                modified_messages[-1]["content"] += json_instruction

                completion = openai_client.chat.completions.create(
                    model=engine,
                    messages=modified_messages,
                    temperature=temperature,
                    timeout=120,  # 120 seconds timeout for proxy services
                    response_format={"type": "json_object"}  # Use simple JSON format
                )

                # Parse the JSON response into the response model
                try:
                    import json
                    content = completion.choices[0].message.content.strip()
                    
                    # Clean up markdown formatting if present
                    if content.startswith('```json'):
                        content = content[7:]  # Remove ```json
                    if content.endswith('```'):
                        content = content[:-3]  # Remove ```
                    content = content.strip()
                    
                    # Remove any potential BOM or extra whitespace
                    content = content.replace('\ufeff', '').replace('\n', ' ').replace('\r', '')
                    
                    json_response = json.loads(content)
                    json_response = Utils._clean_llm_response(json_response, response_model)
                    _record_model_success(engine)  # recordsuccessful
                    return response_model.model_validate(json_response)
                except (json.JSONDecodeError, ValueError) as e:
                    # Enhanced fallback: try multiple cleanup strategies
                    content = completion.choices[0].message.content
                    import re
                    
                    # Strategy 1: Extract JSON object
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            cleaned_content = json_match.group().strip()
                            json_response = json.loads(cleaned_content)
                            json_response = Utils._clean_llm_response(json_response, response_model)
                            return response_model.model_validate(json_response)
                        except:
                            pass
                    
                    # Strategy 2: Try to fix common JSON issues including truncation
                    try:
                        # Fix trailing commas and other common issues
                        fixed_content = re.sub(r',\s*}', '}', content)
                        fixed_content = re.sub(r',\s*]', ']', fixed_content)
                        # Extract JSON from the fixed content
                        json_match = re.search(r'\{.*\}', fixed_content, re.DOTALL)
                        if json_match:
                            json_response = json.loads(json_match.group())
                            json_response = Utils._clean_llm_response(json_response, response_model)
                            return response_model.model_validate(json_response)
                    except:
                        pass
                    
                    # Strategy 3: Enhanced handling of truncated JSON
                    try:
                        # Look for truncated actions array
                        if '"actions"' in content and '[' in content:
                            # Extract the actions array part, even if truncated
                            actions_start = content.find('"actions":')
                            if actions_start != -1:
                                # Find the opening bracket of the actions array
                                bracket_start = content.find('[', actions_start)
                                if bracket_start != -1:
                                    # Extract everything after the opening bracket
                                    actions_content = content[bracket_start+1:]
                                    
                                    # Try to parse individual complete action objects
                                    action_objects = []
                                    current_pos = 0
                                    brace_count = 0
                                    current_action = ""
                                    in_string = False
                                    escape_next = False
                                    
                                    for char in actions_content:
                                        if escape_next:
                                            current_action += char
                                            escape_next = False
                                            continue
                                            
                                        if char == '\\':
                                            escape_next = True
                                            current_action += char
                                            continue
                                            
                                        if char == '"' and not escape_next:
                                            in_string = not in_string
                                            
                                        if not in_string:
                                            if char == '{':
                                                brace_count += 1
                                            elif char == '}':
                                                brace_count -= 1
                                                
                                        current_action += char
                                        
                                        # If we found a complete action object
                                        if brace_count == 0 and current_action.strip() and not in_string:
                                            try:
                                                # Clean and parse the action
                                                clean_action = current_action.strip().rstrip(',')
                                                if clean_action.startswith('{') and clean_action.endswith('}'):
                                                    action_obj = json.loads(clean_action)
                                                    action_objects.append(action_obj)
                                                current_action = ""
                                            except json.JSONDecodeError:
                                                # Skip this malformed action
                                                current_action = ""
                                            except Exception:
                                                current_action = ""
                                                
                                        # Stop if we hit array closing or truncation
                                        if not in_string and char == ']':
                                            break
                                    
                                    # If we successfully parsed at least one action, return it
                                    if action_objects:
                                        reconstructed = {"actions": action_objects}
                                        reconstructed = Utils._clean_llm_response(reconstructed, response_model)
                                        logging.info(f"Successfully reconstructed truncated JSON with {len(action_objects)} actions")
                                        return response_model.model_validate(reconstructed)
                                        
                    except Exception as reconstruction_error:
                        logging.debug(f"Enhanced JSON reconstruction failed: {reconstruction_error}")
                    
                    # Strategy 4: Simple truncation handling - extract complete actions only
                    try:
                        # Look for complete action objects using regex
                        if '"actions"' in content:
                            # Find all complete action objects (from { to matching })
                            action_pattern = r'\{"action":\s*"[^"]+"\s*(?:,\s*"[^"]+"\s*:\s*(?:"[^"]*"|[^,}\]]+))*\s*\}'
                            matches = re.findall(action_pattern, content, re.DOTALL)
                            
                            action_objects = []
                            for match in matches:
                                try:
                                    action_obj = json.loads(match)
                                    action_objects.append(action_obj)
                                except:
                                    continue
                                    
                            if action_objects:
                                reconstructed = {"actions": action_objects}
                                reconstructed = Utils._clean_llm_response(reconstructed, response_model)
                                logging.info(f"Regex-extracted {len(action_objects)} complete actions from truncated JSON")
                                try:
                                    return response_model.model_validate(reconstructed)
                                except Exception as validation_error:
                                    logging.error(f"Model validation failed for reconstructed JSON: {validation_error}")
                                    logging.error(f"Reconstructed data: {reconstructed}")
                                    # Continue to next strategy instead of failing completely
                                
                    except Exception as regex_error:
                        logging.debug(f"Regex JSON extraction failed: {regex_error}")
                    
                    # Strategy 5: Try to fix common JSON issues (original strategy)
                    try:
                        # Fix trailing commas and other common issues
                        fixed_content = re.sub(r',\s*}', '}', content)
                        fixed_content = re.sub(r',\s*]', ']', fixed_content)
                        # Extract JSON from the fixed content
                        json_match = re.search(r'\{.*\}', fixed_content, re.DOTALL)
                        if json_match:
                            json_response = json.loads(json_match.group())
                            json_response = Utils._clean_llm_response(json_response, response_model)
                            return response_model.model_validate(json_response)
                    except:
                        pass
                    
                    # If all strategies fail, provide better error message
                    logging.error(f"Failed to parse Gemini JSON. Content length: {len(content)}, First 200 chars: {content[:200]}")
                    raise ValueError(f"Failed to parse JSON response from Gemini: {content[:500]}...")
            else: # ollama (disabled at import to avoid SSL client init)
                raise RuntimeError(
                    "Ollama backend is disabled to avoid SSL client initialization errors. "
                    "Please use OpenAI-compatible models (gpt-*, gemini-*) or configure Ollama separately."
                )

        # Regular completion without response format - for Post generation
        else:
            if "gpt" in engine or "gemini" in engine or "deepseek" in engine.lower() or "grok" in engine.lower(): # OpenAI-compatible api
                completion = openai_client.chat.completions.create(
                    model=engine,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=120,  # 120 seconds timeout for proxy services
                    # frequency_penalty=1.6,
                    # presence_penalty=1.6
                )
                _record_model_success(engine)  # recordsuccessful
                return completion.choices[0].message.content
            else: # ollama (disabled at import to avoid SSL client init)
                raise RuntimeError(
                    "Ollama backend is disabled to avoid SSL client initialization errors. "
                    "Please use OpenAI-compatible models (gpt-*, gemini-*) or configure Ollama separately."
                )

    @staticmethod
    def generate_llm_response_with_fallback(
        engine: str,
        prompt: str,
        system_message: str,
        temperature: float,
        response_model: Optional[Type[BaseModel]] = None,
        max_tokens: int = 4096,
    ) -> Union[str, BaseModel]:
        """
        Generate an LLM response with automatic fallback to alternative models if one fails.
        """
        try:
            from src.multi_model_selector import multi_model_selector
        except ImportError:
            from multi_model_selector import multi_model_selector

        # Get the fallback model list with the current engine prioritized
        fallback_models = [engine] + [m for m in multi_model_selector.FALLBACK_PRIORITY if m != engine]

        last_error = None
        for attempt, model in enumerate(fallback_models):
            try:
                # Skip models that are marked unhealthy
                if not multi_model_selector.is_model_healthy(model):
                    continue

                # createclient
                client, selected_model = multi_model_selector.create_openai_client(model)

                # Call the original generate_llm_response helper
                result = Utils.generate_llm_response(
                    openai_client=client,
                    engine=selected_model,
                    prompt=prompt,
                    system_message=system_message,
                    temperature=temperature,
                    response_model=response_model,
                    max_tokens=max_tokens
                )

                # If we succeeded using a fallback engine, log it
                if attempt > 0:
                    logging.info(f"✅ Model fallback succeeded: {engine} -> {selected_model}")

                return result

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Mark the model as failed
                multi_model_selector.mark_model_failed(model)
                _record_model_failure(model)  # record failure count

                # Check for specific error classes
                if "502" in error_msg or "Bad Gateway" in error_msg:
                    logging.warning(f"⚠️ Model {model} encountered a 502 error; marking as failed and trying the next model...")
                elif "400" in error_msg and "content_filter" in error_msg.lower():
                    logging.warning(f"⚠️ Model {model} hit a content filter error; marking as failed and trying the next model...")
                elif "400" in error_msg:
                    logging.warning(f"⚠️ Model {model} hit a 400 error (likely a formatting issue); marking as failed and trying the next model...")
                elif "timeout" in error_msg.lower():
                    logging.warning(f"⚠️ Model {model} timed out; marking as failed and trying the next model...")
                else:
                    logging.warning(f"⚠️ Model {model} failed: {error_msg}")

                # If this was the last fallback model, raise the error
                if attempt == len(fallback_models) - 1:
                    logging.error(f"❌ All models failed; last error: {last_error}")
                    raise last_error

                continue

        # This point should never be reached
        raise Exception(f"All models failed; last error: {last_error}")

    @staticmethod
    def update_user_influence(conn, db_path=None):
        """Update influence scores for all users.
        
        Args:
            conn: Database connection object (sqlite3.Connection or ServiceConnection)
            db_path: Optional database path; ServiceConnection uses a default path if not provided
        """
        # Handle service mode connections: identify the real database path if necessary
        # Determine if conn is a ServiceConnection (service mode)
        conn_class_name = conn.__class__.__name__
        is_service_connection = conn_class_name == 'ServiceConnection'
        
        # For ServiceConnection we need a standard sqlite3 connection for pandas
        if is_service_connection:
            # If db_path was not provided, use the default path
            if not db_path:
                db_path = 'database/simulation.db'
            
            # Create a standard sqlite3 connection for pandas use
            actual_conn = sqlite3.connect(db_path, timeout=60.0)
            actual_conn.execute("PRAGMA journal_mode=WAL")
            actual_conn.execute("PRAGMA foreign_keys = ON")
            use_temp_conn = True
        else:
            actual_conn = conn
            use_temp_conn = False
        
        # Get user metrics into a DataFrame
        try:
            df = pd.read_sql_query('''
                SELECT
                    user_id,
                    follower_count,
                    total_likes_received,
                    total_shares_received,
                    total_comments_received
                FROM users
            ''', actual_conn)
        except (sqlite3.OperationalError, pd.errors.DatabaseError) as e:
            if use_temp_conn:
                actual_conn.close()
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in update_user_influence, skipping influence update")
                return
            else:
                raise e

        # Calculate normalized scores (handling division by zero)
        metrics = {
            'follower_count': 0.4,
            'total_likes_received': 0.3,
            'total_shares_received': 0.2,
            'total_comments_received': 0.1
        }

        influence_scores = pd.Series(0.0, index=df.index)

        for metric, weight in metrics.items():
            max_val = df[metric].max()
            if max_val > 0:  # Only normalize if we have non-zero values
                influence_scores += (df[metric] / max_val) * weight

        # Update the database with new scores
        df['influence_score'] = influence_scores
        df['is_influencer'] = influence_scores > 0.5

        # Update the database
        # If we used a temporary connection, close it before updating via the original connection
        if use_temp_conn:
            actual_conn.close()
            # Update using the original ServiceConnection
            from database.database_manager import execute_query
            for _, row in df.iterrows():
                execute_query('''
                    UPDATE users
                    SET influence_score = ?,
                        is_influencer = ?,
                        last_influence_update = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (round(float(row['influence_score']), 3), bool(row['is_influencer']), row['user_id']))
        else:
            # Using the standard connection
            for _, row in df.iterrows():
                actual_conn.execute('''
                    UPDATE users
                    SET influence_score = ?,
                        is_influencer = ?,
                        last_influence_update = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (round(float(row['influence_score']), 3), bool(row['is_influencer']), row['user_id']))
            actual_conn.commit()

        # Log influencer status changes
        influencers = df[df['is_influencer']][['user_id', 'influence_score']].sort_values('influence_score', ascending=False)

        if not influencers.empty:
            logging.info("\nCurrent Influencers:")
            for _, row in influencers.iterrows():
                logging.info(f"User {row['user_id']}: Influence Score = {row['influence_score']:.3f}")

    @staticmethod
    def evaluate_fact_checker_performance(conn: sqlite3.Connection):
        """
        Evaluate the performance of the fact checker on identifying fake news.
        Calculates accuracy, precision, recall, and F1 score.

        Args:
            conn: SQLite database connection
        """
        try:
            cursor = conn.cursor()

            # Get confusion matrix values
            cursor.execute('''
                SELECT
                    p.news_type,
                    fc.verdict,
                    COUNT(*) as count
                FROM posts p
                JOIN fact_checks fc ON p.post_id = fc.post_id
                GROUP BY p.news_type, fc.verdict
            ''')
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in evaluate_fact_checker_performance, skipping evaluation")
                return
            else:
                raise e

        # Initialize confusion matrix values
        true_positives = 0  # Correctly identified fake news
        false_positives = 0  # Real news incorrectly marked as fake
        false_negatives = 0  # Fake news incorrectly marked as real
        true_negatives = 0  # Correctly identified real news

        for news_type, verdict, count in cursor.fetchall():
            is_fake_verdict = verdict in ('false', 'misleading', 'unverified')

            if news_type == 'fake' and is_fake_verdict:
                true_positives += count
            elif news_type == 'fake' and not is_fake_verdict:
                false_negatives += count
            elif news_type == 'real' and is_fake_verdict:
                false_positives += count
            elif news_type == 'real' and not is_fake_verdict:
                true_negatives += count

        total_samples = true_positives + false_positives + false_negatives + true_negatives

        if total_samples > 0:
            # Calculate metrics
            accuracy = (true_positives + true_negatives) / total_samples if total_samples > 0 else 0

            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            print("\nFact Checker Performance Metrics:")
            print(f"Total posts fact-checked: {total_samples}")
            print("\nConfusion Matrix:")
            print(f"True Positives (Correct fake news detection): {true_positives}")
            print(f"False Positives (Real news marked as fake): {false_positives}")
            print(f"True Negatives (Correct real news detection): {true_negatives}")
            print(f"False Negatives (Missed fake news): {false_negatives}")
            print("\nMetrics:")
            print(f"Accuracy: {accuracy:.1%}")
            print(f"Precision: {precision:.1%}")
            print(f"Recall: {recall:.1%}")
            print(f"F1 Score: {f1:.1%}")
        else:
            print("\nNo posts have been fact-checked yet.")

    @staticmethod
    def print_simulation_stats(conn: sqlite3.Connection):
        """Print the simulation statistics."""
        try:
            cursor = conn.cursor()

            # Get total number of users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            # Get total number of posts
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]
            # Get total number of actions
            cursor.execute("SELECT COUNT(*) FROM user_actions")
            total_actions = cursor.fetchone()[0]
            # Get breakdown of action types
            cursor.execute("SELECT action_type, COUNT(*) FROM user_actions GROUP BY action_type")
            action_breakdown = cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in print_simulation_stats, using default values")
                total_users = 0
                total_posts = 0
                total_actions = 0
                action_breakdown = []
            else:
                raise e

        logging.info("Simulation Statistics:")
        logging.info(f"Total users: {total_users}")
        logging.info(f"Total posts: {total_posts}")
        logging.info(f"Total user actions: {total_actions}")
        logging.info("Action breakdown:")
        for action_type, count in action_breakdown:
            logging.info(f"  {action_type}: {count}")

        # Add community notes statistics
        try:
            cursor.execute('''
                SELECT
                    COUNT(*) as total_notes,
                    SUM(CASE WHEN helpful_ratings >= 3 AND helpful_ratings > not_helpful_ratings * 2
                        THEN 1 ELSE 0 END) as visible_notes,
                    AVG(helpful_ratings) as avg_helpful_ratings,
                    AVG(not_helpful_ratings) as avg_not_helpful_ratings
                FROM community_notes
            ''')
            note_stats = cursor.fetchone()
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in print_simulation_stats (community notes), using default values")
                note_stats = (0, 0, 0, 0)
            else:
                raise e

        print("\nCommunity Notes Statistics:")
        print(f"Total Number of Notes Created: {note_stats[0]}")
        print(f"Number of Visible Notes: {note_stats[1]}")
        print(f"Average Helpful Ratings: {note_stats[2]:.2f}" if note_stats[2] is not None else "N/A")
        print(f"Average Not Helpful Ratings: {note_stats[3]:.2f}" if note_stats[3] is not None else "N/A")

        # Add fact checker evaluation
        Utils.evaluate_fact_checker_performance(conn)

    @staticmethod
    def get_influence_stats(conn: sqlite3.Connection, user_id: str) -> dict:
        """
        Get the current influence statistics for a user.

        Args:
            conn: SQLite database connection
            user_id: The ID of the user to get stats for

        Returns:
            dict: Dictionary containing influence statistics, or None if user not found
        """
        cursor = conn.cursor()
        cursor.execute('''
            SELECT follower_count, total_likes_received,
                   total_shares_received, total_comments_received,
                   influence_score, is_influencer
            FROM users
            WHERE user_id = ?
        ''', (user_id,))

        stats = cursor.fetchone()
        if stats:
            return {
                'followers': stats[0],
                'total_likes': stats[1],
                'total_shares': stats[2],
                'total_comments': stats[3],
                'influence_score': stats[4],
                'is_influencer': stats[5]
            }
        return None

    @staticmethod
    def estimate_token_count(prompt: str) -> int:
        """
        Estimate the number of tokens in a string. This is a rough approximation.
        GPT models generally treat words, punctuation, and spaces as tokens.

        Args:
            prompt: The input string to estimate tokens for

        Returns:
            int: Estimated number of tokens
        """
        # Split into words
        words = prompt.split()

        # Count punctuation marks that are likely to be separate tokens
        punctuation_count = sum(1 for char in prompt if char in '.,!?;:()[]{}""\'')

        # Basic estimate: each word is roughly one token
        # Add punctuation count and some overhead for spaces and special characters
        estimated_tokens = len(words) + punctuation_count

        # Add 20% overhead for potential subword tokenization
        estimated_tokens = int(estimated_tokens * 1.2)

        return max(1, estimated_tokens)  # Ensure at least 1 token is returned


    @staticmethod
    def load_safety_prompts(file_path: str) -> Dict:
        """Loads the safety prompts database from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Safety prompts file not found at '{file_path}'")
            return {}
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from '{file_path}'")
            return {}

    @staticmethod
    def identify_topic(text: str, db: Dict) -> str:
        """Identifies the most relevant topic for a given text based on keywords."""
        text_lower = text.lower()
        topic_scores = {topic: 0 for topic in db}

        for topic, data in db.items():
            for keyword in data.get('keywords', []):
                if keyword.lower() in text_lower:
                    topic_scores[topic] += 1

        max_score = 0
        identified_topic = None
        for topic, score in topic_scores.items():
            if score > max_score:
                max_score = score
                identified_topic = topic

        return identified_topic

    @staticmethod
    def generate_prebunking_message(topic: str, db: Dict) -> str:
        """Generates a formatted pre-bunking message for a given topic."""
        prompt_data = db.get(topic, {}).get('prebunking_prompt')

        if not prompt_data:
            return "No pre-bunking information found for this topic."

        title = prompt_data.get('title', 'Important Information')
        content = prompt_data.get('content', '')
        questions = prompt_data.get('questions_to_ask', [])

        message = f"\n--- {title} ---\n\n"
        message += f"{content}\n\n"

        if questions:
            message += "🤔 Questions to consider:\n"
            for q in questions:
                message += f"  - {q}\n"

        return message
