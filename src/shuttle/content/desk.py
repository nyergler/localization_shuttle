class DeskContent(object):

    LOCALE_MAP = {'en_us': 'en'}
    REVERSE_LOCALE_MAP = dict(
        ((v, k) for k, v in LOCALE_MAP.iteritems())
    )

    def __init__(self, deskapi):
        self.desk = deskapi

    def content_locale(self, trans_locale):

        trans_locale = trans_locale.lower().replace('-', '_')
        return self.LOCALE_MAP.get(trans_locale, trans_locale)

    def translation_locale(self, content_locale):

        locale = self.REVERSE_LOCALE_MAP.get(
            content_locale, content_locale,
        )

        pieces = locale.split('_')
        pieces[1:] = [p.upper() for p in pieces[1:]]

        return "_".join(pieces)

    def topics(self):
        """Return an iterator over content topics."""

        return self.desk.topics()

    def topic_translatable(self, topic):
        """Return True if the given topic is translatable.

        ``topic`` will be an object from the iterator returned by
        ``topics``.

        """

        return topic.show_in_portal

    def topic_string(self, topic):
        """Return the string to use as the translation source."""

        return topic.name

    def update_topic_translation(self, topic, locale, translation):
        """Update a locale's translation for topic."""

        if locale in topic.translations:
            topic.translations[locale].update(
                name=translation,
            )
        else:
            topic.translations.create(
                locale=locale,
                name=translation,
            )
