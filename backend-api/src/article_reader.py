"""Bounded extraction of the requested publisher's own article body.

Search-provider snippets are discovery hints only. Never join text across URLs.
"""
from __future__ import annotations

from html.parser import HTMLParser
from html import escape
import re
import json
import time
from urllib import error, request
from urllib.parse import urlparse, urljoin

try:
    from .provider_http import NoRedirect, safe_link, article_url_without_tracking
except ImportError:
    from provider_http import NoRedirect, safe_link, article_url_without_tracking


def _clean_article_body(body: str) -> str:
    """Remove page interaction prompts accidentally included in article prose."""
    cleaned = []
    for paragraph in body.split("\n"):
        paragraph = paragraph.strip()
        if re.fullmatch(
            r"Already have Rappler\+\?\s*Sign in to listen to groundbreaking journalism\.?",
            paragraph, flags=re.I,
        ):
            continue
        paragraph = re.sub(
            r"^\s*(?:This is AI-generated\.\s*)?Read the article for full context\.\s*Report any errors\s*\.\s*",
            "", paragraph, flags=re.I,
        ).strip()
        if paragraph:
            cleaned.append(paragraph)
    return "\n".join(cleaned)


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.hidden = 0
        self.title_parts = []
        self.paragraphs = []
        self.current = []
        self.article_count = 0
        self.primary_article = None

    def handle_starttag(self, tag, attrs):
        # HTML void elements never push an open ancestor. Otherwise an <img>
        # or <br> makes later </p> and </article> close the wrong elements.
        if tag in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            if tag == "br" and self.current:
                self.current.append(" ")
            return
        attributes = dict(attrs)
        chrome_markers = " ".join(str(attributes.get(key, "")) for key in ("class", "id", "role", "aria-label"))
        is_hidden = (tag in {"script", "style", "nav", "footer", "aside", "form"}
                     or attributes.get("aria-hidden") == "true"
                     or "display:none" in str(attributes.get("style", "")).replace(" ", "").lower()
                     or bool(re.search(r"(?:^|[\s_-])(?:related|recommendations?|advert(?:isement)?|sidebar|promo|newsletter|most-read|trending|comments?|share|social)(?:$|[\s_-])", chrome_markers, re.I)))
        if tag == "article":
            self.article_count += 1
        article_id = self.article_count if tag == "article" else self._current_article()
        self.stack.append((tag, is_hidden, article_id))
        if is_hidden:
            self.hidden += 1
        if tag in {"p", "figcaption"}:
            self.current = []

    def handle_endtag(self, tag):
        if tag in {"p", "figcaption"} and self.current:
            paragraph = " ".join(" ".join(self.current).split())
            if len(paragraph) >= 35:
                self.paragraphs.append(paragraph)
            self.current = []
        # Close the matching ancestor, including any unclosed descendants.
        # An unrelated/unmatched end tag must not pop the current article.
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if index is not None:
            del self.stack[index:]
            self.hidden = sum(hidden for _, hidden, _ in self.stack)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.hidden or not data.strip():
            return
        tags = {tag for tag, _, _ in self.stack}
        article_id = self._current_article()
        if "h1" in tags and "main" in tags and article_id and (self.primary_article is None or self.primary_article == article_id):
            self.primary_article = article_id
            self.title_parts.append(data)
        if tags & {"p", "figcaption"} and self.primary_article is not None and article_id == self.primary_article:
            self.current.append(data)

    def _current_article(self):
        return next((article_id for tag, _, article_id in reversed(self.stack) if tag == "article"), None)


class CustomsLayoutParser(HTMLParser):
    """Read the BOC's UIkit article layout, which has no main/article tags.

    Require the displayed heading to match the document title, then capture
    only its following text-large panel. Never use all paragraphs on the page.
    """

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.document_title = []
        self.heading_parts = []
        self.heading = ""
        self.panel = []
        self.panel_depth = None
        self.finished = False

    def handle_starttag(self, tag, attrs):
        classes = set(dict(attrs).get("class", "").split())
        if tag == "h3":
            self.heading_parts = []
        if (tag == "div" and {"uk-panel", "uk-text-large"} <= classes
                and self.heading and self.panel_depth is None and not self.finished):
            self.panel_depth = len(self.stack)
        if self.panel_depth is not None:
            self.panel.append(self.get_starttag_text())
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_data(self, data):
        if "title" in self.stack:
            self.document_title.append(data)
        if "h3" in self.stack:
            self.heading_parts.append(data)
        if self.panel_depth is not None:
            self.panel.append(escape(data))

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i] == tag), None)
        if self.panel_depth is not None:
            self.panel.append(f"</{tag}>")
            if index is not None and index <= self.panel_depth:
                self.panel_depth = None
                self.finished = True
        if tag == "h3" and not self.finished:
            heading = " ".join(" ".join(self.heading_parts).split())
            title = " ".join(" ".join(self.document_title).split())
            if heading and (title == heading or any(title.startswith(heading + separator) for separator in (" – ", " - ", " — "))):
                self.heading = heading
        if index is not None:
            del self.stack[index:]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def article(self):
        if not self.heading or not self.finished:
            return None
        parser = ArticleParser()
        parser.feed("<main><article><h1>" + escape(self.heading) + "</h1>" + "".join(self.panel) + "</article></main>")
        return parser


class PublisherLayoutParser(HTMLParser):
    """Bounded layouts observed on WHO, CDC and Philstar article pages."""

    BODY_CLASSES = {'who.int': 'sf-detail-body-wrapper', 'cdc.gov': 'cdc-dfe-body__center',
                    'philstar.com': 'article__writeup'}
    VOID = CustomsLayoutParser.VOID

    def __init__(self, host):
        super().__init__()
        self.body_class = self.BODY_CLASSES.get(host.removeprefix('www.'))
        self.stack = []
        self.depth = None
        self.body = []
        self.body_count = 0
        self.headings = []
        self.heading = []
        self.title = []
        self.og_title = ''

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'meta' and values.get('property') == 'og:title':
            self.og_title = values.get('content', '')
        if tag == 'h1':
            self.heading = []
        matches = self.body_class and self.body_class in values.get('class', '').split()
        if matches:
            self.body_count += 1
            if self.body_count == 1:
                self.depth = len(self.stack)
        elif self.depth is not None:
            self.body.append(self.get_starttag_text())
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_data(self, data):
        if 'title' in self.stack:
            self.title.append(data)
        if 'h1' in self.stack:
            self.heading.append(data)
        if self.depth is not None:
            self.body.append(escape(data))

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i] == tag), None)
        if self.depth is not None:
            if index is not None and index <= self.depth:
                self.depth = None
            else:
                self.body.append(f'</{tag}>')
        if tag == 'h1' and self.heading:
            self.headings.append(' '.join(' '.join(self.heading).split()))
            self.heading = []
        if index is not None:
            del self.stack[index:]

    def article(self):
        headings = set(self.headings)
        if self.body_count != 1 or self.depth is not None or len(headings) != 1:
            return None
        heading = headings.pop()
        normalize = lambda text: ' '.join(re.findall(r'[^\W_]+', text.casefold()))
        title = normalize(self.og_title or ' '.join(self.title))
        if not title or not heading or not (title == normalize(heading) or title.startswith(normalize(heading) + ' ')):
            return None
        parser = ArticleParser()
        parser.feed('<main><article><h1>' + escape(heading) + '</h1>' + ''.join(self.body) + '</article></main>')
        return parser if parser.paragraphs else None


class StructuredArticleBodyParser(HTMLParser):
    """Extract prose paragraphs from publisher-provided articleBody HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self.current = None
        self.hidden = 0

    def handle_starttag(self, tag, _attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag == "p" and self.current is None and not self.hidden:
            self.current = []

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif tag == "p" and self.current is not None:
            paragraph = " ".join(" ".join(self.current).split())
            if len(paragraph) >= 35:
                self.paragraphs.append(paragraph)
            self.current = None

    def handle_data(self, data):
        if self.current is not None and not self.hidden:
            self.current.append(data)


class ManilaTimesPhotoParser(HTMLParser):
    """Read only the publisher's displayed photo story, not related galleries."""
    def __init__(self):
        super().__init__()
        self.stack=[];self.titles=[];self.og_title='';self.body_count=0
        self.parts=[];self.current=None
    def handle_starttag(self,tag,attrs):
        values=dict(attrs);classes=set(values.get('class','').split())
        if tag=='meta' and values.get('property')=='og:title':
            self.og_title=values.get('content','')
        if tag in CustomsLayoutParser.VOID:return
        title='article-title' in classes
        body='article_body' in classes
        hidden=(tag in {'script','style','aside','nav','footer'} or
                bool(re.search(r'(?:^|[ _-])(?:related|advertisement|social|share)(?:$|[ _-])',values.get('class',''),re.I)))
        if body:self.body_count+=1
        self.stack.append((tag,title,body,hidden))
        if tag=='figcaption' and any(row[2] for row in self.stack):self.current=[]
    def handle_data(self,data):
        if any(row[3] for row in self.stack):return
        if any(row[1] for row in self.stack):self.titles.append(data)
        if self.current is not None and any(row[0]=='figcaption' for row in self.stack):self.current.append(data)
    def handle_endtag(self,tag):
        if tag=='figcaption' and self.current is not None:
            text=' '.join(' '.join(self.current).split())
            if len(text)>=35:self.parts.append(text)
            self.current=None
        index=next((i for i in range(len(self.stack)-1,-1,-1) if self.stack[i][0]==tag),None)
        if index is not None:del self.stack[index:]
    def article(self):
        title=' '.join(' '.join(self.titles).split())
        normal=lambda s:' '.join(re.findall(r'[^\W_]+',s.casefold()))
        if self.body_count!=1 or not title or normal(title)!=normal(self.og_title) or not self.parts:return None
        return {'content_status':'readable','title':title,'article_text':'\n'.join(dict.fromkeys(self.parts))}


class StructuredArticleParser(HTMLParser):
    """Read explicit same-page articleBody metadata, never search descriptions."""

    def __init__(self):
        super().__init__()
        self.blocks = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type', '').lower().strip() == 'application/ld+json':
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.blocks.append(''.join(self.current))
            self.current = None

    def article(self, requested_url):
        def identity(value):
            if not isinstance(value, str):
                return None
            parsed = urlparse(article_url_without_tracking(value))
            if parsed.scheme != 'https' or not parsed.hostname:
                return None
            host = parsed.hostname.casefold().removeprefix('www.')
            if host.endswith('.cnn.com'):
                host = 'cnn.com'
            return (host, parsed.path.rstrip('/'), parsed.query)

        def objects(value, depth=0):
            if depth > 8:
                return
            if isinstance(value, list):
                for item in value:
                    yield from objects(item, depth + 1)
            elif isinstance(value, dict):
                yield value
                # Only traverse the document graph, not recommendations or
                # nested items which can represent different articles.
                yield from objects(value.get('@graph', []), depth + 1)

        candidates = set()
        target = identity(requested_url)
        if target is None:
            return None
        for block in self.blocks[:20]:
            try:
                document = json.loads(block)
            except (ValueError, RecursionError):
                continue
            for item in objects(document):
                kinds = item.get('@type', [])
                kinds = kinds if isinstance(kinds, list) else [kinds]
                if not any(kind in {'Article', 'NewsArticle', 'ReportageNewsArticle', 'LiveBlogPosting'} for kind in kinds if isinstance(kind, str)):
                    continue
                page = item.get('mainEntityOfPage')
                page = page.get('@id') or page.get('url') if isinstance(page, dict) else page
                if target not in {identity(item.get('url')), identity(page), identity(item.get('@id'))}:
                    continue
                headline, body = item.get('headline'), item.get('articleBody')
                if not isinstance(headline, str) or not headline.strip() or len(headline) > 1000:
                    continue
                if '<' in headline or '>' in headline:
                    continue
                if 'LiveBlogPosting' in kinds:
                    updates = item.get('liveBlogUpdate')
                    if not isinstance(updates, list) or not (1 <= len(updates) <= 200):
                        continue
                    update_bodies = []
                    for update in updates:
                        if not isinstance(update, dict):
                            continue
                        update_types = update.get('@type', [])
                        update_types = update_types if isinstance(update_types, list) else [update_types]
                        update_body = update.get('articleBody')
                        if (not any(kind in {'BlogPosting', 'LiveBlogPosting'} for kind in update_types if isinstance(kind, str))
                                or not isinstance(update_body, str) or not (35 <= len(update_body) <= 20_000)):
                            continue
                        if '<' in update_body or '>' in update_body:
                            body_parser = StructuredArticleBodyParser()
                            body_parser.feed(update_body)
                            update_body = "\n".join(body_parser.paragraphs)
                            if not update_body:
                                continue
                        update_bodies.append(update_body.strip())
                    if not update_bodies:
                        continue
                    description = item.get('description')
                    if (isinstance(description, str) and 80 <= len(description) <= 1000
                            and '<' not in description and '>' not in description):
                        update_bodies.insert(0, description.strip())
                    combined_body = "\n".join(dict.fromkeys(update_bodies))
                    if len(combined_body) > 200_000:
                        continue
                    candidates.add((' '.join(headline.split()), combined_body))
                    continue
                if not isinstance(body, str) or not (80 <= len(body) <= 200_000):
                    continue
                if '<' in body or '>' in body:
                    body_parser = StructuredArticleBodyParser()
                    body_parser.feed(body)
                    body = "\n".join(body_parser.paragraphs)
                    if not body:
                        continue
                candidates.add((' '.join(headline.split()), body.strip()))
        if len(candidates) != 1:
            return None
        title, body = candidates.pop()
        return {'content_status': 'readable', 'title': title, 'article_text': body}


def _photo_report_provenance(html, url, article):
    """Require same-page publisher metadata plus a visible named photo credit.

    Publication metadata establishes provenance, not the date of the event.
    Claim/event dates still have to match the literal supporting caption.
    """
    body=article.get('article_text','')
    credit=re.search(r'\bPHOTOS?\s+BY\s+([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){1,4})\s*$',body)
    if not credit:return {}
    parser=StructuredArticleParser();parser.feed(html)
    def identity(value):
        if not isinstance(value,str):return None
        part=urlparse(value)
        return (part.scheme,(part.hostname or '').lower().removeprefix('www.'),part.path.rstrip('/'))
    target=identity(url)
    normal=lambda s:' '.join(re.findall(r'[^\W_]+',s.casefold()))
    for block in parser.blocks[:20]:
        try:item=json.loads(block)
        except ValueError:continue
        if not isinstance(item,dict) or item.get('@type')!='NewsArticle' or str(item.get('articleSection','')).casefold()!='photos':continue
        if identity(item.get('url'))!=target or normal(str(item.get('headline','')))!=normal(article['title']):continue
        published=item.get('datePublished','')
        if not isinstance(published,str) or not re.match(r'^20\d{2}-\d{2}-\d{2}T',published):continue
        return {'content_kind':'publisher_photo_report','photo_credit':credit.group(1),
                'date_published':published,'provenance_verified':True}
    return {}


def read_article(url: str, *, allowed_host) -> dict:
    """Read one bounded HTTPS article, allowing only same-publisher redirects."""
    url = article_url_without_tracking(url)
    parsed = urlparse(url)
    if not safe_link(url) or parsed.scheme != "https" or not allowed_host(parsed.hostname or ""):
        return {"content_status": "inaccessible"}
    try:
        opener = request.build_opener(NoRedirect)
        current = url
        visited = set()
        deadline = time.monotonic() + 8
        response = None
        for _hop in range(3):
            candidate = urlparse(current)
            if (current in visited or candidate.scheme != 'https' or not safe_link(current)
                    or (candidate.hostname or '').casefold().removeprefix('www.') != (parsed.hostname or '').casefold().removeprefix('www.')
                    or not allowed_host(candidate.hostname or '') or time.monotonic() >= deadline):
                return {"content_status": "inaccessible"}
            visited.add(current)
            req = request.Request(current, headers={"User-Agent": "SuriPH-Research/1.0", "Accept": "text/html"})
            try:
                response = opener.open(req, timeout=max(.1, deadline - time.monotonic()))
                break
            except error.HTTPError as exc:
                location = exc.headers.get('Location') if exc.headers else None
                if exc.code not in {301, 302, 303, 307, 308} or not location:
                    raise
                current = urljoin(current, location)
                exc.close()
        if response is None:
            return {"content_status": "inaccessible"}
        with response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                return {"content_status": "inaccessible"}
            body = response.read(1_000_001)
            truncated = len(body) > 1_000_000
            html = body.decode("utf-8", errors="replace")
            parser = ArticleParser()
            if not truncated:
                parser.feed(html)
                if (not parser.title_parts or not parser.paragraphs) and (parsed.hostname or "").lower() in {"customs.gov.ph", "www.customs.gov.ph"}:
                    fallback = CustomsLayoutParser()
                    fallback.feed(html)
                    parser = fallback.article() or parser
                if not parser.title_parts or not parser.paragraphs:
                    fallback = PublisherLayoutParser((urlparse(current).hostname or '').lower())
                    if fallback.body_class:
                        fallback.feed(html)
                        parser = fallback.article() or parser
    except (error.HTTPError, error.URLError, TimeoutError, ValueError, OSError):
        return {"content_status": "inaccessible"}
    title = " ".join(" ".join(parser.title_parts).split())
    paragraphs = parser.paragraphs[:80]
    if not title or not paragraphs:
        if (parsed.hostname or '').lower().removeprefix('www.') == 'manilatimes.net' and '/photos/' in parsed.path:
            photos = ManilaTimesPhotoParser()
            photos.feed(html)
            photo_article = photos.article()
            if photo_article:
                photo_article.update(_photo_report_provenance(html, current, photo_article))
                return photo_article
        structured = StructuredArticleParser()
        structured.feed(html)
        result = structured.article(current) or {"content_status": "inaccessible"}
        if result["content_status"] == "readable":
            result["article_text"] = _clean_article_body(result["article_text"])
        return result
    return {"content_status": "readable", "title": title, "article_text": _clean_article_body("\n".join(paragraphs))}
