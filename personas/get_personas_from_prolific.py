import json
from typing import Dict, List

def read_jsonl(filepath: str) -> List[Dict]:
    """Read JSONL file and return list of dictionaries."""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def generate_persona_from_prolific(person: Dict) -> str:
    """Generate a natural language description from Prolific data."""
    description = f"You are a {person['age']} year old {person['gender'].lower()} who grew up in a {person['type_of_residence'].lower()} area. "
    description += f"You have lived in {person['num_places_lived']} places. "
    description += f"You spend most of your time on {person['favorite_activities'].lower()}. "
    description += f"The value most important to you is {person['important_values'].lower()}. "
    description += f"Your political stance is {person['political_stance'].lower()}. "
    description += f"Your household income level is {person['income']}. "
    description += f"You identify your ethnicity as {person['ethnic_group']}. "
    description += f"Your primary language is {person['primary_language']}. "
    description += f"Your education level is {person['education']}. "
    description += f"Your religious belief is {person['religion']}. "
    description += f"In unfamiliar social contexts, you are typically {person['social_tendency'].lower()}. "
    description += f"Your favorite hobby is {person['hobby'].lower()}. "
    description += f"In social relationships, {person['social_relationship_values'].lower()} is most important to you. "
    description += f"Your personality is {person['personality'].lower()}. "
    description += f"Your primary goal for the next few years is {person['primary_goal'].lower()}. "
    description += f"One of the most meaningful events in your life was {person['meaningful_events'].lower()}. "
    description += f"The trait you value most in friends is being {person['values_in_friends'].lower()}. "
    description += f"With $100, you would {person['what_to_do_with_100_dollars'].lower()}. "
    
    return description

def process_prolific_data(input_file: str, output_file: str):
    """Read Prolific data and write formatted personas to file."""
    # Read JSONL data
    personas = read_jsonl(input_file)
    
    # Process each persona and write to output file
    with open(output_file, 'w') as f:
        for person in personas:
            # Generate the persona description
            description = generate_persona_from_prolific(person)
            
            # Create a new dictionary with all original attributes plus the generated description
            output_data = person.copy()  # Keep all original attributes
            output_data["persona"] = description  # Add the generated persona
            
            # Write the complete data as JSON line
            f.write(json.dumps(output_data) + '\n')

if __name__ == "__main__":
    input_file = "personas/personas_from_prolific.jsonl"
    output_file = "personas/personas_from_prolific_description.jsonl"
    process_prolific_data(input_file, output_file)
