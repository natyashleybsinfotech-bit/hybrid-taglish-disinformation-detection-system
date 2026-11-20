import io
import json
import os
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import article_reader
import retrieval


class FakeResponse(io.BytesIO):
    headers = {"Content-Type": "text/html; charset=utf-8"}


class ArticleReaderTests(unittest.TestCase):
    def test_manila_times_photo_caption_is_read_from_own_body(self):
        text='MMDA personnel stationed beside orange barriers along Roxas Boulevard on November 14, 2026.'
        html=('<meta property="og:title" content="EXPRESS LANES">'
              '<div class="article-title">EXPRESS LANES</div>'
              '<aside><figcaption>Unrelated recommendation should not be read.</figcaption></aside>'
              '<div class="article_body"><figure><amp-img src="photo.jpg"></amp-img>'
              '<figcaption>'+text+'</figcaption></figure><figure><figcaption>'+text+'</figcaption></figure></div>'
              '<figure><figcaption>Outside article must not be read.</figcaption></figure>').encode()
        with patch.object(article_reader.request,'build_opener') as opener:
            opener.return_value.open.return_value=FakeResponse(html)
            result=article_reader.read_article('https://www.manilatimes.net/2026/11/14/photos/example/123/amp',allowed_host=lambda host:host.endswith('manilatimes.net'))
        self.assertEqual(result['content_status'],'readable')
        self.assertEqual(result['article_text'],text)

    def test_photo_parser_rejects_wrong_title_duplicate_body_and_missing_caption(self):
        for html in [
            '<meta property="og:title" content="Different story"><div class="article-title">EXPRESS LANES</div><div class="article_body"><figcaption>Personnel stationed beside barriers on the boulevard.</figcaption></div>',
            '<meta property="og:title" content="EXPRESS LANES"><div class="article-title">EXPRESS LANES</div><div class="article_body"><figcaption>Personnel stationed beside barriers on the boulevard.</figcaption></div><div class="article_body">Another story</div>',
            '<meta property="og:title" content="EXPRESS LANES"><div class="article-title">EXPRESS LANES</div><div class="article_body"></div><figcaption>Caption outside the article must never be accepted.</figcaption>']:
            parser=article_reader.ManilaTimesPhotoParser();parser.feed(html)
            self.assertIsNone(parser.article())

    def test_photo_provenance_requires_same_page_metadata_and_visible_credit(self):
        url='https://www.manilatimes.net/2026/11/14/photos/example/123/amp'
        article={'title':'Express lanes','article_text':'Personnel monitored the designated express lanes. PHOTOS BY RENE H. DILAN'}
        metadata={'@type':'NewsArticle','articleSection':'Photos','url':url,
                  'headline':'Express lanes','datePublished':'2026-11-14T20:00:00+08:00'}
        def html(value):return '<script type="application/ld+json">'+json.dumps(value)+'</script>'
        result=article_reader._photo_report_provenance(html(metadata),url,article)
        self.assertTrue(result['provenance_verified'])
        for field,value in [('url','https://www.manilatimes.net/other'),('headline','Other story'),('articleSection','News'),('datePublished','')]:
            self.assertEqual(article_reader._photo_report_provenance(html({**metadata,field:value}),url,article),{})
        self.assertEqual(article_reader._photo_report_provenance(html(metadata),url,{**article,'article_text':'No named photo credit.'}),{})

    def test_generic_photo_caption_stays_inside_primary_article(self):
        caption='MMDA personnel stationed beside orange barriers along Roxas Boulevard on November 14, 2026.'
        html=('<main><article><h1>Original photo report</h1><figure><img src="photo.jpg">'
              '<figcaption>'+caption+'</figcaption></figure>'
              '<aside><figcaption>Unrelated recommendation must never be extracted.</figcaption></aside>'
              '</article><article><h1>Another story</h1><figcaption>Caption from another article must not be used.</figcaption></article></main>').encode()
        with patch.object(article_reader.request,'build_opener') as opener:
            opener.return_value.open.return_value=FakeResponse(html)
            result=article_reader.read_article('https://www.philstar.com/example',allowed_host=lambda host:True)
        self.assertEqual(result['article_text'],caption)

    def test_tracking_url_matches_same_page_structured_article(self):
        clean='https://www.gmanetwork.com/news/topstories/metro/123/report/story/'
        body='Rice sales in Metro Manila are suspended on November 16 to 18 during the summit.'
        document={'@type':'NewsArticle','url':clean,'headline':'Rice sales temporarily suspended','articleBody':body}
        html=('<script type="application/ld+json">'+json.dumps(document)+'</script>').encode()
        for query in ['?fbclid=facebook-tracking','?utm_source=facebook&fbclid=tracked','?%66bclid=encoded#comments']:
            with patch.object(article_reader.request,'build_opener') as opener:
                opener.return_value.open.return_value=FakeResponse(html)
                result=article_reader.read_article(clean+query,allowed_host=lambda host:host.endswith('gmanetwork.com'))
                sent=opener.return_value.open.call_args.args[0]
                self.assertEqual(sent.full_url,clean)
            self.assertEqual(result['content_status'],'readable')
            self.assertEqual(result['article_text'],body)

    def test_meaningful_query_still_identifies_a_different_article(self):
        clean='https://www.gmanetwork.com/report'
        document={'@type':'NewsArticle','url':clean+'?id=one','headline':'First report',
                  'articleBody':'A complete first report with sufficient length to serve as article body evidence for this test.'}
        parser=article_reader.StructuredArticleParser()
        parser.feed('<script type="application/ld+json">'+json.dumps(document)+'</script>')
        self.assertIsNotNone(parser.article(clean+'?id=one&fbclid=tracked'))
        self.assertIsNone(parser.article(clean+'?id=two&fbclid=tracked'))
        self.assertEqual(article_reader.article_url_without_tracking(clean+'?id=a%2Fb&token=keep%2Bthis&utm_medium=social'),clean+'?id=a%2Fb&token=keep%2Bthis')

    def test_page_prompt_is_not_part_of_matching_article_prose(self):
        url = 'https://www.rappler.com/technology/example-story/'
        report = 'MANILA, Philippines - President Marcos signed an order creating the National AI Council.'
        html = ('<main><article><h1>National AI Council created</h1><p>'
                'Read the article for full context. Report any errors . ' + report +
                '</p></article></main>').encode()
        with patch.object(article_reader.request, 'build_opener') as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article(url, allowed_host=lambda host: host.endswith('rappler.com'))
        self.assertEqual(result['content_status'], 'readable')
        self.assertEqual(result['article_text'], report)

    def test_rappler_separate_page_prompts_are_not_article_prose(self):
        url = 'https://www.rappler.com/technology/example-story/'
        report = 'MANILA, Philippines - President Marcos signed an order creating the National AI Council.'
        html = ('<main><article><h1>National AI Council created</h1>'
                '<p>Already have Rappler+? Sign in to listen to groundbreaking journalism.</p>'
                '<p>This is AI-generated. Read the article for full context. Report any errors .</p>'
                '<p>' + report + '</p></article></main>').encode()
        with patch.object(article_reader.request, 'build_opener') as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article(url, allowed_host=lambda host: host.endswith('rappler.com'))
        self.assertEqual(result['article_text'], report)

    def test_known_publisher_body_layouts_keep_only_the_article(self):
        for host, body_class in article_reader.PublisherLayoutParser.BODY_CLASSES.items():
            with self.subTest(host=host):
                html = f'<title>Water and health - Publisher</title><h1>Water and health</h1><p>An unrelated paragraph outside the article must not enter the body.</p><div class="{body_class}"><p>Drinking enough water helps prevent dehydration and supports normal body functions.</p><div class="related"><p>This separate news story must not enter the article body.</p></div></div><footer><p>Other unrelated information appears in the footer here.</p></footer>'
                parser = article_reader.PublisherLayoutParser(host)
                parser.feed(html)
                parsed = parser.article()
                self.assertIsNotNone(parsed)
                self.assertEqual(len(parsed.paragraphs), 1)
                self.assertNotIn('unrelated', ' '.join(parsed.paragraphs))
                self.assertNotIn('separate', ' '.join(parsed.paragraphs))

    def test_publisher_layout_rejects_different_heading_and_ambiguous_bodies(self):
        for html in (
            '<title>Different story</title><h1>Water and health</h1><div class="sf-detail-body-wrapper"><p>Drinking water helps prevent dehydration and supports normal body functions.</p></div>',
            '<title>Water and health</title><h1>Water and health</h1>' + '<div class="sf-detail-body-wrapper"><p>Drinking water helps prevent dehydration and supports normal body functions.</p></div>' * 2,
        ):
            parser = article_reader.PublisherLayoutParser('who.int')
            parser.feed(html)
            self.assertIsNone(parser.article())

    def test_same_publisher_https_redirect_can_reach_readable_article(self):
        html = b'<main><article><h1>Three schools open in Manila</h1><p>The city opened three public schools in Manila on Monday.</p></article></main>'
        redirect = HTTPError('https://www.gmanetwork.com/news/old', 301, 'Moved', {'Location': 'https://gmanetwork.com/news/story'}, None)
        with patch.object(article_reader.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = [redirect, FakeResponse(html)]
            result = article_reader.read_article('https://www.gmanetwork.com/news/old', allowed_host=lambda host: host.endswith('gmanetwork.com'))
        self.assertEqual(result['content_status'], 'readable')

    def test_redirect_cannot_escape_publisher_or_downgrade_https(self):
        for destination in ('https://unrelated.example/report', 'http://gmanetwork.com/news/story', 'https://127.0.0.1/private'):
            with self.subTest(destination=destination), patch.object(article_reader.request, 'build_opener') as opener:
                opener.return_value.open.side_effect = HTTPError('https://gmanetwork.com/news/old', 302, 'Moved', {'Location': destination}, None)
                result = article_reader.read_article('https://gmanetwork.com/news/old', allowed_host=lambda _host: True)
                self.assertEqual(result['content_status'], 'inaccessible')
                self.assertEqual(opener.return_value.open.call_count, 1)

    def test_redirect_loop_stops_without_reading_other_content(self):
        url = 'https://gmanetwork.com/news/story'
        with patch.object(article_reader.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError(url, 301, 'Moved', {'Location': url}, None)
            result = article_reader.read_article(url, allowed_host=lambda _host: True)
        self.assertEqual(result['content_status'], 'inaccessible')
        self.assertEqual(opener.return_value.open.call_count, 1)

    def test_structured_body_must_identify_the_requested_article(self):
        url = 'https://www.gmanetwork.com/news/story'
        body = 'The city opened three public schools in Manila on Monday. Officials attended the opening ceremony.'
        original = {'@type': 'NewsArticle', 'url': url, 'headline': 'Three public schools open in Manila', 'articleBody': body}
        other = dict(original, url='https://www.gmanetwork.com/news/other', headline='Unrelated story', articleBody='Unrelated. ' * 20)
        html = ('<script type="application/ld+json">' + json.dumps({'@graph': [other, original]}) + '</script>').encode()
        with patch.object(article_reader.request, 'build_opener') as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article(url, allowed_host=lambda _host: True)
        self.assertEqual(result['article_text'], body)
        self.assertNotIn('Unrelated', str(result))

    def test_structured_article_body_html_is_reduced_to_readable_prose(self):
        url = 'https://www.gmanetwork.com/news/story'
        title = "Scarlet Witch is returning in 'Avengers: Doomsday'"
        body = (
            "<p>Elizabeth Olsen's <strong>Scarlet Witch</strong> is making a comeback in the Marvel Cinematic Universe.</p>"
            "<p>The Wakandans, led by Shuri, are also joining Avengers: Doomsday.</p>"
        )
        article = {
            '@type': 'NewsArticle',
            'mainEntityOfPage': {'@id': url},
            'headline': title,
            'articleBody': body,
        }
        html = ('<script type="application/ld+json">' + json.dumps(article) + '</script>').encode()
        with patch.object(article_reader.request, 'build_opener') as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article(url, allowed_host=lambda host: host.endswith('gmanetwork.com'))
        self.assertEqual(result['content_status'], 'readable')
        self.assertEqual(result['title'], title)
        self.assertIn('Scarlet Witch is making a comeback', result['article_text'])
        self.assertNotIn('<p>', result['article_text'])

    def test_structured_description_or_other_page_is_not_article_body(self):
        original = {'@type': 'NewsArticle', 'url': 'https://gmanetwork.com/news/other', 'headline': 'Other article',
                    'articleBody': 'An unrelated article should never become evidence for this requested post. ' * 3}
        parser = article_reader.StructuredArticleParser()
        parser.feed('<script type="application/ld+json">' + json.dumps(original) + '</script>')
        self.assertIsNone(parser.article('https://gmanetwork.com/news/story'))
        original.update(url='https://gmanetwork.com/news/story', description=original.pop('articleBody'))
        parser = article_reader.StructuredArticleParser()
        parser.feed('<script type="application/ld+json">' + json.dumps(original) + '</script>')
        self.assertIsNone(parser.article(original['url']))

    def test_conflicting_same_page_bodies_are_not_merged(self):
        url = 'https://gmanetwork.com/news/story'
        original = {'@type': 'NewsArticle', 'mainEntityOfPage': {'@id': url}, 'headline': 'Original report', 'articleBody': 'Original article body. ' * 8}
        other = dict(original, articleBody='A conflicting article body. ' * 8)
        parser = article_reader.StructuredArticleParser()
        parser.feed('<script type="application/ld+json">' + json.dumps([original, other]) + '</script>')
        self.assertIsNone(parser.article(url))

    def test_customs_layout_requires_matching_title_and_bounded_panel(self):
        html = b"<html><head><title>Customs opens public office - Bureau of Customs</title></head><body><h3>Customs opens public office</h3><div class='uk-panel uk-text-large'><p>The Bureau of Customs opened its public office in Manila on Monday.</p><div class='related'><p>An unrelated story must never appear in the article.</p></div></div><footer><p>Another unrelated story is displayed in the footer here.</p></footer></body></html>"
        with patch.object(article_reader.request, "build_opener") as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article("https://customs.gov.ph/story", allowed_host=lambda host: host == "customs.gov.ph")
        self.assertEqual(result["content_status"], "readable")
        self.assertEqual(result["title"], "Customs opens public office")
        self.assertNotIn("unrelated", result["article_text"])

    def test_customs_layout_does_not_read_page_without_matching_heading(self):
        parser = article_reader.CustomsLayoutParser()
        parser.feed("<title>A different story - Bureau of Customs</title><h3>Customs opens public office</h3><div class='uk-panel uk-text-large'><p>The Bureau of Customs opened its public office in Manila on Monday.</p></div>")
        self.assertIsNone(parser.article())

    def test_paragraphs_outside_an_article_are_not_article_content(self):
        parser = article_reader.ArticleParser()
        parser.feed("<p>A complete but unrelated paragraph outside any article container.</p>")
        self.assertEqual(parser.paragraphs, [])

    def test_void_elements_do_not_leak_neighboring_article(self):
        parser = article_reader.ArticleParser()
        parser.feed("<main><article><h1>Original report</h1><p>The city opened three public schools in Manila on Monday.<img src='photo.jpg'><br>Officials attended.</p></article><article><p>This unrelated incident must not enter the first article body.</p></article></main>")
        self.assertEqual(len(parser.paragraphs), 1)
        self.assertNotIn("unrelated", parser.paragraphs[0])

    def test_hidden_void_elements_do_not_hide_remaining_article(self):
        parser = article_reader.ArticleParser()
        parser.feed("<main><article><h1>Original report</h1><div class='advertisement'><img src='ad.jpg'></div><p>The city opened three public schools in Manila on Monday.</p></article></main>")
        self.assertEqual(len(parser.paragraphs), 1)
        self.assertEqual(parser.hidden, 0)

    def test_excerpt_and_title_come_from_same_article_not_search_snippet(self):
        html = b"<html><nav>Other shocking story</nav><main><article><h1>Customs destroys vape products</h1><p>The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Navotas.</p><aside>Other incident in Cebu</aside><div class='related-story'><p>A separate raid in Cebu involved a different shipment of illicit goods.</p></div></article><article><h2>Related story</h2><p>A separate raid in Cebu involved a different shipment of illicit goods.</p></article></main></html>"
        with patch.object(article_reader.request, "build_opener") as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            rows = retrieval.inspect_related_sources([{"url": "https://customs.gov.ph/story", "title": "Wrong title", "snippet": "Unrelated incident in Cebu"}], "Customs destroyed vape products in Navotas")
        self.assertEqual(rows[0]["title"], "Customs destroys vape products")
        self.assertNotIn("Cebu", rows[0]["snippet"])
        self.assertNotIn("Wrong title", str(rows[0]))
        self.assertNotIn("separate raid", rows[0]["article_text"])

    def test_search_match_does_not_keep_an_unrelated_fetched_article(self):
        article = {"content_status": "readable", "title": "Local hospital opens new clinic",
                   "article_text": "A hospital opened a clinic to serve residents in Quezon City."}
        search = {"url": "https://gmanetwork.com/news/report", "title": "Customs destroys vape products",
                  "snippet": "Customs destroyed 3174 boxes of illicit vape products in Navotas."}
        with patch.object(retrieval, "read_article", return_value=article):
            rows = retrieval.inspect_related_sources([search], "Customs destroyed vape products in Navotas")
        self.assertEqual(rows, [])

    def test_unrelated_liveblog_topic_does_not_hide_relevant_fetched_article(self):
        claim = (
            "Nvidia CEO Jensen Huang has called it quits after revelations about two "
            "extramarital affairs, including one with an alleged Chinese spy."
        )
        article = {
            "content_status": "readable",
            "title": "Jensen Huang summoned after resigning as Nvidia CEO",
            "article_text": claim + "\nSeparately, our TV character season recap covers another story.",
        }
        search = {
            "url": "https://edition.cnn.com/2026/11/11/business/live-news/nvidia-jensen-huang",
            "title": "Jensen Huang resigns as Nvidia CEO amid affairs",
            "snippet": claim,
        }

        with patch.object(retrieval, "read_article", return_value=article):
            rows = retrieval.inspect_related_sources([search], claim)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content_status"], "readable")

    def test_trusted_post_link_is_read_even_when_search_terms_do_not_match(self):
        article = {
            "content_status": "readable",
            "title": "Scarlet Witch returns",
            "article_text": "Elizabeth Olsen's Scarlet Witch is making a comeback.",
        }
        post_link = {
            "url": "https://gmanetwork.com/news/story",
            "origin": "post_link",
        }
        with patch.object(retrieval, "read_article", return_value=article):
            rows = retrieval.inspect_related_sources([post_link], "A different claim")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["origin"], "post_link")
        self.assertEqual(rows[0]["content_status"], "readable")

    def test_inaccessible_article_preserves_search_preview_as_unverified_metadata(self):
        with patch.object(retrieval, "read_article", return_value={"content_status": "inaccessible"}):
            rows = retrieval.inspect_related_sources([{"url": "https://customs.gov.ph/story", "title": "Search title", "snippet": "Search snippet"}], "claim")
        self.assertNotIn("title", rows[0])
        self.assertNotIn("snippet", rows[0])
        self.assertEqual(rows[0]["search_title"], "Search title")
        self.assertEqual(rows[0]["search_snippet"], "Search snippet")
        self.assertEqual(rows[0]["relationship"], "unverified")

    def test_closed_liveblog_heading_and_video_title_are_not_readable_article_body(self):
        html = (
            b"<html><main><div class='container__inner'>"
            b"<h1>Updates: Jensen Huang resigns as Nvidia CEO amid affairs, security concerns</h1>"
            b"<p>These were the updates from November 12, 2026.</p>"
            b"<p>Nvidia CEO Jensen Huang steps down, more affair details revealed</p>"
            b"<p>This live page has now been closed.</p>"
            b"</div></main></html>"
        )
        url = (
            "https://www.aljazeera.com/news/liveblog/2026/11/12/"
            "live-jensen-huang-resigns-as-nvidia-ceo-as-affairs-raise-security-concerns"
        )
        with patch.object(article_reader.request, "build_opener") as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article(
                url, allowed_host=lambda host: host.endswith("aljazeera.com")
            )

        self.assertEqual(result["content_status"], "inaccessible")
        self.assertNotIn("article_text", result)

    def test_same_page_liveblog_structured_updates_are_read_as_article_content(self):
        url = (
            "https://edition.cnn.com/2026/11/11/business/live-news/"
            "nvidia-jensen-huang-investigation-fallout"
        )
        description = (
            "Jensen Huang resigned as Nvidia CEO after reports of relationships with "
            "two women, one allegedly a Chinese spy."
        )
        update = (
            "Series of scandals: The decision followed reports that Huang had a "
            "relationship with an Nvidia executive. He was already under scrutiny "
            "after reports of an affair with another woman who was allegedly working "
            "as a spy for China."
        )
        document = {
            "@type": "LiveBlogPosting",
            "mainEntityOfPage": {"url": url},
            "headline": "Jensen Huang summoned to testify before Congress after resigning as Nvidia CEO",
            "description": description,
            "liveBlogUpdate": [{"@type": "BlogPosting", "articleBody": update}],
        }
        html = (
            "<html><head><title>CNN live blog</title></head><body>"
            + "<!--" + ("page chrome " * 50_000) + "-->"
            + '<script type="application/ld+json">'
            + json.dumps(document)
            + "</script></body></html>"
        ).encode()
        with patch.object(article_reader.request, "build_opener") as opener:
            opener.return_value.open.return_value = FakeResponse(html)
            result = article_reader.read_article(
                url, allowed_host=lambda host: host.endswith("cnn.com")
            )

        self.assertEqual(result["content_status"], "readable")
        self.assertIn(description, result["article_text"])
        self.assertIn(update, result["article_text"])

    def test_liveblog_structured_updates_must_match_the_requested_page(self):
        requested = "https://edition.cnn.com/story/requested"
        other = "https://edition.cnn.com/story/other"
        document = {
            "@type": "LiveBlogPosting",
            "mainEntityOfPage": {"url": other},
            "headline": "Other live blog",
            "liveBlogUpdate": [{"@type": "BlogPosting", "articleBody": "A sufficiently long update body that belongs only to another story."}],
        }
        parser = article_reader.StructuredArticleParser()
        parser.feed(
            '<script type="application/ld+json">'
            + json.dumps(document)
            + "</script>"
        )
        self.assertIsNone(parser.article(requested))


if __name__ == "__main__":
    unittest.main()
