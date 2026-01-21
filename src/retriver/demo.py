import wikipediaapi
import re

def find_arguments_for_claim(claim, find_pro_arguments=True, language='en'):
    """
    Attempts to find arguments for a given claim from Wikipedia.

    Args:
        claim (str): Your claim, e.g., "I support AI" or "We should ban animal testing".
        find_pro_arguments (bool): True to find supporting arguments, False for opposing arguments.
        language (str): The language code for Wikipedia, default is 'en' for English.
    """
    
    print(f"--- Starting search for arguments for the claim: '{claim}' ---")

    # 1. Identify the core topic (simplified implementation)
    # Simple rule: remove prefixes like "I support", "I oppose", "we should", etc.
    # More advanced NLP techniques would be needed for complex claims.
    topic = re.sub(r'^(i support|i oppose|we should|i believe|ban|support|promote)\s+', '', claim, flags=re.IGNORECASE).strip()
    if not topic:
        print("Error: Could not identify a core topic from the claim.")
        return

    print(f"Identified core topic: '{topic}'")

    # 2. Initialize the Wikipedia API
    headers = {
        'User-Agent': 'ArgumentFinder/1.0 (https://example.com/bot; bot@example.com)'
    }
    wiki_api = wikipediaapi.Wikipedia(language, headers=headers)
    page = wiki_api.page(topic)

    if not page.exists():
        print(f"Error: Could not find a Wikipedia page for '{topic}'.")
        return

    print(f"Successfully found page: {page.title} ({page.fullurl})")

    # 3. Define keywords for finding argument sections
    if find_pro_arguments:
        print("\nSearching for Supporting Arguments (Pro)...")
        keywords = ['applications', 'advantages', 'benefits', 'positive aspects', 'merits', 'uses', 'impact']
    else:
        print("\nSearching for Opposing Arguments (Con)...")
        keywords = ['controversy', 'risks', 'criticism', 'disadvantages', 'issues', 'ethics', 'negative aspects', 'concerns']

    found_arguments = []

    # 4. Recursively traverse all sections and subsections to find matching titles
    def find_sections_recursive(sections):
        for s in sections:
            # Check if the section title contains any of the keywords
            if any(keyword in s.title.lower() for keyword in keywords):
                # Filter out sections with very little text
                if len(s.text) > 100:
                    found_arguments.append({'title': s.title, 'text': s.text})
            
            # Recurse into subsections
            if s.sections:
                find_sections_recursive(s.sections)

    find_sections_recursive(page.sections)

    # 5. Print the results
    if not found_arguments:
        print("\n--- No relevant argument sections were found ---")
        print("This might be because the Wikipedia page's section titles do not contain the predefined keywords.")
    else:
        print(f"\n--- Found {len(found_arguments)} potential argument sections ---")
        for i, arg in enumerate(found_arguments, 1):
            print(f"\n{i}. Section Title: {arg['title']}")
            # Display the first 300 characters of the section as a preview
            print(f"   Content Preview: {arg['text'][:300].strip()}...")

# --- EXAMPLE USAGE ---

# Example 1: Find supporting arguments for "Artificial Intelligence"
claim_pro_ai = "I support Artificial Intelligence"
find_arguments_for_claim(claim_pro_ai, find_pro_arguments=True) # language='en' is now the default

print("\n" + "="*50 + "\n")

# Example 2: Find opposing arguments for the "death penalty"
claim_con_death_penalty = "I oppose the death penalty"
find_arguments_for_claim(claim_con_death_penalty, find_pro_arguments=False)

print("\n" + "="*50 + "\n")

# Example 3: Find supporting arguments for "Genetically modified food"
claim_pro_gmf = "promote Genetically modified food"
find_arguments_for_claim(claim_pro_gmf, find_pro_arguments=True)