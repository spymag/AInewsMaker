import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
    report = []
    for source in NEWS_SOURCES:
        report.append(f"## Source: {source['name']}\n")
        processed_successfully = False
        try:
            # Attempt RSS feed parsing
            feed = feedparser.parse(source['url'])
            if feed.entries:
                for entry in feed.entries[:5]: # Limit to 5 articles
                    title = entry.title
                    link = entry.link
                    summary = entry.summary if hasattr(entry, 'summary') else "Summary couldn't be retrieved from the feed."
                    report.append(f"### [{title}]({link})\nSummary: {summary}\n")
                processed_successfully = True
            
            if not processed_successfully:
                report.append(f"Could not fetch RSS feed or no entries found, trying HTML scraping for {source['name']}.\n")
                try:
                    html_url_to_fetch = source.get('html_url', source['url'].replace('/feed/', '').replace('/feed', '').replace('/rss/', ''))
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    response = requests.get(html_url_to_fetch, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    articles_found = 0
                    # Refined selectors: look for common article tags first.
                    # Then, within those, try to find titles (h1-h3 with a link, or a link that looks like a title)
                    # This is still generic but attempts to be a bit more targeted.
                    
                    # Try to find a main content area to reduce noise from headers/footers
                    main_content = soup.find('main') or soup.find('div', id='main-content') or soup.find('div', class_='main-content') or soup.find('div', role='main')
                    search_area = main_content if main_content else soup

                    # More generic selectors for sites like Stanford HAI news, trying common list patterns
                    possible_article_elements = search_area.find_all(['article', 'div.post', 'div.entry', 'li.item', 'div.article-preview', 'div.news-item', 'div.card-item'], limit=20)
                    if not possible_article_elements:
                        possible_article_elements = search_area.find_all('div', class_=lambda x: x and ('post' in x or 'article' in x or 'item' in x or 'news' in x), limit=20)
                    if not possible_article_elements:
                        possible_article_elements = search_area.find_all('div', limit=25) # Last resort, broader div search

                    for item in possible_article_elements:
                        title_text = ""
                        link_href = ""
                        
                        # Attempt 1: Find h_tag with a link inside or as itself
                        h_tags = item.find(['h1', 'h2', 'h3', 'h4'])
                        if h_tags:
                            a_in_h = h_tags.find('a', href=True)
                            if a_in_h:
                                title_text = h_tags.get_text(strip=True)
                                link_href = a_in_h['href']
                            elif h_tags.name == 'a' and h_tags.has_attr('href'): # The h_tag itself is a link
                                title_text = h_tags.get_text(strip=True)
                                link_href = h_tags['href']
                        
                        # Attempt 2: If no h_tag found, find the first prominent link that might be a title
                        if not title_text:
                            links = item.find_all('a', href=True, limit=5) # Look for a few links
                            for l in links:
                                potential_title = l.get_text(strip=True)
                                # Filter out short/generic links like "Read more", "Continue reading"
                                if potential_title and len(potential_title) > 25 and not any(skip_word in potential_title.lower() for skip_word in ['read more', 'continue', 'comments']):
                                    title_text = potential_title
                                    link_href = l['href']
                                    break # Take the first suitable one

                        if title_text and link_href and articles_found < 5:
                            if not link_href.startswith('http'):
                                link_href = urljoin(html_url_to_fetch, link_href)
                            
                            summary = "Summary not available via HTML scraping."
                            p_tag = item.find('p')
                            if p_tag:
                                summary_text = p_tag.get_text(strip=True)
                                if summary_text and len(summary_text) > 20: # Basic check for meaningful summary
                                    summary = summary_text

                            report.append(f"### [{title_text}]({link_href})\nSummary: {summary}\n")
                            articles_found += 1
                        if articles_found >= 5:
                            break
                    
                    if articles_found == 0:
                        report.append("Could not extract articles via HTML scraping (no suitable elements found).\n")
                    else:
                        processed_successfully = True

                except requests.exceptions.RequestException as req_e:
                    report.append(f"HTML Scraping failed for {source['name']} (Request Error): {req_e}\n")
                except Exception as scrape_e:
                    report.append(f"HTML Scraping failed for {source['name']} (Parsing Error): {scrape_e}\n")
            
        except Exception as e: 
            report.append(f"Could not process source {source['name']} due to an unexpected error: {e}\n")
        
        if not processed_successfully: # Check if either RSS or HTML scraping was successful
             report.append(f"Failed to retrieve news from {source['name']}.\n")
        report.append("---\n")
    
    return "".join(report)

if __name__ == "__main__":
    news_report = fetch_news()
    print(news_report)
