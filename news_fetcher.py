import argparse
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import openai
import os

NEWS_SOURCES = [
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "html_url": "https://www.technologyreview.com"
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "html_url": "https://venturebeat.com/category/ai/"
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/artificial-intelligence/index.xml",
        "html_url": "https://www.theverge.com/ai" # Last attempt for The Verge URL
    },
    {
        "name": "Ars Technica AI",
        "url": "https://arstechnica.com/information-technology/artificial-intelligence/feed/",
        "html_url": "https://arstechnica.com/information-technology/artificial-intelligence/"
    },
    {
        "name": "Stanford HAI News",
        "url": "https://hai.stanford.edu/news/feed",
        "html_url": "https://hai.stanford.edu/news"
    }
]

def fetch_news():
    articles_data = []
    for source in NEWS_SOURCES:
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

    prompt_parts = ["Here is a list of news articles:\n"]
    for i, article in enumerate(articles_data):
        prompt_parts.append(f"Article {i+1}:")
        prompt_parts.append(f"Source: {article['source_name']}")
        prompt_parts.append(f"Title: {article['title']}")
        prompt_parts.append(f"Link: {article['link']}")
        prompt_parts.append(f"Summary: {article['summary']}\n")

    prompt_parts.append("Please generate a concise news report (max 1 page, ~500 words) summarizing these articles.")
    prompt_parts.append(
        "When you cite information from an article in your summary, you **must** make the source name a clickable Markdown link pointing directly to the article's URL. "
        "The format **must** be `[Source Name](actual_article_URL)`. "
        "For example, if a point comes from an article from 'Tech Chronicles' with the URL 'https://example.com/news/latest-ai', "
        "the citation in your report should look exactly like this: `[Tech Chronicles](https://example.com/news/latest-ai)`. "
        "Do not write '[Source: ..., Link: ...]' or just the URL text. Use the precise `[DisplayName](URL)` Markdown hyperlink format."
    )
    prompt_parts.append("The output should be in well-formatted, readable Markdown.")
    prompt_string = "\n".join(prompt_parts)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano", # Using the specified model
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
    args = parser.parse_args()

    # Check for API key (OpenAI library does this, but good for early user feedback if missing)
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: The OPENAI_API_KEY environment variable is not set.")
        print("Please set it before running the script.")
        exit(1) # Exit if key is not found

    articles = fetch_news()
    
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
