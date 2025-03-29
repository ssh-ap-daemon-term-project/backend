from app.database import Base, engine
from sqlalchemy import inspect, text
from app.models import *  # Import all models

def reset_model_tables():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()  # Get all tables in the database

    # Get tables in the order they should be dropped (reverse dependency order)
    ordered_tables = list(Base.metadata.tables.keys())[::-1]

    with engine.connect() as conn:
        trans = conn.begin()  # Start transaction
        try:
            for table in ordered_tables:
                if table in existing_tables:
                    print(f"Dropping table: {table}")
                    conn.execute(text(f'DROP TABLE {table} CASCADE'))  # Use text() for raw SQL
            trans.commit()  # Commit transaction after successful execution
        except Exception as e:
            trans.rollback()  # Rollback if any error occurs
            print(f"Error dropping tables: {e}")
            return

    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables updated successfully!")

if __name__ == "__main__":
    reset_model_tables()
