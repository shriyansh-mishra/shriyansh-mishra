import os
import re
import requests
from collections import defaultdict

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


def fetch_repos():
    repos = []
    page = 1
    while True:
        url = f"{API_URL}/user/repos?per_page=100&page={page}&affiliation=owner"
        res = requests.get(url, headers=HEADERS)

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


def make_progress_bar(percentage, size=13):
    filled = int(size * percentage / 100)
    return "█" * filled + "░" * (size - filled)


def replace_badge_value(readme, badge_name, new_value):
    """
    Replace number inside a shields.io badge while keeping the rest intact.
    Example: badge_name = "Public%20Repos"
    """
    pattern = rf'({badge_name}-)([0-9]+(\.[0-9]+)?)([A-Za-z%]*)'
    return re.sub(pattern, rf'\1{new_value}\4', readme)


def main():
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

        total_size += repo["size"]

        langs = fetch_languages(repo["full_name"])
        for lang, val in langs.items():
            lang_stats[lang] += val

    total_commits = fetch_total_commits(USERNAME)

    total_bytes = sum(lang_stats.values())
    lang_percentages = (
        {lang: (count / total_bytes) * 100 for lang, count in lang_stats.items()}
        if total_bytes > 0
        else {}
    )

    # Read README.md
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    # --- Update badges ---
    readme = replace_badge_value(readme, "Public%20Repos", str(public_repos))
    readme = replace_badge_value(readme, "Private%20Repos", str(private_repos))
    readme = replace_badge_value(readme, "Total%20Line%20of%20code", f"{total_bytes/1e6:.2f}M")
    readme = replace_badge_value(readme, "Storage%20Used", f"{total_size/1024:.2f}MB")

    # --- Update language usage table ---
    table_pattern = re.compile(
        r"(\| Language \| % \| Progress \|[\s\S]+?)(</div>|<!--END_SECTION:dashboard-->)"
    )

    top5 = sorted(lang_percentages.items(), key=lambda x: x[1], reverse=True)[:5]

    new_table = "| Language | % | Progress |\n|----------|---|---------|\n"
    for lang, percent in top5:
        bar = make_progress_bar(percent)
        new_table += f"| {lang} | {percent:.2f}% | {bar} {percent:.2f}% |\n"

    readme = table_pattern.sub(new_table + r"\2", readme)

    # Write back to README.md
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)


if __name__ == "__main__":
    main()
