import unittest

import mock

from shuttle.content import desk


class DeskAdapterTests(unittest.TestCase):

    def test_content_locale(self):
        """Test locale mapping for translation -> content."""

        content = desk.DeskContent()

        # en-US, en_US map to en
        self.assertEqual(content.content_locale('en-US'), 'en')
        self.assertEqual(content.content_locale('en_US'), 'en')

        # others are unmapped
        self.assertEqual(content.content_locale('fr'), 'fr')

    def test_translation_locale(self):
        """Test locale mapping for content -> translation."""

        content = desk.DeskContent()

        # en-US, en_US map to en
        self.assertEqual(content.translation_locale('en'), 'en_US')

        # others are unmapped
        self.assertEqual(content.translation_locale('fr'), 'fr')

    def test_list_topics(self):

        pass

    def test_list_articles(self):

        pass

    def test_list_articles_by_id(self):

        pass

    def test_get_translations(self):

        pass
