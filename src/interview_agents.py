import logging
import sqlite3
import json
from agent_user import AgentUser
import argparse

# usage: python interview_agents.py --reset

ENABLE_LLM_INTERVIEWS = False

INTERVIEW_QUESTIONS = [
    "Who were your favorite users to interact with and why?",
    "What types of content did you most enjoy engaging with?",
    "Did you encounter any particularly meaningful or negative experiences?"
]

class AgentInterviewer:
    def __init__(self, engine: str = "gemini-2.0-flash"):
        self.engine = engine
        self.openai_client = None
        if ENABLE_LLM_INTERVIEWS:
            from multi_model_selector import multi_model_selector
            # Unified model selection via MultiModelSelector (interview role)
            if engine.startswith("gpt") or engine.startswith("gemini"):
                self.openai_client, _ = multi_model_selector.create_openai_client(role="interview")
            else:
                self.openai_client, _ = multi_model_selector.create_openai_client_with_base_url(
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                    role="interview",
                )
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Initialize the interviews table
        self._init_db()

    def _init_db(self):
        """
        Initialize the interviews table in the database
        """
        conn = sqlite3.connect('database/simulation.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interviews (
                    interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    question TEXT,
                    answer TEXT,
                    context JSON,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            conn.commit()
        except Exception as e:
            logging.error(f"Error creating interviews table: {str(e)}")
            raise
        finally:
            conn.close()

    def load_users_from_db(self):
        """
        Load all users from the database and recreate AgentUser objects
        """
        users = []
        conn = sqlite3.connect('database/simulation.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT user_id, gender, age, location, communication_style, background 
                FROM users
            """)
            
            for row in cursor.fetchall():
                user_id, gender, age, location, communication_style, background = row
                
                # Reconstruct the config dictionary
                config = {
                    'demographic': {
                        'gender': gender,
                        'age': age,
                        'location': location
                    },
                    'persona': {
                        'communication_style': communication_style,
                        'background': background
                    },
                    'engine': self.engine
                }
                
                users.append(AgentUser(user_id, config))
                
            logging.info(f"Loaded {len(users)} users from database")
            return users
            
        except Exception as e:
            logging.error(f"Error loading users from database: {str(e)}")
            raise
        finally:
            conn.close()

    def interview_users(self, interview_questions=INTERVIEW_QUESTIONS):
        """
        Interview each user about their experience in the simulation.
        
        Args:
            interview_questions (list): List of questions to ask each user
        """
        logging.info("\nBeginning user interviews...")
        
        users = self.load_users_from_db()
        
        for user in users:
            logging.info(f"\nInterviewing User {user.user_id}...")
            
            # Create a context for the interview based on user's activity
            conn = sqlite3.connect('database/simulation.db')
            cursor = conn.cursor()
            
            # Get user's posting stats
            cursor.execute("""
                SELECT COUNT(*) FROM posts WHERE author_id = ?
            """, (user.user_id,))
            post_count = cursor.fetchone()[0]
            
            # Get user's interaction stats
            cursor.execute("""
                SELECT action_type, COUNT(*) 
                FROM user_actions 
                WHERE user_id = ?
                GROUP BY action_type
            """, (user.user_id,))
            actions = dict(cursor.fetchall())
            
            # Get some example posts by this user
            cursor.execute("""
                SELECT content FROM posts 
                WHERE author_id = ? 
                ORDER BY RANDOM() 
                LIMIT 3
            """, (user.user_id,))
            sample_posts = [row[0] for row in cursor.fetchall()]
            
            # Create context for the AI
            context = {
                "user_demographic": user.demographic,
                "user_persona": user.persona,
                "stats": {
                    "posts_created": post_count,
                    "actions": actions,
                    "sample_posts": sample_posts
                }
            }

            if not ENABLE_LLM_INTERVIEWS:
                # Skip LLM interviews; only record latest reflection memory snapshot.
                cursor.execute("""
                    SELECT content
                    FROM agent_memories
                    WHERE user_id = ? AND memory_type = 'reflection'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user.user_id,))
                row = cursor.fetchone()
                memory_snapshot = row[0] if row else ""

                cursor.execute("""
                    INSERT INTO user_interviews
                    (user_id, question, answer, context)
                    VALUES (?, ?, ?, ?)
                """, (
                    user.user_id,
                    "MEMORY_SNAPSHOT",
                    memory_snapshot,
                    json.dumps(context)
                ))
                conn.commit()
                logging.info(f"User {user.user_id}: memory snapshot recorded")
                conn.close()
                continue

            # Create the interview prompt
            prompt = f"""You are the user with the following characteristics:
Demographic: {json.dumps(user.demographic, indent=2)}
Persona: {json.dumps(user.persona, indent=2)}
Activity Stats: {json.dumps(context['stats'], indent=2)}

Some of your posts included:
{json.dumps(sample_posts, indent=2)}

Based on these characteristics and activities, please provide a brief but natural response to this question:"""

            # Ask each question and save responses
            for question in interview_questions:
                try:
                    response = self.openai_client.chat.completions.create(
                        model=self.engine,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": question}
                        ],
                        max_tokens=150,
                        temperature=0.7
                    )
                    answer = response.choices[0].message.content

                    # Save to database
                    cursor.execute("""
                        INSERT INTO user_interviews
                        (user_id, question, answer, context)
                        VALUES (?, ?, ?, ?)
                    """, (
                        user.user_id,
                        question,
                        answer,
                        json.dumps(context)
                    ))
                    conn.commit()

                    logging.info(f"Q: {question}")
                    logging.info(f"A: {answer}\n")
                except Exception as e:
                    logging.error(f"Error during interview: {str(e)}")
            
            conn.close()

    def get_interview_results(self, user_id=None):
        """
        Retrieve interview results from the database
        
        Args:
            user_id (int, optional): Specific user to get results for
        
        Returns:
            list: Interview results
        """
        conn = sqlite3.connect('database/simulation.db')
        cursor = conn.cursor()
        
        try:
            if user_id:
                cursor.execute("""
                    SELECT user_id, timestamp, question, answer, context
                    FROM user_interviews
                    WHERE user_id = ?
                    ORDER BY timestamp, user_id
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT user_id, timestamp, question, answer, context
                    FROM user_interviews
                    ORDER BY timestamp, user_id
                """)
            
            results = cursor.fetchall()
            return results
        
        finally:
            conn.close()

    def reset_interviews(self):
        """
        Reset the interviews table by dropping and recreating it.
        Returns the number of deleted records.
        """
        conn = sqlite3.connect('database/simulation.db')
        cursor = conn.cursor()
        
        try:
            # First get the count of existing records
            cursor.execute("SELECT COUNT(*) FROM user_interviews")
            count = cursor.fetchone()[0]
            
            # Drop the table
            cursor.execute("DROP TABLE IF EXISTS user_interviews")
            conn.commit()
            
            # Recreate the table
            self._init_db()
            
            logging.info(f"Successfully reset interviews table. Deleted {count} records.")
            return count
            
        except Exception as e:
            logging.error(f"Error resetting interviews table: {str(e)}")
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run agent interviews')
    parser.add_argument('--reset', action='store_true', 
                       help='Reset the interviews database before running')
    args = parser.parse_args()
    
    # Load configuration
    with open('configs/experiment_config.json', 'r') as file:
        config = json.load(file)
    
    engine = config['engine']
    
    # Create interviewer
    interviewer = AgentInterviewer(engine)
    
    # Reset if requested
    if args.reset:
        deleted_count = interviewer.reset_interviews()
        logging.info(f"Reset complete. Deleted {deleted_count} previous interviews.")
    
    # Run new interviews
    interviewer.interview_users(INTERVIEW_QUESTIONS)
    
    # Example: Analyze results
    logging.info("\nRetrieving interview results...")
    results = interviewer.get_interview_results()
    
    # Print summary
    user_count = len(set(r[0] for r in results))
    interview_count = len(results)
    logging.info(f"\nInterview Summary:")
    logging.info(f"Total Users Interviewed: {user_count}")
    logging.info(f"Total Q&A Pairs: {interview_count}")
