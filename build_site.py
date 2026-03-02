#!/usr/bin/env python3
"""
Zeekr Manual Static Site Generator
Converts zeekr_manual.json into a static HTML site ready for Pagefind.

Usage:
  python build_site.py
  python build_site.py --input my_manual.json --output my_site/

After running:
  npx pagefind --site site/
  npx serve site/   (then open http://localhost:3000)
"""

import json
import re
import shutil
import argparse
from pathlib import Path
from html import escape

parser = argparse.ArgumentParser()
parser.add_argument('--input', default='zeekr_manual.json')
parser.add_argument('--output', default='site')
args = parser.parse_args()

INPUT_FILE = args.input
OUTPUT_DIR = Path(args.output)
SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / 'templates'

with open(TEMPLATES_DIR / 'page.html', encoding='utf-8') as f:
    PAGE_TEMPLATE = f.read()
with open(TEMPLATES_DIR / 'search.html', encoding='utf-8') as f:
    SEARCH_TEMPLATE = f.read()
with open(TEMPLATES_DIR / 'style.css', encoding='utf-8') as f:
    STYLE_CSS = f.read()


def slugify(text):
    text = text.lower()
    text = re.sub(r'[\s,/]+', '-', text)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    return re.sub(r'-+', '-', text).strip('-')


def page_url(page):
    """Return the URL path for a given page dict."""
    section_slug = slugify(page['section'])
    page_slug = page['id'].replace('.html', '')
    return f"/sections/{section_slug}/{page_slug}/"


def build_sidebar(pages, current_page_id):
    """
    Build the full sidebar HTML: all sections expanded, with each page as a
    direct link. The current page and its section are highlighted.
    """
    # Group pages by section, preserving order
    sections = {}
    for p in pages:
        sections.setdefault(p['section'], []).append(p)

    html = []
    for section_name, section_pages in sections.items():
        section_slug = slugify(section_name)
        is_active_section = current_page_id is not None and any(p['id'] == current_page_id for p in section_pages)

        html.append(f'''
    <div class="sb-section{'  sb-section--active' if is_active_section else ''}">
      <button class="sb-section-name" aria-expanded="{'true' if is_active_section else 'false'}">{escape(section_name)}</button>
      <ul class="sb-pages">''')

        for p in section_pages:
            is_active = p['id'] == current_page_id
            url = page_url(p)
            html.append(f'''
        <li><a href="{url}"{'  class="sb-page--active" aria-current="page"' if is_active else ''}>{escape(p['title'])}</a></li>''')

        html.append('      </ul>\n    </div>')

    return '\n'.join(html)


def render_page(page, all_pages):
    # Use the preserved HTML field; fall back to text if old-format JSON
    if 'html' in page and page['html']:
        content = page['html']
    else:
        lines = page.get('text', '').split('\n')
        parts = [f'<p>{escape(l.strip())}</p>' for l in lines if l.strip()]
        content = '\n'.join(parts)

    sidebar_html = build_sidebar(all_pages, page['id'])

    return (PAGE_TEMPLATE
        .replace('{{TITLE}}', escape(page['title']))
        .replace('{{SECTION}}', escape(page['section']))
        .replace('{{SIDEBAR}}', sidebar_html)
        .replace('{{CONTENT}}', content))


def build():
    with open(INPUT_FILE, encoding='utf-8') as f:
        pages = json.load(f)

    print(f"Loaded {len(pages)} pages from {INPUT_FILE}")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    with open(TEMPLATES_DIR / 'style.css', encoding='utf-8') as f:
        (OUTPUT_DIR / 'style.css').write_text(f.read(), encoding='utf-8')
    fonts_src = SCRIPT_DIR / 'fonts'
    if fonts_src.is_dir():
        shutil.copytree(fonts_src, OUTPUT_DIR / 'fonts')
        print(f"Copied fonts to {OUTPUT_DIR / 'fonts'}/")

    search_sidebar = build_sidebar(pages, current_page_id=None)
    search_html = SEARCH_TEMPLATE.replace('{{SIDEBAR}}', search_sidebar)
    (OUTPUT_DIR / 'search.html').write_text(search_html, encoding='utf-8')
    (OUTPUT_DIR / 'index.html').write_text(search_html, encoding='utf-8')

    # Copy cached images into site
    image_cache = SCRIPT_DIR / 'image_cache'
    image_dest = OUTPUT_DIR / 'images'
    if image_cache.is_dir():
        if image_dest.exists():
            shutil.rmtree(image_dest)
        shutil.copytree(image_cache, image_dest)
        print(f"Copied {len(list(image_dest.iterdir()))} images to {image_dest}/")

    section_counts = {}
    for page in pages:
        section_slug = slugify(page['section'])
        page_slug = page['id'].replace('.html', '')
        page_dir = OUTPUT_DIR / 'sections' / section_slug / page_slug
        page_dir.mkdir(parents=True, exist_ok=True)

        html = render_page(page, pages)
        (page_dir / 'index.html').write_text(html, encoding='utf-8')
        section_counts[page['section']] = section_counts.get(page['section'], 0) + 1

    print(f"\n{'─' * 50}")
    print(f"✓ Built {len(pages)} pages into {OUTPUT_DIR}/")
    print(f"\nPages by section:")
    for section, count in section_counts.items():
        print(f"  {count:3d}  {section}")

    print(f"\n{'─' * 50}")
    print("Next steps:\n")
    print(f"  npx pagefind --site {OUTPUT_DIR}/")
    print(f"  npx serve {OUTPUT_DIR}/")
    print( "  open http://localhost:3000\n")

if __name__ == '__main__':
    build()
