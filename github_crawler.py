import os
import time
import requests
import psycopg2
from datetime import datetime, timedelta

# ============================================================
#  FETCH REPOSITORIES FUNCTION
# ============================================================

def get_query(date_filter, end_cursor):
    return f"""
    {{
        search(query: "{date_filter}", type: REPOSITORY, first: 100 {f', after: "{end_cursor}"' if end_cursor else ''}) {{
            pageInfo {{
                endCursor
                hasNextPage
            }}
            nodes {{
                ... on Repository {{
                    name
                    owner {{ login }}
                    stargazerCount
                    createdAt
                }}
            }}
        }}
    }}
    """

def handle_errors(response):
    if response.status_code == 403:
        reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
        wait_for = max(0, reset_time - time.time())
        print(f"⏳ Rate limit hit. Waiting {wait_for:.2f}s...")
        time.sleep(wait_for)

        return True
        
    if response.status_code != 200:
        print(f"⚠️ GitHub API Error: {response.status_code}")
        retries -= 1
        time.sleep(2)

        return True
    
    return False
        

def fetch_repositories(token, target=100000):
    """Fetch up to target repositories using GitHub GraphQL API with rate limit handling."""
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    all_repos = []

    # Generate monthly date ranges (e.g., 2014-01 to 2024-12)
    start_date = datetime(2014, 1, 1)
    end_date = datetime(2024, 12, 31)
    delta = timedelta(days=30)

    date_ranges = []
    current = start_date
    while current < end_date:
        next_month = current + delta
        date_ranges.append(f"created:{current.date()}..{next_month.date()}")
        current = next_month

    print(f"📆 Generated {len(date_ranges)} monthly ranges to fetch data from.")

    # Start fetching
    for date_filter in date_ranges:
        print(f"\n🔍 Fetching repos for {date_filter}")
        has_next_page = True
        end_cursor = None

        while has_next_page and len(all_repos) < target:
            query = get_query(date_filter, end_cursor) 

            retries = 3
            while retries > 0:
                try:
                    response = requests.post(url, json={"query": query}, headers=headers)

                    # --- Handle Errors ---
                    if handle_errors(response):
                        continue

                    data = response.json()
                    if "errors" in data:
                        print("⚠️ GraphQL error:", data["errors"])
                        retries -= 1
                        time.sleep(2)
                        continue

                    search_data = data["data"]["search"]
                    repos = search_data["nodes"]
                    all_repos.extend(repos)

                    has_next_page = search_data["pageInfo"]["hasNextPage"]
                    end_cursor = search_data["pageInfo"]["endCursor"]

                    print(f"📦 Total fetched so far: {len(all_repos)}")
                    time.sleep(1.2)
                    break

                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Network error: {e}")
                    retries -= 1
                    time.sleep(3)

            if retries == 0:
                print("❌ Failed after multiple retries. Skipping batch.")

            if len(all_repos) >= target:
                print(f"✅ Target reached: {len(all_repos)} repositories.")
                return all_repos

    print(f"\n✅ Completed fetching {len(all_repos)} repositories.")
    return all_repos


# ============================================================
#  STORE INTO POSTGRES FUNCTION
# ============================================================

def store_in_postgres(conn, repositories):
    """Store repository data into PostgreSQL."""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id SERIAL PRIMARY KEY,
        owner_name TEXT NOT NULL,
        repo_name TEXT NOT NULL,
        stars INTEGER,
        created_at TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (owner_name, repo_name)
    );
    """)
    conn.commit()

    for repo in repositories:
        owner = repo['owner']['login']
        name = repo['name']
        stars = repo['stargazerCount']
        created = repo.get('createdAt')

        cur.execute("""
        INSERT INTO repositories (owner_name, repo_name, stars, created_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (owner_name, repo_name)
        DO UPDATE SET
            stars = EXCLUDED.stars,
            last_updated = CURRENT_TIMESTAMP;
        """, (owner, name, stars, created))

    conn.commit()
    cur.close()
    print(f"💾 Stored {len(repositories)} repositories in PostgreSQL.")


# ============================================================
#  MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()

        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("❌ Missing GITHUB_TOKEN environment variable.")

        # --- Connect to PostgreSQL ---
        conn = psycopg2.connect(
            dbname="github_data",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )

        repos = fetch_repositories(token, target=100000)
        store_in_postgres(conn, repos)

    except Exception as e:
        print("❌ Unexpected error:", e)

    finally:
        if 'conn' in locals():
            conn.close()
        print("🧹 Database connection closed.")
