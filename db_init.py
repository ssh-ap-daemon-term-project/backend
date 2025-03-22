from app.database import Base, engine
from app.models import User
# If you have other models, import them as well
# from app.models import User, Post, Comment, etc.

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()