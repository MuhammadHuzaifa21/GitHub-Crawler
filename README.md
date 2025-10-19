# 🕸️ GitHub Crawler

This project implements a **GitHub Crawler** using GitHub’s GraphQL API to collect the number of stars for up to 100,000 repositories.
It respects rate limits, includes retry mechanisms, and stores data efficiently in PostgreSQL.

The project includes a **GitHub Actions CI/CD pipeline** that automates setup, crawling, and exporting results. All while respecting GitHub API rate limits and maintaining clean software architecture.

---

## 📂 Project Overview

### 🔹 What this crawler does:
- Fetches repository data (owner, name, and star count) using **GitHub’s GraphQL API**.
- Stores repository information in a **PostgreSQL** database.
- Automatically updates existing records without duplication.
- Handles **API rate limits** and includes a **retry mechanism**.
- Uses a **fetch_repositories, store_in_postgres** functions for fetching repos and storing the data in postgreSQL.

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

## 🚀 Features
- ✅ Uses GitHub GraphQL API (not REST)
- ✅ Bypasses the 1,000-result limit by splitting queries monthly
- ✅ Stores results in PostgreSQL
- ✅ Handles rate limits gracefully (pauses automatically)
- ✅ Includes retry on API/network errors
- ✅ Easy to understand (only two main functions)

---

## 🧱 Architecture
There are two main functions:
- fetch_repositories(): Fetches repository data from GitHub GraphQL API in monthly batches.
- store_in_postgres(): Saves or updates repositories in a PostgreSQL database.

The flow:
1. Generate monthly date ranges from 2014 → 2024.
2. For each month, use a GraphQL query to fetch up to 1,000 repos.
3. Continue until reaching 100,000 total repositories.
4. Store them into PostgreSQL.

## 🧠  How the 1,000 Limit is Solved
GitHub’s GraphQL search query allows fetching only 1,000 results per search. To bypass this, the crawler splits the data by creation date (monthly). Each monthly range gives up to 1,000 results, around 100 months yield 100,000 repositories.

Example GraphQL query:
```
{
  search(query: "created:2019-01-01..2019-02-01", type: REPOSITORY, first: 100) {
    nodes {
      name
      owner { login }
      stargazerCount
      createdAt
    }
  }
}
```

---

## ⚙️ Setup Instructions (Local Development)

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/MuhammadHuzaifa21/GitHub-Crawler.git
cd GitHub-Crawler
```

### 2️⃣ Install Dependencies
Create a virtual environment and install:
```bash
pip install -r requirements.txt
```

### 3️⃣ Create and Setup PostgreSQL Database
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
🔍 Fetching repos for created:2019-01-01..2020-01-01
📦 Total fetched so far: 6100
📦 Total fetched so far: 6200
    ...
    ...
📦 Total fetched so far: 100099
✅ Target reached: 100099 repositories.
💾 Stored 100099 repositories in PostgreSQL.
🧹 Database connection closed.
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

## 🧠 Key Code Components

### **1. get_query**
Handles GitHub GraphQL search query using filters.

### **2. handle_errors**
Handles errors raised in GraphQL search query response.

### **3. fetch_repositories**
Handles communication with the GitHub GraphQL API.

**Responsibilities:**
- Since GraphQL API can return only 1000 result/query.
- Uses filters based on months, so that we can query on approximately 100 months to get 100,000 results. 
- Uses retry mechanism in case of failures.

### **4. store_in_postgres**
Handles all interactions with the PostgreSQL database.

**Responsibilities:**
- Makes connection with postgres.
- Create the table schema for storing repositories data.
- Insert data into the respositories table.
- Uses constraint on unique name, no duplication allowed.
- If a name already exists, it will only update it's star count.

---

## 🧩 Rate Limiting & Retry Strategy

- GitHub GraphQL search endpoint `(search{})` can only return the first 1,000/query
- Script checks rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`).
- Automatically waits if the limit is near.
- Uses upto 3 retries in case of errors.

---

## 🧱 Database Schema (Flexible Design)

| Column         | Type         | Description                      |
|----------------|--------------|----------------------------------|
| id             | SERIAL       | Primary key                      |
| owner_name     | TEXT         | GitHub username                  |
| repo_name      | TEXT         | Repository name                  |
| stars          | INT          | Star count                       |
| created_at     | TIMESTAMP    | Repo Creation Time               |
| last_updated   | TIMESTAMP    | Last update time                 |

---

### 🔮 Future Schema Expansion
If we add new metadata (issues, PRs, comments), we can:
- Create new tables (`issues`, `pull_requests`, etc.)
- Use **foreign keys** to link to `repositories`.
- Update only affected rows (efficient incremental updates).

---

## 🧩 Clean Architecture & Best Practices

This project follows software engineering principles:

- **Separation of Concerns:** Clear distinction between functions, also used small separate functions to make code more clean.  
- **Retry + Resilience:** Failures are retried with backoff delay.  
- **Clean Folder Layout:** Codebase is modular, testable, and extendable.  

---

## 📊 Performance Optimization

- Fetches data in **paginated batches** (100 repos per query).  
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

| Error | Cause  | Fix |
|-------|--------|-----|
| `ON CONFLICT` error | Missing unique constraint | Ensure `UNIQUE(owner_name, repo_name)` in schema |
| API limit reached | Exceeded 1000 results/query | Wait or use a new token |
| Database connection refused | Postgres not running | Check host, port, or credentials |

---

## 🧑‍💻 Author
**Muhammad Huzaifa**  
Software Engineer | Web Developer | AI Agents | Tech Enthusiast
🌐 [GitHub Profile](https://github.com/MuhammadHuzaifa21)

---

## 🏁 License
This project is open-source and available under the **MIT License**.

