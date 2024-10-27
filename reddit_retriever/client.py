import praw
from dotenv import load_dotenv
import os
from database import save_posts_to_db
import logging

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
reddit = praw.Reddit(client_id=os.getenv('CLIENT_ID'),
                     client_secret=os.getenv('CLIENT_SECRET'),
                     user_agent=os.getenv('USERNAME'),
                     username=os.getenv('USER_NAME'),
                     password=os.getenv('PASSWORD'),
                     redirect_uri=os.getenv('REDIRECT_URI'))
def get_posts(subreddit_name, flair_text, limit=None, after=None, time_filter='all'):
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.search(f"flair_name:{flair_text}", limit=limit, params={'after': after}, time_filter=time_filter)
    save_posts_to_db(posts)
    return posts

def main():
    logger.info("Starting Reddit scraper...")
    unix_time_limit = 'year'
    subreddit_name = "Israel"
    flair_text = "Meme"

    get_posts(subreddit_name, flair_text, time_filter=unix_time_limit)

    # download_media('https://www.reddit.com/gallery/1bkb0fx')

if __name__ == "__main__":
    main()











