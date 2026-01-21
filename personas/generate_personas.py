"""
We use the agent_bank.jsonl to generate personas.
"""

import json
import random
from typing import List, Dict
import numpy as np
import uuid
import sys
import os
from tqdm import tqdm
# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import Utils
from src.keys import OPENAI_API_KEY, OPENAI_BASE_URL
from openai import OpenAI

openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

def load_question_bank(filepath: str) -> List[Dict]:
    questions = []
    with open(filepath, 'r') as f:
        for line in f:
            questions.append(json.loads(line))
    return questions

def get_age() -> str:
    """
    Generate age based on a normal distribution centered around 35 years.
    Returns age as a string between 18-60.
    """
    age = int(np.random.normal(35, 12))
    age = max(18, min(60, age))  # Clamp between 18 and 60
    return str(age)

def get_gender() -> str:
    """
    Generate gender with approximate real-world distribution.
    Returns gender as a string.
    """
    return np.random.choice(
        ["Male", "Female", "Non-binary", "Prefer not to say", "Other"],
        p=[0.48, 0.48, 0.02, 0.01, 0.01]
    )

def get_primary_language(ethnicity: str) -> str:
    """
    Determine primary language based on ethnicity with probabilistic distribution.
    """
    language_mappings = {
        "White/Caucasian": {
            "English": 0.85,
            "Spanish": 0.05,
            "French": 0.05,
            "German": 0.05,
        },
        "Hispanic/Latino": {
            "Spanish": 0.70,
            "English": 0.25,
            "Portuguese": 0.05,
        },
        "Asian": {
            "Mandarin Chinese": 0.25,
            "English": 0.20,
            "Korean": 0.15,
            "Japanese": 0.15,
            "Vietnamese": 0.15,
            "Hindi": 0.10,
        },
        "African American": {
            "English": 0.95,
            "French": 0.05,
        },
        "Middle Eastern": {
            "Arabic": 0.50,
            "English": 0.20,
            "Farsi": 0.15,
            "Turkish": 0.15,
        }
    }
    
    # Get probability distribution for the given ethnicity
    distribution = language_mappings.get(ethnicity, {"English": 0.95, "French": 0.05})
    
    # Get languages and their probabilities
    languages = list(distribution.keys())
    probabilities = list(distribution.values())
    
    return np.random.choice(languages, p=probabilities)

def generate_persona_hardcoded(questions: List[Dict]) -> tuple[str, Dict]:
    """Generate a natural language description of a persona and a dict of labels with answers."""
    # Create answers dict and labels dict
    answers = {q['qid']: random.choice(q['options']) for q in questions}
    labels = {q['question_label']: answers[q['qid']] for q in questions}
    
    # Override age and gender with our distribution-based generators
    age = get_age()
    gender = get_gender()
    answers['Q1'] = age
    answers['Q2'] = gender
    labels['age'] = age
    labels['gender'] = gender
    
    # Set ethnicity first, then determine primary language
    ethnicity = answers['Q29']
    primary_language = get_primary_language(ethnicity)
    answers['Q30'] = primary_language
    labels['ethnicity'] = ethnicity
    labels['primary_language'] = primary_language
    
    # Generate description for all questions in order
    description = f"You are a {answers['Q1']} year old {answers['Q2'].lower()} who grew up in a {answers['Q3'].lower()} area. "
    description += f"You spend most of your time on {answers['Q4'].lower()}. "
    description += f"The value most important to you is {answers['Q5'].lower()}. "
    description += f"Your closest friend or family member is {answers['Q6'].lower()}. "
    description += f"In unfamiliar social contexts, you are typically {answers['Q7'].lower()}. "
    description += f"With infinite money, you would spend most time {answers['Q8'].lower()}. "
    description += f"Your favorite hobby is {answers['Q9'].lower()}. "
    description += f"Your political affiliation is {answers['Q10'].lower()}. "
    description += f"You have lived in {answers['Q11'].lower()} places. "
    description += f"In social relationships, {answers['Q12'].lower()} is most important to you. "
    description += f"Your childhood was {answers['Q13'].lower()}. "
    description += f"Your MBTI type is {answers['Q14']}. "
    description += f"Your primary goal for the next 5 years is {answers['Q15'].lower()}. "
    description += f"You fear {answers['Q16'].lower()} the most. "
    description += f"You {answers['Q17'].lower()} experienced childhood trauma that affects you today. "
    description += f"You {answers['Q18'].lower()} experience intrusive thoughts. "
    description += f"One of the most meaningful events in your life was {answers['Q19'].lower()}. "
    description += f"You {answers['Q20'].lower()} experienced tension growing up between different cultural norms. "
    description += f"When solving difficult situations, your primary approach is {answers['Q21'].lower()}. "
    description += f"You are {answers['Q22'].lower()} regarding religious or spiritual beliefs. "
    description += f"Your most prized possession is your {answers['Q23'].lower()}. "
    description += f"Your biggest career aspiration is {answers['Q24'].lower()}. "
    description += f"When solving difficult situations, you prefer {answers['Q25'].lower()}. "
    description += f"The trait you value most in friends is {answers['Q26'].lower()}. "
    description += f"With $100, you would {answers['Q27'].lower()}. "
    description += f"Your household income level is {answers['Q28'].lower()}. "
    description += f"You identify your ethnicity as {answers['Q29']}. "
    description += f"Your primary language spoken at home is {answers['Q30']}. "
    
    return description, labels


def generate_persona_description(questions: List[Dict]) -> tuple[str, Dict]:
    """
    Generate a natural language description of a persona and a dict of labels with answers.
    In this version, we use GPT-4o to generate the description.
    """
    # Create answers dict and labels dict
    answers = {q['qid']: random.choice(q['options']) for q in questions}
    labels = {q['question_label']: answers[q['qid']] for q in questions}
    
    # Override age and gender with our distribution-based generators
    age = get_age()
    gender = get_gender()
    answers['Q1'] = age
    answers['Q2'] = gender
    labels['age'] = age
    labels['gender'] = gender
    
    # Set ethnicity first, then determine primary language
    ethnicity = answers['Q22']
    primary_language = get_primary_language(ethnicity)
    answers['Q23'] = primary_language
    labels['ethnicity'] = ethnicity
    labels['primary_language'] = primary_language
    
    # Generate description for all questions in order
    system_prompt = """
    You are a helpful assistant generate creative and diverse descriptions based on the attributes provided. 
    Make sure to include all information but make the description creative and diverse.
    """

    prompt = f"""
    Go through the following list of attributes and generate a natural language description of a persona.
    Use second person perspective, and make it sound like a background story of a person.
    YOU MUST STILL INCLUDE EVERY ATTRIBUTE IN THE DICTIONARY. DO NOT SKIP ANY CONTENT. THIS IS NON-NEGOTIABLE. 
    The output should be a single coherent paragraph, not a list of bullet points.
    {labels}
    """

    response = Utils.generate_llm_response(
        openai_client=openai_client,
        engine="gpt-4o",
        prompt=prompt,
        system_message=system_prompt,
        response_model=None,
        temperature=0.8,
        # max_tokens=8192,
    )
    
    return response, labels
    
    
    
def generate_personas(num_personas: int, output_file: str):
    questions = load_question_bank('agent_bank_new.jsonl')
    
    with open(output_file, 'w') as f:
        for _ in tqdm(range(num_personas)):
            persona_description, labels = generate_persona_description(questions)
            persona_id = str(uuid.uuid4())
            
            # Combine all fields into one dictionary
            output = {
                "id": persona_id,
                "persona": persona_description,
                **labels  # This unpacks all the labels and their values into the main dictionary
            }
            
            f.write(json.dumps(output) + '\n')

if __name__ == "__main__":
    generate_personas(200, output_file="generated_personas_with_gpt4o_new.jsonl")

