import sys, unittest, logging
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src')]
import provider_transport as transport

class TransportTests(unittest.TestCase):
    def run_request(self, opener, reserve=None, timeout=10):
        return transport.request_json(object(), opener=opener, reader=lambda r:{'ok':True},
            reserve=reserve or Mock(return_value=True), timeout=timeout, task='transcription')
    def response(self):
        result=Mock();result.__enter__=Mock(return_value=object());result.__exit__=Mock(return_value=False)
        return result
    def test_temporary_http_failure_recovers_once_and_counts_both_attempts(self):
        opener=Mock(side_effect=[HTTPError('secret-url',503,'secret',{},None),self.response()])
        reserve=Mock(return_value=True)
        self.assertEqual(self.run_request(opener,reserve),{'ok':True})
        self.assertEqual(opener.call_count,2);self.assertEqual(reserve.call_count,2)
    def test_repeated_temporary_failure_stops_after_two_attempts(self):
        opener=Mock(side_effect=HTTPError('secret-url',503,'secret',{},None))
        with self.assertRaises(HTTPError):self.run_request(opener)
        self.assertEqual(opener.call_count,2)
    def test_auth_quota_bad_request_and_missing_model_are_not_retried(self):
        for code in (400,401,403,404,429):
            with self.subTest(code=code):
                opener=Mock(side_effect=HTTPError('secret-url',code,'secret',{},None))
                with self.assertRaises(HTTPError):self.run_request(opener)
                opener.assert_called_once()
    def test_connection_failure_can_recover_without_logging_sensitive_exception(self):
        opener=Mock(side_effect=[URLError('credential-secret-in-raw-error'),self.response()])
        with self.assertLogs(transport.__name__,level=logging.WARNING) as records:
            self.run_request(opener)
        self.assertNotIn('credential-secret',str(records.output))
        self.assertNotIn('secret-url',str(records.output))
    def test_retry_cannot_bypass_request_budget(self):
        reserve=Mock(side_effect=[True,False]);opener=Mock(side_effect=URLError('offline'))
        with self.assertRaises(transport.ProviderBudgetExceeded):self.run_request(opener,reserve)
        opener.assert_called_once();self.assertEqual(reserve.call_count,2)
    def test_expired_total_deadline_does_not_start_a_second_attempt(self):
        opener=Mock(side_effect=TimeoutError())
        with patch.object(transport.time,'monotonic',side_effect=[0,0,10]):
            with self.assertRaises(TimeoutError):self.run_request(opener)
        opener.assert_called_once()
    def test_second_attempt_receives_only_the_remaining_timeout(self):
        opener=Mock(side_effect=[URLError('offline'),self.response()])
        with patch.object(transport.time,'monotonic',side_effect=[0,0,2,4]):self.run_request(opener)
        self.assertEqual(opener.call_args_list[0].kwargs['timeout'],10)
        self.assertEqual(opener.call_args_list[1].kwargs['timeout'],6)
    def test_invalid_response_is_not_retried_or_replaced(self):
        opener=Mock(return_value=self.response())
        with self.assertRaises(ValueError):
            transport.request_json(object(),opener=opener,reader=Mock(side_effect=ValueError('invalid-json')),
                reserve=Mock(return_value=True),timeout=10,task='classification')
        opener.assert_called_once()
