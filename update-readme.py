import os
import requests
from collections import defaultdict

# Try to load from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")
API_URL = "https://api.github.com"

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}


# Fetch all repos owned by the user
def fetch_repos():
    repos = []
    page = 1
    while True:
        url = f"{API_URL}/user/repos?per_page=100&page={page}&affiliation=owner"
        res = requests.get(url, headers=HEADERS)
        
        # Check if request was successful
        if res.status_code != 200:
            print(f"Error fetching repos: {res.status_code} - {res.text}")
            break
            
        try:
            data = res.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error parsing JSON response: {res.text}")
            break
            
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


# Fetch language usage for a repo
def fetch_languages(repo_full_name):
    url = f"{API_URL}/repos/{repo_full_name}/languages"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        try:
            return res.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error parsing languages for {repo_full_name}: {res.text}")
            return {}
    else:
        print(f"Error fetching languages for {repo_full_name}: {res.status_code} - {res.text}")
        return {}


# Fetch total commits across ALL repos by user
def fetch_total_commits(username):
    url = f"{API_URL}/search/commits?q=author:{username}"
    headers = {**HEADERS, "Accept": "application/vnd.github.cloak-preview"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        try:
            return res.json().get("total_count", 0)
        except requests.exceptions.JSONDecodeError:
            print(f"Error parsing commits response: {res.text}")
            return 0
    else:
        print(f"Error fetching commits: {res.status_code} - {res.text}")
        return 0


# Create progress bar for percentages
def make_progress_bar(percentage, size=20):
    filled = int(size * percentage / 100)
    return "█" * filled + "░" * (size - filled)


def main():
    # Debug information
    print(f"GitHub Token present: {bool(GITHUB_TOKEN)}")
    print(f"Username: {USERNAME}")
    print(f"API URL: {API_URL}")
    
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable is not set!")
        return
    
    if not USERNAME:
        print("Error: GITHUB_USERNAME environment variable is not set!")
        return
    
    repos = fetch_repos()
    print(f"Fetched {len(repos)} repositories")
    
    if not repos:
        print("No repositories found. Check your token permissions.")
        return
    
    total_size = 0
    lang_stats = defaultdict(int)
    public_repos = 0
    private_repos = 0

    for repo in repos:
        if repo["private"]:
            private_repos += 1
        else:
            public_repos += 1

        total_size += repo["size"]  # Size is in KB

        # Collect languages
        langs = fetch_languages(repo["full_name"])
        for lang, val in langs.items():
            lang_stats[lang] += val

    # Calculate total commits with 1 API call
    total_commits = fetch_total_commits(USERNAME)

    # Calculate language percentages
    total_bytes = sum(lang_stats.values())
    lang_percentages = {
        lang: (count / total_bytes) * 100 for lang, count in lang_stats.items()
    } if total_bytes > 0 else {}

    # Read README.md
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    # Build stats section
    stats_section = [
        "## 📊 GitHub Dashboard\n",
        f"![Public Repos](https://img.shields.io/badge/Public%20Repos-{public_repos}-blue?style=for-the-badge&logo=github)",
        f"![Private Repos](https://img.shields.io/badge/Private%20Repos-{private_repos}-lightgrey?style=for-the-badge&logo=github)",
        f"![Total LOC](https://img.shields.io/badge/Total%20LOC-{total_bytes / 1000000:.2f}M-yellow?style=for-the-badge&logo=files)",
        f"![Storage Used](https://img.shields.io/badge/Storage%20Used-{total_size / 1024:.2f}MB-orange?style=for-the-badge&logo=databricks)\n",
    "### 🖥️ Language Usage\n",
        "| Language | % | Progress |\n|----------|----|-----------|\n"
    ]

    for lang, percent in sorted(lang_percentages.items(), key=lambda x: x[1], reverse=True):
        bar = make_progress_bar(percent)
        stats_section.append(f"| {lang} | {percent:.2f}% | {bar} {percent:.2f}% |")

    stats_content = "\n".join(stats_section)

    # Replace old stats between markers
    start_marker = "<!--START_SECTION:dashboard-->"
    end_marker = "<!--END_SECTION:dashboard-->"
    new_readme = (
        readme.split(start_marker)[0]
        + start_marker + "\n" + stats_content + "\n" + end_marker
        + readme.split(end_marker)[-1]
    )

    # Write back to README.md
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)


if __name__ == "__main__":
    main()
