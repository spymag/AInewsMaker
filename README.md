# AInewsMaker

Fetches AI news from reputable websites and generates a summary report. This script can now leverage OpenAI's GPT model (gpt-5-nano) to create a condensed and analyzed version of the collected news.

## Features

*   **Multi-Source Aggregation**: Gathers news from various configured RSS feeds and websites.
*   **HTML Scraping Fallback**: If RSS feeds are unavailable or incomplete, the script attempts to scrape news directly from website HTML.
*   **AI-Powered Summarization**: Utilizes OpenAI's `gpt-5-nano` model to generate a concise and coherent news report from the fetched articles. This provides a high-level overview and analysis of the latest AI developments.
*   **Markdown Reports**: Outputs reports in Markdown format, suitable for easy reading and sharing.
*   **Automated Daily Reports**: Includes a GitHub Actions workflow to generate and commit a new report daily.

## Setup and Usage

### Prerequisites

*   Python 3.7+
*   pip (Python package installer)

### Local Execution

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/AInewsMaker.git
    cd AInewsMaker
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt 
    ```
    *(Note: If a `requirements.txt` is not yet present, you can install manually: `pip install feedparser requests beautifulsoup4 openai`)*

3.  **Set up OpenAI API Key:**
    For the AI-powered summarization to work, you need a valid API key from OpenAI.
    *   Set the `OPENAI_API_KEY` environment variable in your local environment:
        ```bash
        export OPENAI_API_KEY="your_openai_api_key_here"
        ```
        (On Windows, use `set OPENAI_API_KEY=your_openai_api_key_here`)
    *   If this variable is not set, the script will print an error and will not be able to generate the AI summary.

4.  **Run the script:**
    ```bash
    python news_fetcher.py
    ```
    *   To save the report to a file:
        ```bash
        python news_fetcher.py --output report.md
        ```
    *   The script will fetch news, then use the OpenAI API to generate a summary, and print it to the console or save it to the specified file.

## GitHub Actions Workflow

This repository includes a GitHub Actions workflow defined in `.github/workflows/daily_news_report.yml` that automates the news fetching and report generation process.

*   **Daily Schedule**: The workflow is scheduled to run daily at 06:00 UTC.
*   **Manual Trigger**: It can also be triggered manually from the Actions tab in the GitHub repository.
*   **Report Commits**: Generated reports are automatically committed to the `reports/` directory in the repository.

### Workflow Setup: `OPENAI_API_KEY` Secret

For the automated daily workflow to successfully generate AI-powered summaries, you **must** configure the `OPENAI_API_KEY` as a secret in your GitHub repository:

1.  Go to your repository on GitHub.
2.  Navigate to `Settings` > `Secrets and variables` > `Actions`.
3.  Click on `New repository secret`.
4.  Name the secret `OPENAI_API_KEY`.
5.  Paste your valid OpenAI API key into the value field.
6.  Click `Add secret`.

Without this secret, the workflow will fail when trying to access the OpenAI API.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make improvements, and submit pull requests.
