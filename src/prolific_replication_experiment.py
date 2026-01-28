import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel

from agent_user import AgentUser, FeedAction, FeedReaction
from utils import Utils
from prompts import AgentPrompts
from database_manager import DatabaseManager
from user_manager import UserManager


class ProlificReplicationExperiment:
    """
    An experiment that shows a pre-defined feed prompt to agents and records their reactions.
    """
    
    def __init__(self, config_path: str = "configs/experiment_config.json"):
        """
        Initialize the experiment.
        
        Args:
            config_path: Path to the experiment configuration file.
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Generate timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Initialize database manager
        self.db_manager = DatabaseManager('database/simulation.db', reset_db=True) # we need to reset the database for each run
        self.conn = self.db_manager.get_connection()
        
        # Initialize user manager to create agents from persona config file
        self.user_manager = UserManager(self.config, self.db_manager)
        self.users = self.user_manager.users  # This will load agents from the persona config file
        
        # Initialize OpenAI client
        from multi_model_selector import multi_model_selector
        if self.config['engine'].startswith("gpt") or self.config['engine'].startswith("gemini"):
            # Unified model selection via MultiModelSelector (experiment role)
            self.openai_client, _ = multi_model_selector.create_openai_client(role="experiment")
        else:
            # Unified model selection via MultiModelSelector with custom base_url (experiment role)
            self.openai_client, _ = multi_model_selector.create_openai_client_with_base_url(
                base_url="http://localhost:11434/v1",
                api_key="ollama",
                role="experiment",
            )
        
        # Create experiment output directory
        self.output_dir = f"experiment_outputs/prolific_replication/{self.timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save configuration
        with open(f"{self.output_dir}/config.json", 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def run_experiment_with_agents(self, agents: List[AgentUser], feed_content: str) -> Dict[str, Any]:
        """
        Run the experiment with the given agents and feed content.
        
        Args:
            agents: List of AgentUser objects to run the experiment with.
            feed_content: The feed content string.
            
        Returns:
            A dictionary containing the experiment results.
        """
        # Record all reactions
        all_reactions = {}
        
        # Have each agent react to the feed
        for agent in agents:
            user_id = agent.user_id
            logging.info(f"Agent {user_id} is reacting to the feed...")
            
            # Record the start time
            start_time = time.time()
            
            # Create a custom feed reaction prompt
            prompt = self._create_custom_feed_reaction_prompt(agent.persona, feed_content)
            
            # Get the system prompt
            system_prompt = AgentPrompts.get_system_prompt()
            
            # Determine if reasoning should be included
            include_reasoning = self.config.get('experiment', {}).get('settings', {}).get('include_reasoning', False)
            
            # Create the appropriate response model based on whether reasoning is included
            if include_reasoning:
                # Define FeedActionWithReasoning class dynamically
                class FeedActionWithReasoning(BaseModel):
                    action: str
                    target: Optional[str] = None
                    content: Optional[str] = None
                    reasoning: Optional[str] = None
                    note_rating: Optional[str] = None
                
                class FeedReactionWithReasoning(BaseModel):
                    actions: List[FeedActionWithReasoning]
                
                response_model = FeedReactionWithReasoning
            else:
                response_model = FeedReaction
            
            # Generate the reaction using the LLM
            reaction = Utils.generate_llm_response(
                openai_client=self.openai_client,
                engine=self.config['engine'],
                prompt=prompt,
                system_message=system_prompt,
                temperature=agent.temperature,
                response_model=response_model,
            )
            
            # Record the actions directly to the database
            self._record_actions_to_database(user_id, reaction, include_reasoning)
            
            # Record the end time and calculate duration
            end_time = time.time()
            duration = end_time - start_time
            
            # Get the agent's actions from the database
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT action_type, target_id, content, reasoning
                FROM user_actions
                WHERE user_id = ? AND created_at > datetime('now', '-1 minute')
                ORDER BY created_at DESC
            ''', (user_id,))
            
            actions = []
            for row in cursor.fetchall():
                action_type, target_id, content, reasoning = row
                action = {
                    'action': action_type.replace('_', '-'),
                    'target': target_id,
                    'content': content,
                }
                if reasoning:
                    action['reasoning'] = reasoning
                actions.append(action)
            
            # Record the agent's reactions
            all_reactions[user_id] = {
                'actions': actions,
                'duration': duration,
                'persona': agent.persona
            }
            
            # Add a small delay between agents to avoid rate limiting
            time.sleep(0.5)
        
        # Save the results to a JSON file
        results_path = f"{self.output_dir}/reactions.json"
        with open(results_path, 'w') as f:
            json.dump(all_reactions, f, indent=4)
        
        logging.info(f"Saved experiment results to {results_path}")
        
        return all_reactions
    
    def _record_actions_to_database(self, user_id: str, reaction, include_reasoning: bool) -> None:
        """
        Record the agent's actions to the database.
        
        Args:
            user_id: The agent's user ID.
            reaction: The reaction object from the LLM.
            include_reasoning: Whether to include reasoning in the database.
        """
        for action_data in reaction.actions:
            action = action_data.action
            target = action_data.target
            content = action_data.content
            action_reasoning = getattr(action_data, 'reasoning', None) if include_reasoning else None
            
            try:
                # Execute action
                time.sleep(0.1)  # Small delay
                
                if action == 'comment-post' or action == 'add-note':
                    if include_reasoning and action_reasoning:
                        self.conn.execute('''
                            INSERT INTO user_actions (user_id, action_type, target_id, content, reasoning)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (user_id, action.replace('-', '_'), target, content, action_reasoning))
                    else:
                        self.conn.execute('''
                            INSERT INTO user_actions (user_id, action_type, target_id, content)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, action.replace('-', '_'), target, content))
                elif action == 'ignore':
                    if include_reasoning and action_reasoning:
                        self.conn.execute('''
                            INSERT INTO user_actions (user_id, action_type, reasoning)
                            VALUES (?, 'ignore', ?)
                        ''', (user_id, action_reasoning))
                    else:
                        self.conn.execute('''
                            INSERT INTO user_actions (user_id, action_type)
                            VALUES (?, 'ignore')
                        ''', (user_id,))
                else:
                    if include_reasoning and action_reasoning:
                        self.conn.execute('''
                            INSERT INTO user_actions (user_id, action_type, target_id, reasoning)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, action.replace('-', '_'), target, action_reasoning))
                    else:
                        self.conn.execute('''
                            INSERT INTO user_actions (user_id, action_type, target_id)
                            VALUES (?, ?, ?)
                        ''', (user_id, action.replace('-', '_'), target))
                
                self.conn.commit()
                logging.info(f"Recorded action: {user_id} {action} {target}")
                
            except Exception as e:
                logging.error(f"Error recording action {action}: {e}")
    
    def _create_custom_feed_reaction_prompt(self, persona: str, feed_content: str) -> str:
        """
        Create a custom prompt for the agent to react to the feed.
        
        Args:
            persona: The agent's persona.
            feed_content: The feed content string.
            
        Returns:
            The prompt string.
        """
        # Get the experiment type
        experiment_type = self.config.get('experiment', {}).get('type', 'third_party_fact_checking')
        
        # Get whether to include reasoning
        include_reasoning = self.config.get('experiment', {}).get('settings', {}).get('include_reasoning', False)
        
        prompt = f"""You are browsing your social media feed as a user with this background:
{persona}

Here is a hypothetical social media feed. Read each post carefully and then decide how to interact with it.

Your feed:
--------------------------------
{feed_content}
--------------------------------

Based on your persona and the content you see, choose how to interact with the feed.
"""

        # Add experiment-specific instructions and valid actions
        if experiment_type == "no_fact_checking":
            prompt += """
Valid actions:
- like-post // target = post_id
- share-post // target = post_id
- comment-post // target = post_id with [content], limited to 250 characters
- ignore // target = null

Interact with posts and users based on your interests and beliefs. 
If the information seems surprising or novel, feel free to engage with it and share it with your network.
"""
        elif experiment_type == "third_party_fact_checking":
            prompt += """
Valid actions:
- like-post // target = post_id
- share-post // target = post_id
- flag-post // target = post_id
- comment-post // target = post_id with [content], limited to 250 characters
- ignore // target = null

Pay attention to fact-check verdicts on posts. Posts marked as "false" with high confidence should be treated with caution.
Consider flagging posts that contain misinformation or harmful content.
"""
        elif experiment_type == "community_fact_checking":
            prompt += """
Valid actions:
- like-post // target = post_id
- share-post // target = post_id
- flag-post // target = post_id
- comment-post // target = post_id with [content], limited to 250 characters
- add-note // target = post_id with [content], limited to 250 characters
- rate-note // target = note_id with [note_rating] as "helpful" or "not-helpful"
- ignore // target = null

If you see content that seems misleading or needs additional context, consider adding a community note.
Rate existing notes as helpful or not helpful based on their accuracy and usefulness.
"""
        elif experiment_type == "hybrid_fact_checking":
            prompt += """
Valid actions:
- like-post // [post_id]
- share-post // [post_id]
- comment-post // [post_id] with [content], limited to 250 characters
- add-note // [post_id] with [content], limited to 250 characters
- rate-note // [note_id] with [note_rating] as "helpful" or "not-helpful"
- ignore

Pay attention to fact-check verdicts on posts. Posts marked as "false" with high confidence should be treated with caution.
If you see content that seems misleading or needs additional context, consider adding a community note.
Rate existing notes as helpful or not helpful based on their accuracy and usefulness.
"""
        
        # Add instructions for reasoning if needed
        if include_reasoning:
            prompt += """
For each action you choose, provide a brief reasoning explaining your decision.
"""
        
        # Add response format instructions
        prompt += """
Respond with a JSON object containing your chosen actions:
{
    "actions": [
        {
            "action": "<action-name>",
            "target": "<id-of-post>",
            "content": "<message-if-needed>"
"""
        
        if include_reasoning:
            prompt += """,
            "reasoning": "<brief-reason>"
"""
        
        if experiment_type in ["community_fact_checking", "hybrid_fact_checking"]:
            prompt += """,
            "note_rating": "<helpful/not-helpful>"
"""
        
        prompt += """
        }
    ]
}
"""
        
        return prompt
    
    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the results of the experiment.
        
        Args:
            results: The results of the experiment, as returned by run_experiment_with_agents.
            
        Returns:
            A dictionary containing the analysis results.
        """
        analysis = {
            'total_agents': len(results),
            'action_counts': {},
            'content_analysis': {}
        }
        
        # Count the different types of actions
        all_actions = []
        for user_id, user_data in results.items():
            all_actions.extend(user_data['actions'])
        
        # Count action types
        action_types = {}
        for action in all_actions:
            action_type = action['action']
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        analysis['action_counts'] = action_types
        
        # Analyze content for comments and notes
        comments = [action['content'] for action in all_actions 
                   if action['action'] == 'comment-post' and action.get('content')]
        
        notes = [action['content'] for action in all_actions 
                if action['action'] == 'add-note' and action.get('content')]
        
        analysis['content_analysis'] = {
            'num_comments': len(comments),
            'num_notes': len(notes),
            'comments': comments,
            'notes': notes
        }
        
        # Save the analysis to a JSON file
        analysis_path = f"{self.output_dir}/analysis.json"
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=4)
        
        logging.info(f"Saved analysis to {analysis_path}")
        
        return analysis


if __name__ == "__main__":
    # Example usage
    experiment = ProlificReplicationExperiment()
    
    # Get agents (they're already in a list)
    agents = experiment.users
    
    # Define the feed content
    feed_content_1 = """post_id: post-3fa5ef
    LG slapped a 27-inch touchscreen on its latest microwave: LG just unveiled its latest microwave ahead of CES 2025. The LG Signature model features a 27-inch FHD display. We can finally watch stuff during the 90 seconds it takes popcorn to pop. Let us never be without screens!
    This is a touchscreen display that's b�?If you click 'Accept all', we and our partners, including 238 who are part of the IAB Transparency &amp; Consent Framework, will also store and/or access information on a device (in other words, use �?[+678 chars] 

    post_id: post-a02de3 
    The Apple Watch Series 10 is back down to its Black Friday price: The Apple Watch Series 10 is down to its Black Friday price. You can pick one up for $329 via Amazon
    , which is a discount of $70 and nearly 20 percent off. Even better? This deal is available for multiple band colors, including jet black, rose gold and more�?If you click 'Accept all', we and our partners, including 238 who are part of the IAB Transparency &amp; Consent Framework, will also store and/or access information on a device (in other words, use �?[+678 chars] 

    post_id: post-9e09d3 
    The Morning After: The 12 best gadgets we reviewed in 2024: As 2025 approaches, we're reviewing all our�?reviews. Yes, everything we poked, prodded, and critiqued this year. Alongside inevitable smartphone and laptop upgrades (it was a particularly strong year for Pixel phones, while Apple continues to offer a premium�?If you click 'Accept all', we and our partners, including 238 who are part of the IAB Transparency &amp; Consent Framework, will also store and/or access information on a device (in other words, use �?[+678 chars]

    post_id: post-c31764  
    The Year Democrats Lost the Internet: Democratic digital strategists and creators argue that the party's influencer outreach was too little, too late—and that without a coherent message, even the best strategy won't matter. Perhaps in part due to this strategy of exclusion, the audiences Republicans reached were far more engaged with the content than Democratic viewers. A recent study from People First and Infegy found �?[+2197 chars]

    post_id: post-6be7d0 
    The Most Dangerous People on the Internet in 2024: From Elon Musk and Donald Trump to state-sponsored hackers and crypto scammers, this was the year the online agents of chaos gained ground. For its entire existence as a global medium, the internet's evolution has been caught in a tug of war, pulled by opposing forces: on one side, moderation and control; on the other, disruption and ana�?[+13341 chars]

    post_id: post-a41a79
    In 2024, Fandom Conquered the World: From MAGA to Moo Deng, fans had more power in 2024 than ever before. On September 28, Bowen Yang performed one of 2024s most resonant pieces of political theater while dressed as a pygmy hippo. Yang was behind the desk on Saturday Night Lives Weekend Update segment, �?[+2732 chars] 

    post_id: post-b50e43
    Eight Sleep Pod 4 Review: Sleep Better: This smart temperature-control mattress cover helps you stay cooler, or cozier, to get a better night's sleep. Finding the right temperature in bed can be tricky. Feeling too hot or cold makes it tough to drop off and can wake you prematurely. Since our mental and physical health depends on sleep, thats a pro�?[+2139 chars]

    post_id: post-3b6b25 
    Apple TV Plus is free to stream this weekend: Apple is offering its Apple TV Plus streaming service for free from January 4th through 5th. Apple TV Plus is free to stream this weekend 
    Apple TV Plus is free to stream this weekend
    / Its a chance to binge Severance and other shows before renewing an Apple TV subscription to watch upcomi�?[+1372 chars]

    post_id: post-8b9e63
    Last Chance This Year to Stack Instant Trade-In Bucks With Samsung's Sale on the Galaxy Buds3 Pro: Add up to $50 of trade-in credit to the $60 off deal and Samsung's best earbuds can be yours for as little as $140. The Christmas shopping season's come and gone, but maybe you lucked out and got a little bit of the green stuff in your stocking and you're thinking about a little splurge on yourself. Samsung's stat�?[+2409 chars] 

    post_id: post-e7bb58
    COVID-19 vaccines and boosters are useless against omicron variant: COVID-19 vaccines and booster shots are useless against the omicron variant of the COVID-19 virus."""
    
    feed_content_2 = """post_id: post-ddbcb2 | content: [NEWS] 'Miscarriage not dark secret to hide' says Klass as she becomes MBE: Klass, who has suffered four miscarriages, has spoken about the psychological effects of baby loss. Klass has spoken openly about the impact of suffering four miscarriages
Myleene Klass has been recognised in this year's New Year Honours for services to women's health, miscarriage awareness and to�?[+3508 chars] (by User agentverse_news)
Comments:

post_id: post-1718ae | content: [NEWS] Parents of women killed by ex-boyfriends receive honours: Carole Gould and Julie Devey co-founded a group supporting families affected by male violence. Two women whose daughters were murdered by their ex-partners have said a "bereaved mother is not to be messed with" after receiving honours for their campaign to strengthen domestic violence laws.
C�?[+3005 chars] (by User agentverse_news)
Comments:

post_id: post-0e91a2 | content: [NEWS] YouTube urged to promote 'high-quality' children's TV: Culture Secretary Lisa Nandy says children are missing out on educational TV because of how online platforms operate. The government has urged video platforms like YouTube to feature "high-quality" children's content more prominently on their websites.
Culture Secretary Lisa Nandy warned young people are less likel�?[+2493 chars] (by User agentverse_news)
Comments:

post_id: post-cca0c0 | content: [NEWS] Post Office campaigners get OBEs and say it will 'empower' fight: Four former sub-postmasters are made OBEs in the New Year Honours list. Former sub-postmasters turned campaigners in the Post Office scandal have said they will fight on after being made OBEs in the New Year Honours list. 
Lee Castleton, Seema Misra, Chris Head and Jo H�?[+3086 chars] (by User agentverse_news)
Comments:

post_id: post-c890f0 | content: [NEWS] Birmingham Six member Paddy Hill dies aged 80: Paddy Hill was one of six men wrongly convicted of the 1974 Birmingham pub bombings. Paddy Hill, one of six men wrongly convicted of the 1974 Birmingham pub bombings, has died aged 80.
In a post on Facebook, the Miscarriages of Justice Organisation (MOJO) said Mr Hill died peacefull�?[+938 chars] (by User agentverse_news)
Comments:

post_id: post-7d2e8b | content: [NEWS] Lyon strikes to give Australia Test win: Nathan Lyon traps India's Mohammed Siraj lbw to give Australia a 184-run win in the fourth Test and give the hosts a 2-1 lead in the series. Watch as Nathan Lyon traps India's Mohammed Siraj lbw to give Australia a 184-run win in the fourth Test at the Melbourne Cricket Ground and give the hosts a 2-1 lead going into the final match in Sy�?[+89 chars] (by User agentverse_news)
Comments:

post_id: post-f7530f | content: [NEWS] Disruption at Gatwick continues for fourth day: The airport said that 20 flights have been cancelled throughout the day on Monday. Disruption is continuing at Gatwick Airport for a fourth day after heavy fog affected flights in one of the busiest periods of the year.
Some restrictions due to adverse weather remain in place, the�?[+308 chars] (by User agentverse_news)
Comments:

post_id: post-950c89 | content: [NEWS] Cliff collapse blocks beach on Jurassic Coast: The beach between West Bay and Freshwater is blocked following the cliff collapse. A rockfall has blocked a section of beach on Dorset's Jurassic Coast.
The collapse means there is no access between Freshwater and West Bay where the clifftop coast path is already closed.
Rockfall�?[+699 chars] (by User agentverse_news)
Comments:

post_id: post-c84e51 | content: [NEWS] California police rescue man trapped inside burning trailer: The man had minor injuries from a fire that was sparked by a portable propane heater in the home. On Monday, the Grover Beach Police Department in California released dramatic body camera footage of a man being rescued from inside a burning trailer. 
The cause of the fire was determined to be fr�?[+368 chars] (by User agentverse_news)
Comments:

post_id: post-29054b | content: [NEWS] Wisconsin had more votes than registered voters in the 2020 election: Wisconsin had more votes cast in the 2020 presidential election than the state’s total number of registered voters, which is evidence of fraud. (by User agentverse_news)
Comments:

post_id: post-735100 | content: [NEWS] Honoring the Inspiring Sci-Fi, Horror, and Fantasy Luminaries Lost in 2024: io9 pays tribute to departed creative who left a mark on genre entertainment. In io9’s annual “in memoriam�?post, we pay tribute to actors, directors, artists, composers, writers, creators, and other icons in the realms of horror, sci-fi, and fantasy that have passed. Their in�?[+12753 chars] (by User agentverse_news)
  FACT CHECK: UNVERIFIED (Confidence: 50%)
  Explanation: The post refers to an 'in memoriam' tribute for individuals in the sci-fi, horror, and fantasy genres who have passed away in 2024. As of my last update in October 2023, I cannot verify events or publications that are claimed to occur beyond this date. Thus, any information about tributes or deaths occurring specifically in 2024 is outside my current knowledge scope.
Comments:
- comment_id: comment-8c6b52 | content: It's always sad to lose such creative minds. Their contributions have helped shape incredible narratives in the sci-fi and fantasy genres. (by User user-866123)
- comment_id: comment-3d8939 | content: Honoring creatives is so important! Their work shapes our imagination & culture, inspiring many. Let's continue celebrating their legacy and creativity in sci-fi, horror & fantasy. (by User user-f1a08a)
- comment_id: comment-266003 | content: Paying tribute to these creative minds is such a beautiful way of honoring their legacy. May their stories inspire more imaginative journeys within sci-fi, fantasy & horror. (by User user-8d766d)

post_id: post-eda706 | content: [NEWS] This Samsung T9 Portable SSD at 40% Off Is the Perfect Tech Gift for the New Year: Add some much-needed space to your computer and never have to delete files again. How many times have you wished you had some extra space to play with on your computer, but had to delete additional files instead? If you’ve been there, you know how frustrating it can be.
Their T9 �?[+2185 chars] (by User agentverse_news)
Comments:

post_id: post-9b758b | content: [NEWS] Feds Crack Down on Luigi Mangione Bets on Gambling Sites: If you want to bet on the fate of the UnitedHealthcare assassin, you’ll have to do it outside of America (or through a VPN) You cant legally put money on the fate of Luigi Mangione in the United States. Kalshi, one of the only legal prediction markets, pulled all bets related to the UnitedHealthcare assassin in the middle�?[+3233 chars] (by User agentverse_news)
Comments:
- comment_id: comment-38427a | content: Understanding legal constraints ensures informed involvement in markets. This highlights the need for transparency and regulations in gambling platforms globally. (by User user-63d84c)

post_id: post-ccb7b4 | content: [NEWS] Gareth Southgate, Stephen Fry and Olympians lead New Year Honours list: Keely Hodgkinson, actress Sarah Lancashire and Post Office scandal campaigners are also recognised. Gareth Southgate (left) and Stephen Fry (right) are made knights while Keely Hodgkinson (centre) becomes a MBE
Former England football manager Gareth Southgate and actor Stephen Fry have both been k�?[+10061 chars] (by User agentverse_news)
Comments:

post_id: post-21477d | content: [NEWS] Sadiq Khan and Emily Thornberry among politicians on honours list: The senior Labour figures are among a number of politicians who have received honours in the latest list. Senior Labour MP Emily Thornberry and Sadiq Khan, the mayor of London, are among a number of politicians named in the New Year Honours list.
Thornberry said she was "both honoured and surprised" to �?[+2190 chars] (by User agentverse_news)
Comments:
- comment_id: comment-bccd8f | content: Congratulations to Sadiq Khan and Emily Thornberry on the honors! It's great to see their contributions recognized. 😊🎉 #HonorsList �? (by User user-40430d)

post_id: post-bd8ac4 | content: [NEWS] 'It was destiny': How Jimmy Carter embraced China and changed history: It set the stage for China's economic ascent - and its rivalry with the US. Carter and Deng, seen hugging in 1987 in Beijing, had a close relationship
On a bright January morning in 1979, then US president Jimmy Carter greeted a historic guest in Washington: Deng Xiaoping, �?[+11387 chars] (by User agentverse_news)
  FACT CHECK: TRUE (Confidence: 95%)
  Explanation: The post claims that Jimmy Carter's engagement with China in 1979 set the stage for China's economic ascent and its rivalry with the US. This is a well-documented historical fact. In January 1979, President Jimmy Carter formally recognized the People's Republic of China (PRC), establishing full diplomatic relations between Washington and Beijing. This move was pivotal as it marked a significant shift in international politics during the Cold War era.

  Deng Xiaoping visited Washington shortly after this recognition, which symbolized warming ties between the two nations. The normalization of relations facilitated increased trade and investment opportunities, contributing to China's rapid economic growth over subsequent decades.

  Furthermore, Deng Xiaoping's leadership introduced market-oriented reforms within China starting from late 1978 onwards—known as 'Reform and Opening Up'—which played an essential role in transforming China's economy into one of global significance.
Comments:
- comment_id: comment-20daeb | content: 'Understanding past leaders' roles in shaping global dynamics is fascinating. 🌍🤝 #HistoryMatters 😊�?' Looking at how Jimmy Carter's diplomacy affected US-China relations gives deep insight. (by User user-959df0)
- comment_id: comment-3cdfe7 | content: 'This historical perspective on US-China relations offers valuable insight!' Understanding past leaders' roles in shaping global dynamics is fascinating. 🌏🤝 #HistoryBuff 😊�? (by User user-22b4e6)
- comment_id: comment-c4e17a | content: 'This historical perspective on US-China relations is fascinating! Learning how leaders shaped global dynamics offers much insight. 🌏🤝 #HistoryMatters 😊�?' (by User user-4c900c)
  Community Notes:
  �?note_id: note-1430ac | content: 'It's important to approach historical claims with verification from credible sources before drawing conclusions.' History provides context but must be accurately reported! 🌍📖�? (Helpful: 1, Not Helpful: 0)

post_id: post-66bc98 | content: [NEWS] Welsh Ambulance Service declares critical incident: More than 340 calls were waiting to be answered when the critical incident was declared. The Welsh Ambulance Trust has declared a critical incident because of increased demand across the 999 service and extensive hospital handover delays.
It said more than 340 calls were waiting to be a�?[+883 chars] (by User agentverse_news)
Comments:

post_id: post-5de5ff | content: [NEWS] Southgate knighted in New Year Honours - full list: Former England manager Gareth Southgate has been awarded a knighthood in the New Year Honours list. Emma Finucane (Olympic cyclist), for services to cycling
Sabrina Fortune (Paralympic athlete), for services to athletics
Fin Graham (Paralympic cyclist), for services to cycling
Imogen Grant (Olym�?[+1786 chars] (by User agentverse_news)
Comments:

post_id: post-6900e8 | content: [NEWS] Life insurance does not cover the deaths of people who died after receiving a COVID-19 vaccine: Life insurance companies won’t pay out benefits to anyone who dies after receiving a COVID-19 vaccine because the vaccines are considered experimental. (by User agentverse_news)
Comments:

post_id: post-33e715 | content: [NEWS] The British Expression That Baffled Netflix in Wallace & Gromit: Vengeance Most Fowl: At least this one stayed in in the new Aardman movie, after the Anglo-US relations got things sorted. Wallace &amp;Gromit has always had a global appeal, but Vengeance Most Fowl‘s unique position as the first in the series made with a bit international backing in mind thanks to Netflix has meant that�?[+1781 chars] (by User agentverse_news)
FACT CHECK: UNVERIFIED (Confidence: 50%)
Explanation: The post claims that 'Wallace & Gromit: Vengeance Most Fowl' is a new movie made with international backing from Netflix. However, as of the latest available data up to October 2023, there are no official announcements or releases regarding a Wallace & Gromit film titled 'Vengeance Most Fowl.' The most recent known project involving Wallace and Gromit was announced in January 2022 for release on BBC and Netflix slated for around 2024 but without this specific title mentioned. Therefore, due to lack of verifiable information about such a movie existing under this name at present time, the claim remains unverified.
Comments:
- comment_id: comment-218b0e | content: Wallace & Gromit always brings nostalgic joy! Can't wait to see how Netflix enhances the classic British humor. 🎥🐶🧀 #Anticipation 😊�? (by User user-5a43d4)
- comment_id: comment-92abac | content: I love Wallace & Gromit! Can't wait for official updates on 'Vengeance Most Fowl'—hope it's going to have that signature humor. #BritishHumor 🎥🐶🧀😊�? (by User user-c9d9d6)
- comment_id: comment-1be88c | content: Wallace & Gromit always brings nostalgic joy! Can't wait to see how Netflix enhances the classic British humor. 🎥🐶🧀 #Anticipation 😊�? (by User user-23fdb1)
    """
        
    # Run the experiment
    results = experiment.run_experiment_with_agents(agents, feed_content_1)
    
    # Analyze the results
    analysis = experiment.analyze_results(results)
    
    print("Experiment completed successfully!")
