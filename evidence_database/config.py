# Evidence Database configuration file

## API configuration
import os
import sys

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from keys import OPENAI_BASE_URL as API_BASE_URL, OPENAI_API_KEY as API_KEY
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
VIEWPOINT_SIMILARITY_THRESHOLD = 0.7

## Wikipedia search configuration
MAX_WIKIPEDIA_RESULTS = 15
MAX_EVIDENCE_PER_VIEWPOINT = 5
MIN_EVIDENCE_ACCEPTANCE_RATE = 0.5
FALLBACK_EVIDENCE_COUNT = 3

## Database configuration
DEFAULT_DB_PATH = "opinion_database.db"

## Wikipedia MediaWiki API configuration（V2 升级新增）
WIKIPEDIA_MEDIAWIKI_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_MAX_PAGES_PER_QUERY = 5       # 每条 query search 返回的候选页面数
WIKIPEDIA_MAX_QUERIES = 6               # 最多使用的 queries 条数
WIKIPEDIA_PARA_MIN_LENGTH = 20         # 段落最小字符数（低于此值丢弃）
WIKIPEDIA_PARA_MAX_LENGTH = 1000        # 段落最大字符数（超过此值丢弃）
WIKIPEDIA_PARA_SIM_THRESHOLD = 0.25     # 段落 embedding 与观点相似度阈值（调参入口）
WIKIPEDIA_REQUEST_TIMEOUT = (5, 15)     # (connect_timeout, read_timeout) 秒
WIKIPEDIA_INTER_QUERY_DELAY = 0.2       # 每条 query 请求后的节流间隔（秒）
