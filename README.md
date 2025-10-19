# 🕸️ GitHub Crawler

This project is a **GitHub repository crawler** built using Python, PostgreSQL, and GitHub's GraphQL API.  
It collects repository data (e.g., stars, owner, repo name) for a large number of repositories and stores them in a PostgreSQL database.

The project includes a **GitHub Actions CI/CD pipeline** that automates setup, crawling, and exporting results — all while respecting GitHub API rate limits and maintaining clean software architecture.

---

## 📂 Project Overview

### 🔹 What this crawler does:
- Fetches repository data (owner, name, and star count) using **GitHub’s GraphQL API**.
- Stores repository information in a **PostgreSQL** database.
- Automatically updates existing records without duplication.
- Handles **API rate limits** and includes a **retry mechanism**.
- Uses a **class-based, modular architecture** with clear separation of concerns.

---

## 🏗️ Folder Structure

```
├── .github/
│   └── workflows/
│       └── crawler.yml         # GitHub Actions workflow file
├── github_crawler.py           # Main Python File
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## ⚙️ Setup Instructions (Local Development)

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/MuhammadHuzaifa21/GitHub-Crawler.git
cd GitHub-Crawler
```

### 2️⃣ Create and Setup PostgreSQL Database
Make sure PostgreSQL is installed and running.

```bash
psql -U postgres
CREATE DATABASE github_data;
\c github_data
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    owner_name TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    stars INT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (owner_name, repo_name)
);
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Set GitHub Token as Environment Variable
You’ll need a **GitHub Personal Access Token (classic)** to make API calls.

```bash
export GITHUB_TOKEN=your_personal_access_token
```
or add it in `.env` file
```bash
GITHUB_TOKEN = your_token_here
```

### 5️⃣ Run the Script
```bash
python github_crawler.py
```

You should see output like:
```
Fetching batch... (Total: 0)
Fetching batch... (Total: 10)
✅ Saved 10 repositories into PostgreSQL!
```

---

## ⚙️ Setup via GitHub Actions

This project includes a CI/CD pipeline defined in `.github/workflows/crawler.yml`.

### 🔄 What it does automatically:
1. Spins up a **PostgreSQL service container**.
2. Installs dependencies.
3. Runs schema setup.
4. Executes `github_crawler.py` to fetch repositories.
5. Dumps database contents (CSV or JSON) as a **GitHub Actions artifact**.

You can view workflow runs under the **"Actions" tab** of your repository.

---

## 🧠 Key Code Components (Class-Based Design)

### **1. DatabaseManager**
Handles all interactions with the PostgreSQL database.

**Responsibilities:**
- Creates and initializes tables.
- Inserts or updates repository data using `ON CONFLICT`.
- Uses transactions and commits for efficiency.
- Closes DB connections cleanly to prevent leaks.

### **2. GitHubCrawler**
Handles communication with the GitHub GraphQL API.

**Responsibilities:**
- Sends paginated GraphQL queries to fetch repository data.
- Respects GitHub’s rate limits and pauses when necessary.
- Implements a retry mechanism with exponential backoff.
- Returns clean, structured repository data.

### **3. CrawlerService**
Coordinates both the API and database layers.

**Responsibilities:**
- Calls `GitHubCrawler` to fetch repositories.
- Passes normalized data to `DatabaseManager` for storage.
- Logs progress, handles exceptions, and manages crawl loop.

This modular structure follows **clean architecture** principles, each class is testable and independently replaceable.

---

## 🧩 Rate Limiting & Retry Strategy

- GitHub API allows up to **5000 requests/hour** for authenticated users.
- Script checks rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`).
- Automatically waits if the limit is near.
- Uses **exponential backoff** for retries in case of errors.

Example:
```python
for attempt in range(max_retries):
    try:
        response = requests.post(...)
        if response.status_code == 200:
            break
        else:
            raise Exception("Bad response")
    except Exception as e:
        wait = 2 ** attempt
        time.sleep(wait)
```

---

## 🧱 Database Schema (Flexible Design)

| Column        | Type         | Description                     |
|----------------|--------------|----------------------------------|
| id             | SERIAL       | Primary key                      |
| owner_name     | TEXT         | GitHub username                  |
| repo_name      | TEXT         | Repository name                  |
| stars          | INT          | Star count                       |
| last_updated   | TIMESTAMP    | Last update time                 |

### 🔮 Future Schema Expansion
If we add new metadata (issues, PRs, comments), we can:
- Create new tables (`issues`, `pull_requests`, etc.)
- Use **foreign keys** to link to `repositories`.
- Update only affected rows (efficient incremental updates).

---

## 🧩 Clean Architecture & Best Practices

This project follows software engineering principles:

- **Separation of Concerns:** Clear distinction between API, database, and orchestration layers.  
- **Immutability:** Repository data is not overwritten unnecessarily.  
- **Retry + Resilience:** Failures are retried with backoff delay.  
- **Anti-Corruption Layer:** GitHub API responses are transformed before saving.  
- **Clean Folder Layout:** Codebase is modular, testable, and extendable.  

---

## 📊 Performance Optimization

- Fetches data in **paginated batches** (10 repos per query).  
- Minimizes DB writes using **UPSERT** via `ON CONFLICT`.  
- Can scale further using **async calls** or multiple parallel workers.  

---

## 🚀 Future Improvements

- Async fetching using `aiohttp` for faster data collection.  
- Export daily data dumps to AWS S3 or Google Cloud Storage.  
- Add Dockerfile for containerized runs.  
- Add unit tests for all classes.  

---

## 🧰 Troubleshooting

| Error | Cause | Fix |
|-------|--------|-----|
| `ON CONFLICT` error | Missing unique constraint | Ensure `UNIQUE(owner_name, repo_name)` in schema |
| API limit reached | Exceeded 5000 requests/hour | Wait or use a new token |
| Database connection refused | Postgres not running | Check host, port, or credentials |

---

## 🧑‍💻 Author
**Muhammad Huzaifa**  
Software Engineer | Web Developer | Tech Enthusiast  
🌐 [GitHub Profile](https://github.com/MuhammadHuzaifa21)

---

## 🏁 License
This project is open-source and available under the **MIT License**.

