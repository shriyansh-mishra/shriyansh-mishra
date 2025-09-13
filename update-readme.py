import os
import requests
from collections import defaultdict

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
        res = requests.get(url, headers=HEADERS).json()
        if not res:
            break
        repos.extend(res)
        page += 1
    return repos


# Fetch language usage for a repo
def fetch_languages(repo_full_name):
    url = f"{API_URL}/repos/{repo_full_name}/languages"
    res = requests.get(url, headers=HEADERS)
    return res.json() if res.status_code == 200 else {}


# Fetch total commits across ALL repos by user
def fetch_total_commits(username):
    url = f"{API_URL}/search/commits?q=author:{username}"
    headers = {**HEADERS, "Accept": "application/vnd.github.cloak-preview"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get("total_count", 0)
    return 0


# Create progress bar for percentages
def make_progress_bar(percentage, size=20):
    filled = int(size * percentage / 100)
    return "█" * filled + "░" * (size - filled)


def main():
    repos = fetch_repos()
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
        f"- **Public Repos:** {public_repos}",
        f"- **Private Repos:** {private_repos}",
        f"- **Total Commits:** {total_commits}",
        f"- **Total LOC (bytes counted):** {total_bytes:,}",
        f"- **Storage Used:** {total_size/1024:.2f} MB\n",
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
