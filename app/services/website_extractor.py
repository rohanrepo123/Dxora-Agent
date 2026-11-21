"""Collect readable evidence from the submitted page and related same-site pages."""

import os
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup
from fastapi import HTTPException
from playwright.sync_api import sync_playwright

from app.schemas import Page, WebsiteEvidence
from app.utils.validators import fetch_html


def collect_website(url: str, max_pages: int = 3) -> WebsiteEvidence:
    """Fetch up to three pages and use sync Playwright to extract visible text."""
    home_url, home_html = fetch_html(url)
    home = BeautifulSoup(home_html, "html.parser")
    related_urls = []
    for link in home.select("a[href]"):
        target = urldefrag(urljoin(home_url, link["href"]))[0]
        label = (link.get_text(" ", strip=True) + " " + urlsplit(target).path).lower()
        if urlsplit(target).netloc == urlsplit(home_url).netloc and target != home_url:
            if any(word in label for word in ("service", "product", "solution", "about")):
                related_urls.append(target)
    urls = [home_url] + list(dict.fromkeys(related_urls))[:max_pages - 1]

    pages = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROME_PATH") or None)
        try:
            # Browser networking stays disabled; HTML is retrieved by the
            # validator, which checks the destination and pins the public IP.
            context = browser.new_context(java_script_enabled=False, offline=True,
                                          service_workers="block")
            context.route("**/*", lambda route: route.abort())
            tab = context.new_page()
            for page_url in urls:
                html = home_html if page_url == home_url else fetch_html(page_url)[1]
                soup = BeautifulSoup(html, "html.parser")
                description = soup.select_one('meta[name="description" i]')
                meta = description.get("content", "")[:500] if description else ""
                for tag in soup.select("script, nav, footer, iframe, form, template, meta[http-equiv]"):
                    tag.decompose()
                tab.set_content(str(soup), wait_until="domcontentloaded", timeout=6000)
                lines = tab.locator("body").inner_text().splitlines()
                text = "\n".join(dict.fromkeys(line.strip() for line in lines if line.strip()))[:10000]
                pages.append(Page(url=page_url, title=tab.title()[:300],
                                  meta_description=meta, text=text))
        finally:
            browser.close()

    if sum(len(page.text) for page in pages) < 100:
        raise HTTPException(422, "Too little readable content. Try a descriptive service page.")
    return WebsiteEvidence(pages=pages)

