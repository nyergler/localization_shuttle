import unittest

import mock

from shuttle.content import desk


class DeskAdapterTests(unittest.TestCase):

    def test_desk_takes_api_wrapper(self):

        api = mock.MagicMock()
        content = desk.DeskContent(api)

        self.assertEqual(content.desk, api)

    def test_content_locale(self):
        """Test locale mapping for translation -> content."""

        content = desk.DeskContent(mock.MagicMock())

        # en-US, en_US map to en
        self.assertEqual(content.content_locale('en-US'), 'en')
        self.assertEqual(content.content_locale('en_US'), 'en')

        # others are unmapped
        self.assertEqual(content.content_locale('fr'), 'fr')

    def test_translation_locale(self):
        """Test locale mapping for content -> translation."""

        content = desk.DeskContent(mock.MagicMock())

        # en-US, en_US map to en
        self.assertEqual(content.translation_locale('en'), 'en_US')

        # others are unmapped
        self.assertEqual(content.translation_locale('fr'), 'fr')

    def test_topics_delegates_to_deskapi(self):
        api = mock.MagicMock()
        api.topics.return_value = [1, 2, 3]

        content = desk.DeskContent(api)

        self.assertEqual(content.topics(), [1, 2, 3])

    def test_topic_translatable_if_shown_in_portal(self):

        content = desk.DeskContent(mock.Mock())

        self.assertTrue(
            content.topic_translatable(mock.Mock(show_in_portal=True))
        )

        self.assertFalse(
            content.topic_translatable(mock.Mock(show_in_portal=False))
        )

    def test_topic_string_returns_name(self):
        content = desk.DeskContent(mock.Mock())

        topic = mock.Mock()
        topic.name = 'blarf'

        self.assertEqual(
            content.topic_string(topic),
            'blarf',
        )

    def test_update_translation_calls_desk_update(self):

        content = desk.DeskContent(mock.Mock())

        topic = mock.Mock(translations={'fr': mock.MagicMock()})

        content.update_topic_translation(
            topic,
            'fr',
            'Bonjour!',
        )

        topic.translations['fr'].update.assertCalledOnceWith(
            name='Bonjour!',
        )

    def test_update_translation_creates_for_new_locale(self):

        content = desk.DeskContent(mock.Mock())
        topic = mock.MagicMock()

        content.update_topic_translation(
            topic,
            'es',
            'Hola!',
        )

        topic.translations.create.assert_called_once_with(
            locale='es',
            name='Hola!',
        )
