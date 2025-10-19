import requests
import psycopg2
import time
import os
from dotenv import load_dotenv

load_dotenv()

# --- GitHub API Config ---
url = "https://api.github.com/graphql"
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise ValueError("❌ No GitHub token found. Set GITHUB_TOKEN in environment variables.")

headers = {"Authorization": f"Bearer {token}"}

# --- PostgresSQL Config ---
conn = psycopg2.connect(
    dbname = 'github_data',
    user = 'postgres',
    password = 'postgres',
    host = "localhost",
    port = '5432'
)

cursor = conn.cursor()

# --- Function to fetch Repositories ---
def fetch_repositories():
    all_repos = []
    has_next_page = True
    end_cursor = None


    while has_next_page and len(all_repos) < 50:
        print(f"Fetching batch... (Total: {len(all_repos)})")

        query = f"""
        {{
            search (query: "stars:>1000", type: REPOSITORY, first: 10 {f', after: "{end_cursor}"' if end_cursor else ''}) {{
                pageInfo {{
                    endCursor
                    hasNextPage
                }}
                nodes {{
                    ... on Repository {{
                        name
                        owner {{ login }}
                        stargazerCount
                    }}
                }}
            }}
        }}
        """

        # --- Retry Mechanism ---
        for attempt in range(3):
            try:
                response = requests.post(url, json={"query": query}, headers=headers, timeout=10)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    wait = 2 ** attempt
                    print(f"Retrying in {wait} seconds...")
                    time.sleep(wait)
                else:
                    print("❌ Max retries reached. Skipping this batch.")
                    return []

        # --- Handle API Response ---
        data = response.json()

        # Error handling for GraphQL errors
        if "errors" in data:
            print(f"⚠️ GraphQL error: {data['errors']}")
            break

        # Extract data
        try:
            search_data = data["data"]["search"]
        except (KeyError, TypeError):
            print("⚠️ Unexpected API response:", data)
            break

        all_repos.extend(search_data["nodes"])

        has_next_page = search_data["pageInfo"]["hasNextPage"]
        end_cursor = search_data["pageInfo"]["endCursor"]

        # Checking the rate limit
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
        reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
        
        # Sleep if almost at limits
        if remaining < 10:
            wait = reset_time - time.time() + 5
            print(f"⏸ Rate limit nearly exhausted. Sleeping for {wait:.0f} seconds...")
            time.sleep(wait)

        # --- Safety Delay Between Batches ---
        time.sleep(2)

    return all_repos

# --- Function to Save Data into PostgreSQL ---
def save_to_postgres(repos):
    for repo in repos:
        owner = repo['owner']['login']
        name = repo['name']
        stars = repo['stargazerCount']

        cursor.execute("""
        INSERT INTO repositories (owner_name, repo_name, stars)
        VALUES (%s, %s, %s)
        ON CONFLICT (owner_name, repo_name)
        DO UPDATE SET stars = EXCLUDED.stars, last_updated = CURRENT_TIMESTAMP
        """, (owner, name, stars))

    conn.commit()
    print(f"✅ Saved {len(repos)} repositories into PostgreSQL!")

# --- Main Script ---
try:
    repos = fetch_repositories()
    if repos:
        save_to_postgres(repos)
    else:
        print("⚠️ No repositories fetched.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
finally:
    # --- Cleanup ---
    cursor.close()
    conn.close()
    print("🧹 Database connection closed.")