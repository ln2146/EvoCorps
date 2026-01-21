#!/usr/bin/env python3
"""
Quick launcher for the opinion balance system.
"""

import sys
import os
import asyncio

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from opinion_balance_launcher import OpinionBalanceLauncher

async def main():
    """Quickly launch the opinion balance system."""
    print("🚀 Quickly launching the opinion balance system...")
    
    launcher = OpinionBalanceLauncher()
    
    if launcher.initialize_system():
        print("✅ System initialized successfully, starting monitoring...")
        await launcher.start_monitoring()
    else:
        print("❌ System initialization failed")

if __name__ == "__main__":
    asyncio.run(main())
