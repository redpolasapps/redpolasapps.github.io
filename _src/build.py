#!/usr/bin/env python3
"""Builds the static site from the sources in _src/ (GitHub Pages doesn't publish folders starting with "_").

    python3 _src/build.py

Each source page is written once, in both languages: every element with lang="es" or lang="en" belongs to that
language only. The script writes one static page per language (Spanish at the folder, English under en/), so each
URL has a single language for search engines, linked to each other with hreflang. Head texts come from PAGES.

To add an app: put its icon in assets/icons/<slug>.png and add an entry to _src/apps.json. Its card appears on the
home page (both languages), in the structured data and in the sitemap.
"""
import html
import json
import os
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '_src')
SITE = 'https://redpolasapps.fyi'
LANGS = ('es', 'en')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class LangFilter(HTMLParser):
    """Copies the HTML as it is, leaving out every element whose lang is the other language."""

    def __init__(self, keep):
        super().__init__(convert_charrefs=False)
        self.keep, self.out, self.skip = keep, [], 0

    def _lang_of(self, attrs):
        return dict(attrs).get('lang')

    def handle_starttag(self, tag, attrs):
        lang = self._lang_of(attrs)
        if self.skip:
            if tag not in VOID:
                self.skip += 1
            return
        if tag != 'html' and lang in LANGS and lang != self.keep:
            if tag not in VOID:
                self.skip = 1
            return
        text = self.get_starttag_text()
        # the language marker has done its job: drop it (the page's own lang is on <html>)
        if tag != 'html' and lang == self.keep:
            text = text.replace(f' lang="{lang}"', '', 1)
        self.out.append(text)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in VOID:
                self.skip -= 1
            return
        self.out.append(f'</{tag}>')

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)

    def handle_entityref(self, name):
        if not self.skip:
            self.out.append(f'&{name};')

    def handle_charref(self, name):
        if not self.skip:
            self.out.append(f'&#{name};')

    def handle_comment(self, d):
        if not self.skip and not d.strip().startswith('src:'):
            self.out.append(f'<!--{d}-->')

    def handle_decl(self, d):
        self.out.append(f'<!{d}>')


def only(lang, src):
    f = LangFilter(lang)
    f.feed(src)
    f.close()
    out = ''.join(f.out)
    # collapse the blank lines the removed blocks leave behind
    lines = out.split('\n')
    clean = []
    for line in lines:
        if line.strip() == '' and clean and clean[-1].strip() == '':
            continue
        clean.append(line.rstrip())
    return '\n'.join(clean)


def e(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- apps (home page cards + structured data)

def app_cards(apps, lang):
    cards = []
    for a in apps:
        t = a[lang]
        live = bool(a.get('appStoreId')) and a.get('status') == 'live'
        store = f"https://apps.apple.com/{'es' if lang == 'es' else 'us'}/app/id{a['appStoreId']}" if live else None
        badge = (f'<span class="tag tag-new">{"Muy pronto" if lang == "es" else "Coming soon"}</span>' if a.get('status') == 'soon'
                 else '')
        links = []
        if a.get('page'):
            page = a['page'] if lang == 'es' else a['page'].rstrip('/') + '/en/'
            links.append(f'<a class="btn btn-primary" href="{e(page)}">{"Ver la app" if lang == "es" else "See the app"}</a>')
        if store:
            links.append(f'<a class="btn {"btn-ghost" if a.get("page") else "btn-primary"}" href="{e(store)}" rel="noopener">'
                         f'<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M16.37 12.6c-.02-2.3 1.88-3.4 1.96-3.46-1.07-1.56-2.73-1.77-3.32-1.8-1.41-.14-2.76.83-3.48.83-.72 0-1.83-.81-3-.79-1.55.02-2.97.9-3.77 2.28-1.6 2.78-.41 6.9 1.15 9.16.76 1.1 1.67 2.34 2.87 2.3 1.15-.05 1.58-.75 2.97-.75 1.39 0 1.78.75 3 .72 1.24-.02 2.02-1.12 2.78-2.23.87-1.28 1.23-2.52 1.25-2.58-.03-.01-2.39-.92-2.41-3.68zM14.1 5.86c.64-.77 1.07-1.85.95-2.92-.92.04-2.03.61-2.69 1.38-.59.68-1.1 1.77-.96 2.82 1.02.08 2.07-.52 2.7-1.28z"/></svg>'
                         f'App Store</a>')
        links.append(f'<a class="btn btn-link" href="{e(a["privacy"])}">{"Privacidad" if lang == "es" else "Privacy"}</a>')
        cards.append(f'''        <article class="app" id="{e(a['slug'])}">
          <img class="app-icon" src="/assets/icons/{e(a['slug'])}.png" alt="{e(a['name'])}" width="96" height="96" loading="lazy">
          <div class="app-body">
            <div class="app-meta"><span class="tag">{e(t['category'])}</span>{badge}</div>
            <h3>{e(a['name'])}</h3>
            <p>{e(t['pitch'])}</p>
            <div class="app-actions">
              {(chr(10) + '              ').join(links)}
            </div>
          </div>
        </article>''')
    return '\n'.join(cards)


def apps_jsonld(apps, lang):
    items = []
    for i, a in enumerate(apps, 1):
        t = a[lang]
        app = {
            '@type': 'VideoGame' if a.get('game') else 'MobileApplication',
            'name': a['name'],
            'operatingSystem': 'iOS',
            'applicationCategory': 'GameApplication' if a.get('game') else a.get('schemaCategory', 'UtilitiesApplication'),
            'description': t['pitch'],
            'image': f"{SITE}/assets/icons/{a['slug']}.png",
            'author': {'@type': 'Person', 'name': 'Víctor M. García Ortega'},
        }
        if a.get('game'):
            app['gamePlatform'] = 'iOS'
        if a.get('status') == 'live' and a.get('appStoreId'):
            app['url'] = f"https://apps.apple.com/app/id{a['appStoreId']}"
            app['offers'] = {'@type': 'Offer', 'price': '0', 'priceCurrency': 'EUR'}
        elif a.get('page'):
            app['url'] = SITE + a['page']
        items.append({'@type': 'ListItem', 'position': i, 'item': app})
    return items


# ---------------------------------------------------------------- pages

def head_block(meta, lang, path_es, path_en):
    url = SITE + (path_es if lang == 'es' else path_en)
    alt = 'en' if lang == 'es' else 'es'
    m = meta[lang]
    tags = [
        f'<title>{e(m["title"])}</title>',
        f'<meta name="description" content="{e(m["description"])}">',
        f'<link rel="canonical" href="{url}">',
        f'<link rel="alternate" hreflang="es" href="{SITE + path_es}">',
        f'<link rel="alternate" hreflang="en" href="{SITE + path_en}">',
        f'<link rel="alternate" hreflang="x-default" href="{SITE + path_en}">',
        f'<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="Redpolas Apps">',
        f'<meta property="og:title" content="{e(m["title"])}">',
        f'<meta property="og:description" content="{e(m["description"])}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{SITE + meta["image"]}">',
        f'<meta property="og:image:width" content="1200">',
        f'<meta property="og:image:height" content="630">',
        f'<meta property="og:locale" content="{"es_ES" if lang == "es" else "en_US"}">',
        f'<meta property="og:locale:alternate" content="{"en_US" if lang == "es" else "es_ES"}">',
        f'<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(m["title"])}">',
        f'<meta name="twitter:description" content="{e(m["description"])}">',
        f'<meta name="twitter:image" content="{SITE + meta["image"]}">',
    ]
    return '\n'.join(tags)


def build_page(src_name, path_es, path_en, meta, extra):
    src = open(os.path.join(SRC, src_name), encoding='utf-8').read()
    for lang in LANGS:
        page = only(lang, src)
        page = page.replace('<html lang="es" class="es">', f'<html lang="{lang}" class="{lang}">')
        page = page.replace('<!--HEAD-->', head_block(meta, lang, path_es, path_en))
        page = page.replace('{{ALT_LANG_URL}}', path_en if lang == 'es' else path_es)
        page = page.replace('{{HOME}}', '/' if lang == 'es' else '/en/')
        for key, fn in extra.items():
            page = page.replace('{{' + key + '}}', fn(lang))
        page = page.lstrip()
        out_path = os.path.join(ROOT, (path_es if lang == 'es' else path_en).lstrip('/'), 'index.html')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, 'w', encoding='utf-8').write(page)
        print('escrito', os.path.relpath(out_path, ROOT))


def main():
    apps = json.load(open(os.path.join(SRC, 'apps.json'), encoding='utf-8'))
    live_count = sum(1 for a in apps if a.get('status') == 'live')

    # home
    home_meta = {
        'image': '/assets/og-home.jpg',
        'es': {'title': 'Redpolas Apps · Apps y juegos para iPhone y iPad',
               'description': 'Estudio independiente de apps y juegos para iPhone y iPad: The Line Tycoon, Cozy Plants, DogWeight y EyeColor. Soporte, contacto y políticas de privacidad.'},
        'en': {'title': 'Redpolas Apps · Apps and games for iPhone and iPad',
               'description': 'Independent studio making apps and games for iPhone and iPad: The Line Tycoon, Cozy Plants, DogWeight and EyeColor. Support, contact and privacy policies.'},
    }

    def home_ld(lang):
        data = [{
            '@context': 'https://schema.org', '@type': 'Organization', 'name': 'Redpolas Apps', 'url': SITE + '/',
            'logo': SITE + '/assets/logo.png', 'email': 'redpolasapps@gmail.com',
            'founder': {'@type': 'Person', 'name': 'Víctor M. García Ortega'},
        }, {
            '@context': 'https://schema.org', '@type': 'ItemList',
            'name': 'Apps de Redpolas Apps' if lang == 'es' else 'Redpolas Apps apps',
            'itemListElement': apps_jsonld(apps, lang),
        }]
        return '\n'.join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in data)

    build_page('home.html', '/', '/en/', home_meta, {
        'APP_CARDS': lambda lang: app_cards(apps, lang),
        'JSONLD': home_ld,
        'APP_COUNT': lambda lang: str(len(apps)),
        'PRIVACY_LINKS': lambda lang: '\n'.join(
            f'            <li><a href="{e(a["privacy"])}">{e(a["name"])}<span>→</span></a></li>' for a in apps),
        'LIVE_COUNT': lambda lang: str(live_count),
    })

    # The Line Tycoon
    lt = next(a for a in apps if a['slug'] == 'linetycoon')
    lt_meta = {
        'image': '/LineTycoon/img/og.jpg',
        'es': {'title': 'The Line Tycoon: juego de parque de atracciones y colas para iPhone y iPad',
               'description': 'Dibuja colas, cruza puentes y vagonetas y sube a toda la multitud a la montaña rusa. 7 atracciones, 21 estrellas y 30 visitantes secretos. Gratis, sin internet, para iPhone y iPad.'},
        'en': {'title': 'The Line Tycoon: theme park queue game for iPhone and iPad',
               'description': 'Draw the line, cross it with bridges and mine carts and get the whole crowd onto the roller coaster. 7 rides, 21 stars, 30 secret guests. Free, plays offline, for iPhone and iPad.'},
    }

    def lt_ld(lang):
        m = lt_meta[lang]
        data = {
            '@context': 'https://schema.org', '@type': 'VideoGame',
            'name': 'The Line Tycoon', 'alternateName': 'The Line Tycoon: Theme Park',
            'description': m['description'], 'url': SITE + ('/LineTycoon/' if lang == 'es' else '/LineTycoon/en/'),
            'image': SITE + '/LineTycoon/img/og.jpg',
            'screenshot': [f'{SITE}/LineTycoon/img/shot-{lang}-{i}.jpg' for i in range(1, 6)],
            'gamePlatform': ['iPhone', 'iPad'], 'operatingSystem': 'iOS 17.0 or later',
            'applicationCategory': 'GameApplication', 'genre': ['Simulation', 'Strategy', 'Casual'],
            'inLanguage': ['es', 'en', 'fr', 'de', 'pt'],
            'author': {'@type': 'Person', 'name': 'Víctor M. García Ortega'},
            'publisher': {'@type': 'Organization', 'name': 'Redpolas Apps', 'url': SITE + '/'},
            'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'EUR'},
        }
        if lt.get('status') == 'live':
            data['installUrl'] = f"https://apps.apple.com/app/id{lt['appStoreId']}"
        return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'

    build_page('linetycoon.html', '/LineTycoon/', '/LineTycoon/en/', lt_meta, {'JSONLD': lt_ld})

    # sitemap + robots
    pages = [('/', '/en/'), ('/LineTycoon/', '/LineTycoon/en/')]
    urls = []
    for es, en in pages:
        for loc in (es, en):
            urls.append(f'''  <url>
    <loc>{SITE + loc}</loc>
    <xhtml:link rel="alternate" hreflang="es" href="{SITE + es}"/>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE + en}"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE + en}"/>
  </url>''')
    for a in apps:
        urls.append(f'  <url>\n    <loc>{SITE + a["privacy"]}</loc>\n  </url>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + '\n'.join(urls) + '\n</urlset>\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write(
        f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    print('escrito sitemap.xml y robots.txt')


if __name__ == '__main__':
    main()
