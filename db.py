import mysql.connector
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="localhost",
            user="your_mysql_username",
            password="your_mysql_password",
            database="telegram_bot_db"
        )
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                language VARCHAR(10) DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                prompt_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT,
                prompt_text TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS premium (
                premium_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                prompt_limit INT,
                prompts_used INT DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        self.connection.commit()

    def add_user(self, user_id, username):
        """Add a new user to the database."""
        self.cursor.execute("""
            INSERT INTO users (user_id, username)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE username = %s
        """, (user_id, username, username))
        self.connection.commit()

    def get_user(self, user_id):
        """Retrieve a user from the database."""
        self.cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()

    def update_user_language(self, user_id, language):
        """Update a user's language preference."""
        self.cursor.execute("""
            UPDATE users
            SET language = %s
            WHERE user_id = %s
        """, (language, user_id))
        self.connection.commit()

    def save_prompt(self, user_id, prompt_text, response_text):
        """Save a user's prompt and the bot's response."""
        self.cursor.execute("""
            INSERT INTO prompts (user_id, prompt_text, response_text)
            VALUES (%s, %s, %s)
        """, (user_id, prompt_text, response_text))
        self.connection.commit()

    def get_prompts(self, user_id):
        """Retrieve all prompts for a user."""
        self.cursor.execute("SELECT * FROM prompts WHERE user_id = %s", (user_id,))
        return self.cursor.fetchall()

    def add_premium(self, user_id, days=30, prompt_limit=100):
        """Add a premium subscription for a user."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        self.cursor.execute("""
            INSERT INTO premium (user_id, start_date, end_date, prompt_limit)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            start_date = %s, end_date = %s, prompt_limit = %s, prompts_used = 0
        """, (user_id, start_date, end_date, prompt_limit, start_date, end_date, prompt_limit))
        self.connection.commit()

    def get_premium(self, user_id):
        """Retrieve premium subscription details for a user."""
        self.cursor.execute("SELECT * FROM premium WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()

    def increment_prompt_count(self, user_id):
        """Increment the prompt count for a premium user."""
        self.cursor.execute("""
            UPDATE premium
            SET prompts_used = prompts_used + 1
            WHERE user_id = %s
        """, (user_id,))
        self.connection.commit()

    def is_premium_active(self, user_id):
        """Check if a user's premium subscription is active and within the prompt limit."""
        premium = self.get_premium(user_id)
        if not premium:
            return False
        end_date = premium[3]
        prompt_limit = premium[4]
        prompts_used = premium[5]
        return datetime.now() < end_date and prompts_used < prompt_limit

    def close(self):
        """Close the database connection."""
        self.cursor.close()
        self.connection.close()