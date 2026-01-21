# Evidence Database configuration file

## API configuration
API_BASE_URL = "BASE_URL"
API_KEY = "YOUR_API_KEY"
API_MODEL_NAME = "gemini-2.0-flash"

## 14 topic categories
TOPICS = [
    "Society & Ethics",
    "Politics & Governance", 
    "Technology & Future",
    "Economy & Business",
    "Environment & Energy",
    "Science & Health",
    "Education & Humanities",
    "Arts & Culture",
    "Philosophy & Religion",
    "Breaking News & Current Events",
    "Pop Culture & Entertainment", 
    "Daily Life & Hobbies",
    "Internet Memes & Trends",
    "Products & Consumption"
]

## Similarity threshold configuration
KEYWORD_SIMILARITY_THRESHOLD = 0.7
VIEWPOINT_SIMILARITY_THRESHOLD = 0.8

## Wikipedia search configuration
MAX_WIKIPEDIA_RESULTS = 15
MAX_EVIDENCE_PER_VIEWPOINT = 5

## Database configuration
DEFAULT_DB_PATH = "opinion_database.db"
