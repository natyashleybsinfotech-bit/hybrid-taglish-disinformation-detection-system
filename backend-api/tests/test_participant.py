import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'src')]
from fastapi.testclient import TestClient
import app as application
import database
import retrieval
from feature_display import describe
from provider_http import NoRedirect, read_json
from model_runtime import Prediction

class ParticipantTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.patches = [patch.object(database.config, 'DATABASE_URL', ''), patch.object(database.config, 'DB_PATH', Path(self.directory.name)/'test.db')]
        for item in self.patches: item.start()
        self.assertEqual(database.migrate()['status'], 'available')
        self.client = TestClient(application.app)
        self.prediction = Prediction('Non-Misleading', 'Prediction: Non-Misleading', .6, 'ready', 'test', 'test', model_score=.4,
                                    linguistic_indicators=[{'name': 'capitalization_ratio', 'value': .125}])
        self.patches.append(patch.object(application, 'classify', return_value=self.prediction)); self.patches[-1].start()
    def tearDown(self):
        database._get_engine().dispose()
        for item in reversed(self.patches): item.stop()
        self.directory.cleanup()
    def test_default_does_not_send_query_or_expose_research_fields(self):
        with patch.object(application, 'retrieve_related_sources') as provider:
            body = self.client.post('/analyze', json={'text': 'Private example text'}).json()
        provider.assert_not_called()
        self.assertNotIn('storage_status', body)
        self.assertNotIn('research_receipt', body)
        self.assertEqual(database.list_candidates(), [])
    def test_retired_research_inputs_cannot_store_or_return_receipts(self):
        response = self.client.post('/analyze', json={
            'text':'Legacy client input', 'research_consent':True, 'retain_text':True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('research_receipt', response.json())
    def test_research_product_routes_are_removed(self):
        payload = {'record_id':'a'*32, 'withdrawal_token':'x'*20, 'usefulness':5}
        self.assertEqual(self.client.get('/privacy').status_code, 404)
        self.assertEqual(self.client.post('/research/feedback', json=payload).status_code, 404)
        self.assertEqual(self.client.post('/research/withdraw', json=payload).status_code, 404)
        self.assertEqual(self.client.get('/admin-api/research-export').status_code, 404)
    def test_feature_display_preserves_unscaled_value(self):
        body=self.client.post('/analyze',json={'text':'specific input'}).json()
        self.assertEqual(body['linguistic_indicators'][0]['value'], .125)
        self.assertEqual(body['linguistic_indicators'][0]['unit'],'ratio')
        self.assertIn('Uppercase',body['linguistic_indicators'][0]['definition'])
    def test_cookie_origin_is_checked(self):
        self.assertEqual(self.client.post('/admin-api/login',headers={'Origin':'https://evil.invalid'},json={'username':'x','password':'y'}).status_code,403)
    def test_removed_agreement_and_candidate_capture_routes(self):
        self.assertEqual(self.client.get('/admin-api/annotation-agreement').status_code,404)
        self.assertEqual(self.client.post('/candidates',json={'text':'x'}).status_code,410)

class ProviderTests(unittest.TestCase):
    def test_success_empty_error_timeout_unsafe_link_and_dates(self):
        cases=[({'organic':[{'title':'Advisory','link':'https://who.int/advisory','date':'2026-01-01'}]},'available'), ({'organic':[]},'no_results'), ({'organic':[{'title':'Unsafe','link':'javascript://who.int/x'}]},'no_results')]
        with patch.object(retrieval.config,'SERPER_ENABLED',True),patch.object(retrieval.config,'SERPER_API_KEY','fixture-not-live'):
            for payload,status in cases:
                with patch.object(retrieval,'open_provider',return_value=io.BytesIO(json.dumps(payload).encode())):
                    result=retrieval.retrieve_related_sources('sample')
                    self.assertEqual(result['retrieval_status'],status)
                    if status=='available': self.assertEqual(result['related_sources'][0]['date'],'2026-01-01')
            with patch.object(retrieval,'open_provider',side_effect=TimeoutError):
                self.assertEqual(retrieval.retrieve_related_sources('sample')['retrieval_status'],'unavailable')
    def test_bounded_response_and_redirect_rejection(self):
        with self.assertRaises(ValueError): read_json(io.BytesIO(b'x'*2_000_001))
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'http://127.0.0.1'))
