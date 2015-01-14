import unittest

from mock import MagicMock

import shuttle.sync


class TestSync(unittest.TestCase):

    def test_sync_requires_content_and_translation(self):
        """Sync requires a content and translation parameter."""

        tx = MagicMock()
        content = MagicMock()

        sync = shuttle.sync.Sync(content, tx)

        self.assertEqual(sync.translation, tx)
        self.assertEqual(sync.content, content)
