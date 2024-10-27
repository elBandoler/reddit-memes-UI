from sqlalchemy import Column, Integer, String, create_engine, DateTime, LargeBinary, ForeignKey
from sqlalchemy.orm import Session, declarative_base, relationship
import datetime as dt
from utils import download_media

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    subreddit = Column(String)
    title = Column(String)
    content = Column(String)
    date = Column(DateTime)
    author = Column(String)
    media = relationship("Media", back_populates="post")
    src = Column(String)

class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    post = relationship("Post", back_populates="media")
    data = Column(LargeBinary)


# create the database engine and create the tables
engine = create_engine('sqlite:///reddit.db')
Base.metadata.create_all(engine)


def save_posts_to_db(posts):
    with Session(engine) as session:

        for post in posts:
            media = download_media(post.url)
            media_arr = []
            if media is None:
                continue
            for m in media:
                new_media = Media(data=m)
                session.add(new_media)
                media_arr.append(new_media)

            new_post = Post(url=f"https://www.reddit.com/r/{post.subreddit}/comments/{post.id}",
                            subreddit=f"/r/{post.subreddit}",
                            title=post.title,
                            content=post.selftext,
                            date=dt.datetime.fromtimestamp(post.created_utc),
                            author=post.author.name,
                            media=media_arr,
                            src=post.url)
            session.add(new_post)
        session.commit()
