from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit

import argparse
import os
import psycopg2
import re
import requests
import time
import requests_cache

requests_cache.install_cache('cache')

re_spaces = re.compile(r'([\s\n]+)')

class StatusException(Exception):
    pass

class ContentException(Exception):
    pass

class Page(object):
    """Page represents a single page."""

    title = None
    soup = None
    url = None

    def __init__(self, url, data):
        self.url = url
        self.soup = BeautifulSoup(data, "html.parser")

        if not self.soup.title:
            self.title = url
        else:
            self.title = self.soup.title.get_text()

    def text(self):
        """Processes text to make it more friendly for storage."""
        if self.soup.text:
            return re_spaces.sub(" ", self.soup.text).strip()
        return None

    def _is_link_valid(self, link):
        parts = urlsplit(link)
        if parts.scheme in ['https', 'http']:
            return True
        return False

    def _fixup_link(self, link):
        parts = urlsplit(urljoin(self.url, link))

        # Remove trailing forward slash
        path = parts.path
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        return parts.scheme + "://" + parts.netloc + path

    def links(self):
        """Returns all links on the page, uniquely."""
        links = []
        for link in self.soup.find_all('a', href=True):
            href = self._fixup_link(link.get('href'))
            if not self._is_link_valid(href):
                continue
            elif href in links:
                continue

            print(href)
            links.append(href)

        return links

class Scraper(object):
    """Scraper is a bare-bones web scraper for the rover search engine."""

    session = None

    def __init__(self):
        self.session = requests.Session()

    def scrape(self, url):
        """Scrapes the HTML page at url."""
        urlp = urlsplit(url)
        path = urlp.path
        if path == '':
            path = '/'
        url = urlp.scheme + "://" + urlp.netloc + path
        print(url)

        with self.session.get(url, stream=True) as res:
            if res.status_code != 200:
                raise StatusException(res.status_code)
            elif not res.headers['Content-Type'].startswith('text/html'):
                raise ContentException(res.headers['Content-Type'])
            
            return Page(url, res.content)

    def recursive_scrape(self, url, seen, pages, depth=0, max_depth=3, delay=1.0):
        """Recursively scrapes url."""
        if url in seen:
            return

        print(url)

        page = self.scrape(url)

        seen.append(url)
        pages.append(page)

        if depth > max_depth:
            print(f"{url}: not following links because max depth reached")
            return

        for link in page.links():
            # Determine if page is under url. Ignore if not
            # TODO: gemini and gopher support
            if not is_same_origin(url, link):
                continue

            time.sleep(delay)

            try:
                self.recursive_scrape(link, seen, pages, depth=depth+1, max_depth=max_depth, delay=delay)
            except ContentException:
                seen.append(link)
                print(f"{link} failed because of content type")
            except StatusException:
                seen.append(link)
                print(f"{link} failed because of status")

def is_same_origin(left, right):
    ls = urlsplit(left)
    rs = urlsplit(right)
    return ls.netloc == rs.netloc

parser = argparse.ArgumentParser(description='web crawler')

parser.add_argument('url', type=str, help='url to crawl')
parser.add_argument('-d', '--depth', type=int, help='depth of pages to crawl (default: 3)', default=3)
parser.add_argument('-D', '--delay', type=float, help='delay between pages (default: 1.0)', default=1.0)

args = parser.parse_args()

with psycopg2.connect(os.environ['PGURL']) as pq: 
    sc = Scraper()

    domain = None
    with pq.cursor() as cur:
        cur.execute("SELECT id FROM domains WHERE url LIKE %s", ("%" + args.url + "%",))
        row = cur.fetchone()
        domain = row[0]

    seen = []
    pages = []

    sc.recursive_scrape(args.url, seen, pages, max_depth=args.depth, delay=args.delay)

    with pq.cursor() as cur:
        for page in pages:
            text = page.text()
            if not text:
                continue
            links = page.links()

            cur.execute("""
                INSERT INTO search(domain, url, title, body, last_updated) VALUES (%(domain)s, %(url)s, %(title)s, %(body)s, NOW())
                ON CONFLICT (url)
                DO UPDATE
                SET title = %(title)s, body = %(body)s, last_updated = NOW()
            """, {'domain': domain, 'url': page.url, 'title': page.title, 'body': page.text()})

            for link in page.links():
                if is_same_origin(link, page.url):
                    continue
                parts = urlsplit(link)

                dst_domain = parts.netloc
                if dst_domain.startswith("www."):
                    dst_domain = dst_domain[4:]

                cur.execute("""
                    INSERT INTO links(src_domain, src, dst_domain, dst) VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """,  (domain, page.url, dst_domain, link))

            pq.commit()

