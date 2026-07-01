import unittest

from drop_compliance_tool.workflow import build_drop_url, hash_email, normalize_hash, resolve_status


class WorkflowTests(unittest.TestCase):
    def test_hash_email_is_stable(self):
        self.assertEqual(hash_email('user@example.com'), hash_email('USER@example.com'))

    def test_resolve_status_prefers_deleted(self):
        self.assertEqual(resolve_status(True, False), 'deleted')

    def test_resolve_status_prefers_opted_out(self):
        self.assertEqual(resolve_status(False, True), 'opted_out')

    def test_resolve_status_defaults_to_not_found(self):
        self.assertEqual(resolve_status(False, False), 'not_found')

    def test_build_drop_url_uses_configured_path(self):
        self.assertEqual(
            build_drop_url('https://example.com', '/download/data'),
            'https://example.com/download/data',
        )

    def test_normalize_hash_supports_base64_unhex(self):
        self.assertEqual(
            normalize_hash('68656c6c6f', mode='base64-unhex'),
            'aGVsbG8=',
        )


if __name__ == '__main__':
    unittest.main()
