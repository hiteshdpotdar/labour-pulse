"""Site-wide settings. Edit these to rename the site or point it at your repository."""

import os

SITE_NAME = "Labour Pulse"
TAGLINE = "Struggles, law, theory and research on work around the world"

# Set automatically on GitHub Actions (owner/repo); the fallback is used when running on your own computer.
_REPO = os.environ.get("GITHUB_REPOSITORY", "YOUR-GITHUB-NAME/labour-pulse")
REPO_URL = f"https://github.com/{_REPO}"

# Optional: an email address sent to Crossref with each request, which puts us in its "polite" pool.
# Set it as a repository secret named CROSSREF_MAILTO (never committed).
CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "")

# How far back the site shows stories (the database keeps more).
SITE_DAYS = 180
