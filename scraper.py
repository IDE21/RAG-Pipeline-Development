
# scraper.py
import json, time, re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

PRODUCTS_BASE = "https://www.kddc.com/product/"
CAREERS_BASE  = "https://career.kddc.com/"
HEADERS       = {"User-Agent": "Mozilla/5.0 (compatible; RAGBot/1.0; +https://example.org)"}

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def clean_text(x: str) -> str:
    import re
    return re.sub(r"\s+", " ", (x or "").strip())

def scrape_product_categories(max_categories=2):
    soup = get_soup(PRODUCTS_BASE)
    cat_links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/product/" in href and href != PRODUCTS_BASE:
            full = urljoin(PRODUCTS_BASE, href)
            cat_links.append(full)
    cat_links = list(dict.fromkeys(cat_links))
    chosen = cat_links[:max_categories]
    all_products = []
    for c in chosen:
        try:
            csoup = get_soup(c)
            product_cards = csoup.select("article, .product-item, .product, .card")
            for card in product_cards:
                title_el = card.select_one(".product-title, h2, h3, .title")
                title = clean_text(title_el.get_text()) if title_el else ""
                link_el  = card.select_one("a[href]")
                link  = urljoin(c, link_el["href"]) if link_el else c
                desc_el  = card.select_one(".desc, .excerpt, p")
                desc  = clean_text(desc_el.get_text()) if desc_el else ""
                if title:
                    all_products.append({"category_url": c, "name": title, "url": link, "description": desc})
        except Exception as e:
            print(f"[warn] product category error {c}: {e}")
        time.sleep(0.5)
    return all_products

def scrape_careers():
    jobs = []
    try:
        soup = get_soup(CAREERS_BASE)
        job_cards = soup.select("article, .job, .career, .opening, .position, .vacancy, .card")
        for card in job_cards:
            title_el = card.select_one("h2, h3, .title")
            title = clean_text(title_el.get_text()) if title_el else ""
            link_el  = card.select_one("a[href]")
            link  = urljoin(CAREERS_BASE, link_el["href"]) if link_el else CAREERS_BASE
            loc_el = card.select_one(".location")
            location = clean_text(loc_el.get_text()) if loc_el else ""
            dept_el = card.select_one(".department, .dept")
            dept     = clean_text(dept_el.get_text()) if dept_el else ""
            sum_el = card.select_one("p, .summary, .desc")
            summary  = clean_text(sum_el.get_text()) if sum_el else ""
            if title:
                jobs.append({"title": title, "url": link, "location": location, "department": dept, "summary": summary})
    except Exception as e:
        print(f"[warn] careers page error: {e}")
    return jobs

def save_json(products, careers, path="kdd_data.json"):
    payload = {"products": products, "careers": careers, "meta": {"source_products": PRODUCTS_BASE, "source_careers": CAREERS_BASE}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(products)} products and {len(careers)} careers to {path}")

if __name__ == "__main__":
    products = scrape_product_categories(max_categories=2)
    careers  = scrape_careers()
    if not products and not careers:
        print("[info] Using fallback sample data.")
        products = [
            {"category_url": PRODUCTS_BASE+"sample-iot/", "name": "IoT Gateway X1", "url": PRODUCTS_BASE+"iot-gateway-x1", "description": "Edge gateway for industrial IoT."},
            {"category_url": PRODUCTS_BASE+"sample-networking/", "name": "Smart Switch S12", "url": PRODUCTS_BASE+"smart-switch-s12", "description": "Managed Layer-2 switch for SMBs."},
        ]
        careers = [
            {"title": "Data Engineer", "url": CAREERS_BASE+"jobs/data-engineer", "location": "Kuwait", "department": "IT", "summary": "Build data pipelines and analytics."},
            {"title": "Sales Executive", "url": CAREERS_BASE+"jobs/sales-executive", "location": "Kuwait", "department": "Sales", "summary": "Develop client relationships and hit targets."},
        ]
    save_json(products, careers, "kdd_data.json")
