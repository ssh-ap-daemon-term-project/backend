import psycopg2
from psycopg2 import sql, OperationalError

# Replace with your actual credentials
DB_HOST = "sshapdaemon.postgres.database.azure.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "sshapdaemon"
DB_PASSWORD = "noPassword1"
def connect_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✅ Connected to the database.")
        return conn
    except OperationalError as e:
        print("❌ Connection failed:", e)
        exit(1)

def run_query(conn, query):
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description:  # If the query returns rows (e.g., SELECT)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                print("🧾 Results:")
                print(" | ".join(columns))
                print("-" * 50)
                for row in rows:
                    print(" | ".join(str(col) for col in row))
            else:
                print(f"✅ Query executed. {cur.rowcount} rows affected.")
            conn.commit()
    except Exception as e:
        print("❌ Error executing query:", e)
        conn.rollback()

def main():
    conn = connect_db()
    print("Enter SQL queries below (type 'exit' to quit):")
    while True:
        try:
            query = input("SQL> ").strip()
            if query.lower() in ('exit', 'quit'):
                break
            if query.lower() == '\\dt':
                query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE';
                """

            if query:
                run_query(conn, query)
        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break
    conn.close()

if __name__ == "__main__":
    main()
