# AInewsMaker

Fetches AI news from reputable websites and generates a summary report. This script can now leverage OpenAI's GPT model (gpt-5-nano) to create a condensed and analyzed version of the collected news.

## Features

* **Dynamic Multi-Source Aggregation**: Builds a pool (up to 50) of AI / ML / tech news feeds and randomly selects a small subset daily.
* **HTML Scraping Fallback**: If RSS feeds are unavailable or incomplete, the script attempts to scrape news directly from website HTML.
* **AI-Powered Summarization**: Utilizes OpenAI's `gpt-5-nano` model to generate a concise and coherent news report from the fetched articles. This provides a high-level overview and analysis of the latest AI developments.
* **Markdown Reports**: Outputs reports in Markdown format, suitable for easy reading and sharing.
* **Automated Daily Reports**: Includes a GitHub Actions workflow to generate and commit a new report daily.
* **Deterministic Daily Variety**: Each day (UTC) up to 5 sources are chosen via a date-seeded random selection for variety while remaining reproducible.
* **Configurable Source Pool**: Provide sources via `AI_SOURCES_JSON` env var (GitHub secret) or a local `sources.json` (ignored by git) for development.

## Setup and Usage

### Prerequisites

* Python 3.7+
* pip (Python package installer)

### Local Execution

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/AInewsMaker.git
   cd AInewsMaker
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt 
   ```

   *(Note: If a `requirements.txt` is not yet present, you can install manually: `pip install feedparser requests beautifulsoup4 openai`)*

3. **Set up OpenAI API Key:**

   For the AI-powered summarization to work, you need a valid API key from OpenAI.
   * Set the `OPENAI_API_KEY` environment variable in your local environment:

     ```bash
     export OPENAI_API_KEY="your_openai_api_key_here"
     ```

     (On Windows, use `set OPENAI_API_KEY=your_openai_api_key_here`)
   * If this variable is not set, the script will print an error and will not be able to generate the AI summary.

4. **Run the script:**

   ```bash
   python news_fetcher.py
   ```

   * To save the report to a file:

     ```bash
     python news_fetcher.py --output report.md
     ```

   * To adjust how many random sources are used today (default 5, max 50):

     ```bash
     python news_fetcher.py --sources 8 --output report.md
     ```

     The selection is seeded by the current UTC date, so the same set of sources is used for all runs within the same day, then changes the next day.

## Source Configuration

The script loads its pool of news sources in this priority order:

1. `AI_SOURCES_JSON` environment variable (expected to contain a JSON array of source objects with `name`, `url`, `html_url`).
2. Local `sources.json` file (placed in the project root and ignored by git).

If neither is present or valid, no sources will be loaded and the script will exit with zero articles.

### Example `AI_SOURCES_JSON` value

```json
[{"name":"MIT Technology Review","url":"https://www.technologyreview.com/feed/","html_url":"https://www.technologyreview.com"}]
```

### Local Development

Create a `sources.json` (already in `.gitignore`) containing an array of sources for experimentation. In production (GitHub Actions), define a repository secret named `AI_SOURCES_JSON` with the full list.

The script will fetch news, then use the OpenAI API to generate a summary, and print it to the console or save it to the specified file.

## GitHub Actions Workflow

This repository includes a GitHub Actions workflow defined in `.github/workflows/daily_news_report.yml` that automates the news fetching and report generation process.

* **Daily Schedule**: The workflow is scheduled to run daily at 06:00 UTC.
* **Manual Trigger**: It can also be triggered manually from the Actions tab in the GitHub repository.
* **Report Commits**: Generated reports are automatically committed to the `reports/` directory in the repository.

### Workflow Setup: `OPENAI_API_KEY` Secret

For the automated daily workflow to successfully generate AI-powered summaries, you **must** configure the `OPENAI_API_KEY` as a secret in your GitHub repository:

1. Go to your repository on GitHub.
2. Navigate to `Settings` > `Secrets and variables` > `Actions`.
3. Click on `New repository secret`.
4. Name the secret `OPENAI_API_KEY`.
5. Paste your valid OpenAI API key into the value field.
6. Click `Add secret`.

Without this secret, the workflow will fail when trying to access the OpenAI API.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make improvements, and submit pull requests.
