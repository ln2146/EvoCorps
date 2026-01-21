#!/usr/bin/env python3
"""
Start the database service
"""

import sys
import os
import time

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_service import start_database_service

def main():
    """Start the database service"""
    print("🚀 Starting the database service...")
    
    # Start the database service
    service = start_database_service()
    
    try:
        print("📊 Database service running... press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping the database service...")
        service.cleanup()

if __name__ == "__main__":
    main()
