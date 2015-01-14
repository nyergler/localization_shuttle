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
