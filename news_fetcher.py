#!/usr/bin/env python3
import sys
if sys.version_info < (3, 8):
    sys.stderr.write("This script requires Python 3.8+ (f-strings and annotations).\n")
    sys.exit(1)

import argparse
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import openai
import os
import json
import random


def load_all_sources():
    """Load all sources from environment variable AI_SOURCES_JSON or local sources.json.

    Environment variable takes precedence. Local file is ignored if env var present.
    Returns list of dicts (may be empty if not found/parse error)."""
    env_json = os.getenv("AI_SOURCES_JSON")
    if env_json:
        try:
            data = json.loads(env_json)
            if isinstance(data, list):
                return data[:50]
        except Exception:
            pass
    # Fallback: local file
    local_path = os.path.join(os.path.dirname(__file__), 'sources.json')
    if os.path.isfile(local_path):
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data[:50]
        except Exception:
            return []
    return []

def select_daily_sources(max_sources: int = 5):
    """Select up to max_sources from the pool in a deterministic, date-seeded way.
    Ensures reproducibility for the day and variation across days."""
    all_sources = load_all_sources()
    today_seed = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    rnd = random.Random(today_seed)
    if max_sources >= len(all_sources):
        return all_sources
    return rnd.sample(all_sources, k=max_sources)


def fetch_news(max_daily_sources: int = 5):
    articles_data = []
    selected_sources = select_daily_sources(max_daily_sources)
    for source in selected_sources:
        processed_successfully = False
        try:
            # Attempt RSS feed parsing
            feed = feedparser.parse(source['url'])
            if feed.entries:
                for entry in feed.entries[:5]: # Limit to 5 articles
                    title = entry.title
                    link = entry.link
                    summary = entry.summary if hasattr(entry, 'summary') else "Summary couldn't be retrieved from the feed."
                    articles_data.append({
                        "source_name": source['name'],
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
                processed_successfully = True
            
            if not processed_successfully:
                # Fallback to HTML scraping if RSS fails or has no entries
                # print(f"Could not fetch RSS feed or no entries found for {source['name']}, trying HTML scraping.")
                try:
                    html_url_to_fetch = source.get('html_url', source['url'].replace('/feed/', '').replace('/feed', '').replace('/rss/', ''))
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    response = requests.get(html_url_to_fetch, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    articles_found_count = 0
                    main_content = soup.find('main') or soup.find('div', id='main-content') or soup.find('div', class_='main-content') or soup.find('div', role='main')
                    search_area = main_content if main_content else soup

                    possible_article_elements = search_area.find_all(['article', 'div.post', 'div.entry', 'li.item', 'div.article-preview', 'div.news-item', 'div.card-item'], limit=20)
                    if not possible_article_elements:
                        possible_article_elements = search_area.find_all('div', class_=lambda x: x and ('post' in x or 'article' in x or 'item' in x or 'news' in x), limit=20)
                    if not possible_article_elements:
                        possible_article_elements = search_area.find_all('div', limit=25)

                    for item in possible_article_elements:
                        title_text = ""
                        link_href = ""
                        
                        h_tags = item.find(['h1', 'h2', 'h3', 'h4'])
                        if h_tags:
                            a_in_h = h_tags.find('a', href=True)
                            if a_in_h:
                                title_text = h_tags.get_text(strip=True)
                                link_href = a_in_h['href']
                            elif h_tags.name == 'a' and h_tags.has_attr('href'):
                                title_text = h_tags.get_text(strip=True)
                                link_href = h_tags['href']
                        
                        if not title_text:
                            links = item.find_all('a', href=True, limit=5)
                            for l_tag in links:
                                potential_title = l_tag.get_text(strip=True)
                                if potential_title and len(potential_title) > 25 and not any(skip_word in potential_title.lower() for skip_word in ['read more', 'continue', 'comments']):
                                    title_text = potential_title
                                    link_href = l_tag['href']
                                    break

                        if title_text and link_href and articles_found_count < 5:
                            if not link_href.startswith('http'):
                                link_href = urljoin(html_url_to_fetch, link_href)
                            
                            summary_text_scraped = "Summary not available via HTML scraping."
                            p_tag = item.find('p')
                            if p_tag:
                                current_summary = p_tag.get_text(strip=True)
                                if current_summary and len(current_summary) > 20:
                                    summary_text_scraped = current_summary
                            
                            articles_data.append({
                                "source_name": source['name'],
                                "title": title_text,
                                "link": link_href,
                                "summary": summary_text_scraped
                            })
                            articles_found_count += 1
                        if articles_found_count >= 5:
                            break
                    
                    if articles_found_count > 0:
                        processed_successfully = True
                    # else:
                        # print(f"Could not extract articles via HTML scraping for {source['name']} (no suitable elements found).")

                except requests.exceptions.RequestException as req_e:
                    # print(f"HTML Scraping failed for {source['name']} (Request Error): {req_e}")
                    pass # Silently fail for this source if scraping fails
                except Exception as scrape_e:
                    # print(f"HTML Scraping failed for {source['name']} (Parsing Error): {scrape_e}")
                    pass # Silently fail

        except Exception as e: 
            # print(f"Could not process source {source['name']} due to an unexpected error: {e}")
            pass # Silently fail for this source if any other error occurs
        
        # if not processed_successfully:
            # print(f"Failed to retrieve news from {source['name']}.")
    
    return articles_data

def generate_ai_report(articles_data):
    client = openai.OpenAI() # API key picked from OPENAI_API_KEY env var
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    prompt_parts = [
        "Please generate a concise news report (max 1 page, ~500 words) summarizing the following articles.",
        f"The report MUST have a main title formatted as an H1 markdown header, like this: '# AI News Report for {current_date}'.",
        "All subsequent sections must use H2 headers, like this: '## Section Title'.",
        "When you cite information from an article, you **must** make the source name a clickable Markdown link pointing to the article's URL. The format is `[Source Name](URL)`. For example, a citation for an article from 'Tech Chronicles' should be `[Tech Chronicles](https://example.com/news/latest-ai)`.",
        "The output must be well-formatted, readable Markdown.",
        "\nHere is the list of news articles:\n"
    ]
    for i, article in enumerate(articles_data):
        prompt_parts.append(f"Article {i+1}:")
        prompt_parts.append(f"Source: {article['source_name']}")
        prompt_parts.append(f"Title: {article['title']}")
        prompt_parts.append(f"Link: {article['link']}")
        prompt_parts.append(f"Summary: {article['summary']}\n")

    prompt_string = "\n".join(prompt_parts)

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano", # Using the specified model
            messages=[
                {"role": "system", "content": "You are a news analyst compiling a report."},
                {"role": "user", "content": prompt_string}
            ]
        )
        ai_content = response.choices[0].message.content
        return ai_content
    except Exception as e:
        return f"Error generating AI report: {e}\n\nShowing raw data instead:\n" + "\n".join([f"Title: {a['title']}, Link: {a['link']}" for a in articles_data])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetches AI news, generates a report using OpenAI, and compiles it in Markdown.")
    parser.add_argument(
        "-o", "--output",
        help="Path to save the news report (e.g., report.md). Prints to stdout if not provided.",
        default=None,
        metavar="FILEPATH"
    )
    parser.add_argument(
        "-s", "--sources",
        type=int,
        default=5,
        help="Maximum number of random sources to use today (default 5, <=50)."
    )
    args = parser.parse_args()

    # Check for API key (OpenAI library does this, but good for early user feedback if missing)
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: The OPENAI_API_KEY environment variable is not set.")
        print("Please set it before running the script.")
        exit(1) # Exit if key is not found

    articles = fetch_news(max_daily_sources=args.sources)
    
    if not articles:
        print("No articles fetched. Exiting.")
        exit(0)

    ai_generated_report = generate_ai_report(articles)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(ai_generated_report)
            print(f"Report saved to {args.output}")
        except IOError as e:
            print(f"Error writing report to file {args.output}: {e}")
            print("\nReport content:\n")
            print(ai_generated_report) # Print to stdout if file writing fails
    else:
        print(ai_generated_report)
