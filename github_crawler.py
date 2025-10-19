import os
import time
import requests
import psycopg2

# ============================================================
#  GITHUB CLIENT (Anti-Corruption Layer)
# ============================================================

class GitHubClient:
    def __init__(self, token: str):
        self.url = "https://api.github.com/graphql"
        self.headers = {"Authorization": f"Bearer {token}"}

    def run_query(self, query: str):
        """Run a GitHub GraphQL query with retries and rate-limit handling."""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = requests.post(self.url, json={"query": query}, headers=self.headers)

                # Handle rate limit
                if response.status_code == 403:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait_for = max(0, reset_time - time.time())
                    print(f"⏳ Rate limit hit. Waiting {wait_for:.2f}s before retrying...")
                    time.sleep(wait_for)
                    continue

                # Handle success
                if response.status_code == 200:
                    return response.json()

                print(f"⚠️ GitHub API error: {response.status_code} — {response.text}")
                time.sleep(2)

            except requests.exceptions.RequestException as e:
                print(f"⚠️ Network error (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(3)

        raise Exception("❌ All retry attempts failed after hitting GitHub API issues.")

# ============================================================
#  DATABASE LAYER
# ============================================================

class PostgresDB:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.setup_schema()

    def setup_schema(self):
        """Create repositories table if it doesn't exist."""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id SERIAL PRIMARY KEY,
            owner_name TEXT NOT NULL,
            repo_name TEXT NOT NULL,
            stars INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (owner_name, repo_name)
        );
        """)
        self.conn.commit()

    def upsert_repositories(self, repos):
        """Insert or update repository data efficiently."""
        for repo in repos:
            owner = repo['owner']['login']
            name = repo['name']
            stars = repo['stargazerCount']

            self.cursor.execute("""
            INSERT INTO repositories (owner_name, repo_name, stars)
            VALUES (%s, %s, %s)
            ON CONFLICT (owner_name, repo_name)
            DO UPDATE SET
                stars = EXCLUDED.stars,
                last_updated = CURRENT_TIMESTAMP;
            """, (owner, name, stars))
        self.conn.commit()

# ============================================================
#  CRAWLER (Main Logic)
# ============================================================

class GitHubCrawler:
    def __init__(self, client: GitHubClient, db: PostgresDB):
        self.client = client
        self.db = db

    def fetch_and_store_repos(self, limit=100000):
        """Fetch repositories and store them in Postgres."""
        all_repos = []
        has_next_page = True
        end_cursor = None

        while has_next_page and len(all_repos) < limit:
            print(f"📦 Fetching batch... (Total so far: {len(all_repos)})")

            query = f"""
            {{
                search (query: "stars:>10", type: REPOSITORY, first: 100 {f', after: "{end_cursor}"' if end_cursor else ''}) {{
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

            try:
                data = self.client.run_query(query)
                search = data["data"]["search"]
                repos = search["nodes"]

                self.db.upsert_repositories(repos)
                all_repos.extend(repos)

                has_next_page = search["pageInfo"]["hasNextPage"]
                end_cursor = search["pageInfo"]["endCursor"]

                # Short delay to stay under GitHub's secondary rate limits
                time.sleep(1.5)

            except Exception as e:
                print(f"❌ Error while fetching batch: {e}")
                time.sleep(3)

        print(f"✅ Completed! Total repositories processed: {len(all_repos)}")

# ============================================================
#  MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("❌ Missing GITHUB_TOKEN environment variable.")

        conn = psycopg2.connect(
            dbname='github_data',
            user='postgres',
            password='postgres',
            host='localhost',
            port='5432'
        )

        client = GitHubClient(token)
        db = PostgresDB(conn)
        crawler = GitHubCrawler(client, db)

        # 🔸 Fetch 50 repos for testing (must change to 100000 in final) *
        crawler.fetch_and_store_repos(limit=50)

    except Exception as e:
        print("❌ Unexpected error:", e)

    finally:
        if 'db' in locals():
            db.cursor.close()
        if 'conn' in locals():
            conn.close()
        print("🧹 Database connection closed.")
