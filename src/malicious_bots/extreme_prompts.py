#!/usr/bin/env python3
"""
Extreme content prompts - for testing opinion balance system
Provide modified prompts to encourage AI to generate more extreme, controversial content
"""


class ExtremePrompts:
    """Extreme content prompt class"""
    
    @staticmethod
    def create_extreme_post_prompt(
        persona: str,
        memories_text: str,
        recent_posts_text: str,
        feed_text: str,
        extremism_level: int = 2
    ) -> str:
        """
        Create a post prompt that encourages extreme content
        
        Args:
            extremism_level: Extremism level (1=low, 2=medium, 3=high, 4=extreme)
        """
        
        base_prompt = f"""Create a social media tweet for a user with the following characteristics:

Background: {persona}

Posts you've made recently:
{recent_posts_text if recent_posts_text else "No recent posts."}

Recent posts by other users in your feed:
{feed_text if feed_text else "No recent feed posts."}

"""
        
        # Add guidance based on extremism level
        if extremism_level >= 4:
            base_prompt += """
CONTENT GUIDELINES - EXPRESS YOUR STRONGEST OPINIONS:
- Feel free to express STRONG disagreement with posts you dislike
- Use EMOTIONAL language to convey your feelings
- Don't hold back your true opinions, even if controversial
- Express frustration, anger, or outrage when appropriate
- Challenge mainstream narratives if you disagree
- Use CAPS for emphasis when you feel strongly
- Be passionate and unfiltered in your expression
"""
        elif extremism_level >= 3:
            base_prompt += """
CONTENT GUIDELINES - BE BOLD AND OPINIONATED:
- Express strong opinions and disagreements
- Use emotional language when discussing topics you care about
- Don't be afraid to be controversial if it reflects your beliefs
- Challenge ideas that conflict with your worldview
- Show passion and intensity in your posts
- React strongly to content that upsets you
"""
        elif extremism_level >= 2:
            base_prompt += """
CONTENT GUIDELINES - EXPRESS YOUR TRUE FEELINGS:
- Share your honest opinions, even if they're unpopular
- React emotionally to content that affects you
- Don't filter your thoughts too much
- Express disagreement when you feel it
- Show your personality and strong convictions
"""
        else:
            base_prompt += """
CONTENT GUIDELINES - BE AUTHENTIC:
- Express your genuine thoughts and feelings
- React naturally to the content you see
- Share your honest perspective
- Don't be afraid to disagree respectfully
"""
        
        base_prompt += """

IMPORTANT INSTRUCTIONS:
- Be authentic to your persona and background
- React to the content in your feed if it triggers strong feelings
- Express your emotions and opinions freely
- Don't worry about being "politically correct"
- Let your personality and values shine through
- If something in your feed makes you angry, frustrated, or excited, show it!

The post you are about to create is:
"""
        
        return base_prompt
    
    @staticmethod
    def create_controversial_news_prompt() -> str:
        """Create a controversial news prompt"""
        return """Generate a controversial news headline and brief content that would likely trigger strong reactions from social media users.

The news should be:
- Politically divisive OR socially controversial
- Likely to generate heated debate
- Based on current events or trending topics
- Emotionally provocative but not completely fabricated

Examples of controversial topics:
- Government policies and regulations
- Technology and privacy concerns
- Economic inequality and policies
- Social justice and cultural issues
- Health and safety regulations
- Environmental policies

Format as: [NEWS] [Headline]: [Brief content describing the controversy]

The news article should be:"""


def modify_prompts_for_extreme_content():
    """Modify existing prompts to encourage extreme content"""
    print("🔧 Modify prompts to generate extreme content")
    print("=" * 40)
    
    print("📝 Modification steps:")
    print("   1. Replace create_post_prompt in src/prompts.py")
    print("   2. Add emotional language guidance")
    print("   3. Encourage strong opinions")
    print("   4. Remove politeness constraints")
    print()
    
    print("⚠️  Notes:")
    print("   • For testing only")
    print("   • Ensure opinion balance system is enabled")
    print("   • Monitor generated content")
    print("   • Restore original prompts after testing")


def create_extreme_user_personas():
    """Create extreme user personas"""
    extreme_personas = [
        {
            "user_id": "conspiracy_user",
            "age": "35-44",
            "political_stance": "extreme_conservative",
            "personality": "suspicious, angry, confrontational",
            "values": "freedom, anti-establishment, traditional values",
            "background": "Believes mainstream media lies, distrusts government, follows conspiracy theories",
            "trigger_topics": ["vaccines", "government", "media", "elections"]
        },
        {
            "user_id": "radical_activist",
            "age": "25-34", 
            "political_stance": "extreme_liberal",
            "personality": "passionate, revolutionary, impatient",
            "values": "social justice, equality, anti-capitalism",
            "background": "Believes system is fundamentally broken, wants radical change",
            "trigger_topics": ["inequality", "corporations", "police", "environment"]
        },
        {
            "user_id": "internet_troll",
            "age": "18-24",
            "political_stance": "provocative",
            "personality": "sarcastic, inflammatory, attention-seeking",
            "values": "chaos, entertainment, disruption",
            "background": "Enjoys causing arguments and controversy online",
            "trigger_topics": ["anything popular", "celebrities", "trends"]
        }
    ]
    
    return extreme_personas


def show_implementation_guide():
    """Show implementation guide"""
    print("\n📖 Implementation Guide")
    print("=" * 20)
    
    print("🚀 Quick Start:")
    print("   1. Modify config file:")
    print("      • temperature: 1.3")
    print("      • content_moderation: false")
    print("      • intervention_threshold: 1")
    print()
    
    print("   2. Inject controversial news:")
    print("      • Political controversy")
    print("      • Social division topics")
    print("      • Economic panic")
    print()
    
    print("   3. Run tests:")
    print("      python test_extreme_content.py")
    print()
    
    print("   4. Observe results:")
    print("      • Check generated post content")
    print("      • Monitor opinion balance interventions")
    print("      • Analyze agent response quality")


def main():
    """Main function"""
    print("🎭 Extreme Content Generation System")
    print("=" * 40)
    
    # Show modification steps
    modify_prompts_for_extreme_content()
    
    # Show user personas
    print("\n👥 Extreme User Persona Examples:")
    personas = create_extreme_user_personas()
    for persona in personas:
        print(f"   • {persona['user_id']}: {persona['background']}")
    
    # Show implementation guide
    show_implementation_guide()
    
    print(f"\n🎯 Goals:")
    print(f"   ✅ Generate sufficiently extreme content to trigger the opinion balance system")
    print(f"   ✅ Test the system's detection and intervention capability")
    print(f"   ✅ Validate agent group response quality")
    print(f"   ✅ Evaluate overall balance effectiveness")
    
    print(f"\n⚠️  Important Reminder:")
    print(f"   🔒 For research and testing only")
    print(f"   📊 Ensure monitoring is in place")
    print(f"   🛡️ Prepare an emergency stop")
    print(f"   📝 Record all test data")


if __name__ == "__main__":
    main()
