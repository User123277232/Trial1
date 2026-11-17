# Market Brief

A desktop-first, light-themed financial news reader. Free to host using **GitHub Pages** and free to update using scheduled **GitHub Actions** in a public repository.

## What it does

- Collects titles, short RSS-supplied descriptions, publication times and source links from multiple public publisher and official feeds.
- Produces an **automatically ranked daily briefing of up to eight headlines** (only on days when sufficient content is available).
- Retains up to **seven daily briefings**. Does not replace an existing briefing during the day.
- Shows major updates published after that day's briefing, plus chronological news with filters and search.
- Groups sufficiently similar headlines, linking to multiple original reports when detected.
- Stores a customizable watchlist and saved headline IDs in local browser storage.
- Avoids fabricated news, AI-generated predictions, unsourced summaries and invented stock prices.

## Publish online for $0 with GitHub Pages

1. Create a **new public repository** on GitHub named `market-brief` (or another name).
2. Upload *all files and folders from this project* to the repository root. Keep `.github/workflows/update-news.yml` and `.nojekyll` (hidden folders/files may need to be shown in your file manager).
3. Under **Settings → Pages**, select **GitHub Actions** as the publishing source. This project deploys its own generated news files as a Pages artifact on every scheduled run.
4. Under **Settings → Actions → General → Workflow permissions**, select **Read and write permissions** if available. If organizational controls prevent this, adjust repository permissions to allow the scheduled bot to commit `data/*.json`.
5. Open **Actions → Update and publish Market Brief → Run workflow** to collect the first headlines. Wait until it finishes successfully. For a brand-new repo, scheduled workflows may require the workflow file on the default branch.
6. Visit `https://YOUR_GITHUB_USERNAME.github.io/market-brief/` (replace the username and repository name appropriately). The initial site and content updates may take several minutes to publish.

The schedule runs at minutes 7 and 37 of each hour in UTC, and prepares a new briefing after 6 AM Eastern Time. GitHub scheduled workflows **may be delayed or skipped**, especially under heavy load. The website checks its own updated data periodically when open; it does not independently fetch publisher feeds from your browser.

### Free-tier and tradeoffs

GitHub Pages is publicly accessible, not password protected. GitHub Actions minutes are free for public repositories using standard runners. Watchlists and saves are browser-local. Headlines are sourced from RSS feeds, and some publishers may limit or block automated requests. The workflow keeps previously collected stories when a source fails, and labels last successful update. It does **not** include live share prices, economic calendar data, full-text copyrighted articles, sourced LLM synthesis, or guaranteed 30-minute refreshes.

### Local preview

```bash
python -m http.server 8080
```

Open http://localhost:8080. You can manually gather news on a computer with network access using:

```bash
pip install -r requirements.txt
python scripts/update_news.py
```

The checked-in `data/news.json` and `data/briefings.json` are **intentionally empty**. They will populate after the first successful workflow run. A demo preview should not be mistaken for current news.

## Responsible data practices

Sources in `scripts/update_news.py` are public RSS endpoints. This tool displays metadata, a limited feed excerpt (up to 220 characters), and links to source content. **Review each provider's current terms before expanding or redistributing this project.** Names and trademarks belong to their respective owners. This is independent software, not affiliated with publishers, and not investment advice.

### Architecture

- `index.html`, `styles.css`, `app.js`: responsive static news dashboard.
- `scripts/update_news.py`: feed collection, deduplication, ranking and seven-day retention.
- `.github/workflows/update-news.yml`: collection job every 30 minutes, committing changed JSON files.
- `data/news.json`, `data/briefings.json`: generated files consumed by the browser.

## Next features (not implemented)

- Verified free source for delayed market prices and returns.
- More sophisticated story clustering, backed by source evidence.
- Optional AI summaries and sourced Q&A without paid usage.
- Economic releases calendar from verified data.
