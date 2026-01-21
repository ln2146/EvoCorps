"""
Network configuration module that addresses Wikipedia API SSL connectivity issues.
"""

import ssl
import socket
import urllib3
from urllib3.util.ssl_ import create_urllib3_context
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def configure_ssl_context():
    """Configure the SSL context to mitigate connection problems."""
    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Create a custom SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    # Relax SSL cipher requirements
    context.set_ciphers('DEFAULT@SECLEVEL=1')
    
    return context


def create_robust_session():
    """Create a robust requests session with retry support."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set timeout
    session.timeout = 30
    
    return session


def test_wikipedia_connection():
    """Test the Wikipedia API connection."""
    try:
        import wikipediaapi
        
        print("🔍 Testing Wikipedia API connection...")
        
        # Ensure SSL is configured
        configure_ssl_context()
        
        # Initialize the Wikipedia client
        wiki = wikipediaapi.Wikipedia(
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='EnhancedEvidenceDatabase/1.0 (https://example.com/contact)',
            timeout=30
        )
        
        # Run a simple test query
        test_page = wiki.page("Python")
        
        if test_page.exists():
            print("✅ Wikipedia API connection succeeded")
            print(f"   Test page: {test_page.title}")
            print(f"   Page length: {len(test_page.text)} characters")
            return True
        else:
            print("❌ Wikipedia API connection failed: test page missing")
            return False
            
    except Exception as e:
        print(f"❌ Wikipedia API connection test failed: {e}")
        return False


def configure_network_for_wikipedia():
    """Configure the network environment for accessing the Wikipedia API."""
    try:
        # Configure SSL
        configure_ssl_context()
        
        # Set socket options
        socket.setdefaulttimeout(30)
        
        print("✅ Network setup complete")
        return True
        
    except Exception as e:
        print(f"❌ Network setup failed: {e}")
        return False


if __name__ == "__main__":
    # Test network configuration
    configure_network_for_wikipedia()
    test_wikipedia_connection()
