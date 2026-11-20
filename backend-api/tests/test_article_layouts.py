"""Shared layout contracts use synthetic articles; live pages stay local-only."""
import sys,json,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
import article_reader
from article_layouts import SamePageArticleParser,ScopedBodyText
from test_article_reader import FakeResponse

URL='https://news.example/report'
TITLE='City opens a community library'
BODY='The city opened a new community library on Monday, providing free access to books and reading rooms.'

def meta(url=URL,title=TITLE,kind='article'):
 return f'<link rel="canonical" href="{url}"><meta property="og:url" content="{url}"><meta property="og:title" content="{title}"><meta property="og:type" content="{kind}">'

def parse(html,url=URL):
 p=SamePageArticleParser();p.feed(html);return p.article(url)

def hydrated(bodies=None,schema_url=None):
 schema={'@type':'NewsArticle','headline':TITLE,'datePublished':'2026-11-20T10:00:00+08:00'}
 if schema_url:schema['url']=schema_url
 articles=bodies or [{'headline':TITLE,'body_html':'<div>'+BODY+'</div>','type':'text','pubstatus':'usable'}]
 return meta(kind='Website')+'<h1>'+TITLE+'</h1><h1>Newsletter</h1><script type="application/ld+json">'+json.dumps(schema)+'</script><script type="application/json" id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'articles':articles}}})+'</script>'

class SharedLayoutTests(unittest.TestCase):
 def test_article_without_main_is_readable_and_stays_scoped(self):
  result=parse(meta()+'<p>Unrelated navigation paragraph outside the report should never enter the prose.</p><article><h1>'+TITLE+'</h1><p>'+BODY+'</p></article>')
  self.assertEqual(result['article_text'],BODY)
 def test_explicit_body_without_article_or_main_is_readable(self):
  result=parse(meta()+'<h1>'+TITLE+'</h1><div class="entry-content"><div>'+BODY+'</div></div><aside><p>Different story outside this article must never be read as proof.</p></aside>')
  self.assertEqual(result['article_text'],BODY)
 def test_nested_wordpress_body_excludes_wrapper_and_related_promotions(self):
  html=meta()+'<article><h1>'+TITLE+'</h1><p>Photo caption outside the primary prose must remain separate from this selected article body.</p><div class="td-post-content"><p>'+BODY+'</p><div class="related"><p>Another mayor closed a market, which is an entirely different event.</p></div></div></article>'
  self.assertEqual(parse(html)['article_text'],BODY)
 def test_sibling_title_and_prose_scopes_ignore_heading_only_container(self):
  html=meta()+'<main><div class="article-content-protected"><h1>'+TITLE+'</h1></div><div class="article-content-protected"><p>'+BODY+'</p></div></main>'
  self.assertEqual(parse(html)['article_text'],BODY)
 def test_hydration_can_read_same_page_newsml_body_not_rendered_as_paragraphs(self):
  self.assertEqual(parse(hydrated())['article_text'],BODY)
 def test_identical_hydration_copies_are_deduplicated(self):
  row={'headline':TITLE,'body_html':'<p>'+BODY+'</p>','type':'text','pubstatus':'usable'}
  self.assertEqual(parse(hydrated([row,row]))['article_text'],BODY)
 def test_changed_hydration_bodies_are_ambiguous(self):
  rows=[{'headline':TITLE,'body_html':'<p>'+body+'</p>'} for body in [BODY,'The city rejected a proposal to open a community library and explained its decision at a public meeting.']]
  self.assertIsNone(parse(hydrated(rows)))
 def test_other_story_state_cannot_supply_the_primary_article_body(self):
  self.assertIsNone(parse(hydrated([{'headline':'An unrelated story','body_html':'<p>'+BODY+'</p>'}])))
 def test_description_is_never_substituted_for_body(self):
  self.assertIsNone(parse(hydrated([{'headline':TITLE,'description_html':'<p>'+BODY+'</p>'}])))
 def test_wrong_schema_url_is_not_ignored_even_with_matching_headline(self):
  self.assertIsNone(parse(hydrated(schema_url='https://news.example/different-story')))
 def test_wrong_canonical_or_query_id_is_rejected(self):
  html=meta()+'<h1>'+TITLE+'</h1><div itemprop="articleBody"><p>'+BODY+'</p></div>'
  for target in ['https://other.example/report',URL+'?id=two']:
   self.assertIsNone(parse(html,target))
 def test_wrong_headline_and_ambiguous_explicit_bodies_are_rejected(self):
  self.assertIsNone(parse(meta()+'<h1>Other story</h1><div class="article-body"><p>'+BODY+'</p></div>'))
  self.assertIsNone(parse(meta()+'<h1>'+TITLE+'</h1><div class="article-body"><p>'+BODY+'</p></div><div class="article-body"><p>A second different article appeared in the same response and cannot be merged with the original.</p></div>'))
 def test_script_and_hidden_content_cannot_be_article_prose(self):
  html=meta()+'<h1>'+TITLE+'</h1><div class="story-content"><p>'+BODY+'</p><script>throw new Error("execute me");</script><div hidden><p>A hidden story about a different mayor must not be included in the article prose.</p></div></div>'
  self.assertEqual(parse(html)['article_text'],BODY)
 def test_article_lead_in_div_and_nested_inline_markup_are_preserved(self):
  p=ScopedBodyText();p.feed('<div>MANILA — The city opened a <strong>community library</strong> on Monday, officials confirmed.</div><p>'+BODY+'</p>')
  self.assertIn('MANILA — The city opened a community library',p.text())
 def test_real_http_block_is_distinct_from_layout_extraction_failure(self):
  with patch.object(article_reader.request,'build_opener') as p:
   p.return_value.open.side_effect=HTTPError(URL,403,'Forbidden',{},None)
   value=article_reader.read_article(URL,allowed_host=lambda _:True)
  self.assertEqual(value['content_reason'],'http_403')
  with patch.object(article_reader.request,'build_opener') as p:
   p.return_value.open.return_value=FakeResponse(b'<html><title>Generic site</title><p>Navigation only</p></html>')
   value=article_reader.read_article(URL,allowed_host=lambda _:True)
  self.assertEqual(value['content_reason'],'body_not_extracted')
 def test_reader_uses_new_fallback_without_expanding_network_permissions(self):
  html=(meta()+'<h1>'+TITLE+'</h1><div class="story-body"><p>'+BODY+'</p></div>').encode()
  with patch.object(article_reader.request,'build_opener') as p:
   p.return_value.open.return_value=FakeResponse(html)
   value=article_reader.read_article(URL,allowed_host=lambda _:True)
  self.assertEqual(value['content_status'],'readable');self.assertEqual(value['article_text'],BODY)

if __name__=='__main__':unittest.main()
