from cStringIO import StringIO

import babel.messages.catalog
import babel.messages.pofile
from deskapi.models import DeskApi2
from django.conf import settings
import txlib.api.statistics
import txlib.api.translations
from txlib.http.exceptions import NotFoundError

from transifex import Tx


DEFAULT_VENDOR_LOCALE_MAP = {'en_us': 'en'}

DEFAULT_SOURCE_LANGUAGE = 'en_US'
DEFAULT_I18N_TYPE = 'HTML'


class DeskTxSync(object):

    def __init__(self, tx_project_slug, log, locales=None,
                 vendor_locale_map=None, options=None):

        self.tx_project_slug = tx_project_slug
        self.log = log
        self.enabled_locales = locales
        self.lower_locales = [l.lower() for l in self.enabled_locales]
        self.options = options
        self.vendor_locale_map = vendor_locale_map or DEFAULT_VENDOR_LOCALE_MAP
        self.reverse_locale_map = dict(
            ((v, k) for k, v in self.vendor_locale_map.iteritems())
        )

        self.desk = DeskApi2(
            sitename=settings.DESK_SITENAME,
            auth=(settings.DESK_USER, settings.DESK_PASSWD),
        )

    def _process_locale(self, locale):
        """Return True if this locale should be processed."""

        if locale.lower().startswith('en'):
            return False

        return (locale in self.enabled_locales or

                self.reverse_locale_map.get(locale.lower(), None)
                in self.enabled_locales or

                locale in self.lower_locales or

                self.reverse_locale_map.get(locale.lower(), None)
                in self.lower_locales
        )

    def desk_locale(self, locale):
        """Return the Desk-style locale for locale."""

        locale = locale.lower().replace('-', '_')
        return self.vendor_locale_map.get(locale, locale)

    def push(self):
        """Push data from Desk into Transifex."""

        raise NotImplemented()

    def pull(self):
        """Pull data from Transifex into Desk."""

        raise NotImplemented()


class DeskTopics(DeskTxSync):

    def __init__(self, *args, **kwargs):

        super(DeskTopics, self).__init__(settings.TOPICS_PROJECT_SLUG,
                                         *args, **kwargs)

        self.TOPIC_STRINGS_SLUG = 'desk-topics'

    def push(self):
        """Push topics to Transifex."""

        tx = Tx(self.tx_project_slug)

        # asssemble the template catalog
        template = babel.messages.catalog.Catalog()
        for topic in self.desk.topics():
            if topic.show_in_portal:
                template.add(topic.name)

        # serialize the catalog as a PO file
        template_po = StringIO()
        babel.messages.pofile.write_po(template_po, template)

        # upload/update the catalog resource
        tx.create_or_update_resource(
            self.TOPIC_STRINGS_SLUG,
            DEFAULT_SOURCE_LANGUAGE,
            "Help Center Topics",
            template_po.getvalue(),
            i18n_type='PO',
            project_slug=self.tx_project_slug,
        )

    def pull(self):
        """Pull topics from Transifex."""

        topic_stats = txlib.api.statistics.Statistics.get(
            project_slug=self.tx_project_slug,
            resource_slug=self.TOPIC_STRINGS_SLUG,
        )

        translated = {}

        # for each language
        for locale in self.enabled_locales:

            if not self._process_locale(locale):
                continue

            locale_stats = getattr(topic_stats, locale, None)
            if locale_stats is None:
                self.log.debug('Locale %s not present when pulling topics.' %
                               (locale,))
                continue

            if locale_stats['completed'] == '100%':
                # get the resource from Tx
                translation = txlib.api.translations.Translation.get(
                    project_slug=self.tx_project_slug,
                    slug=self.TOPIC_STRINGS_SLUG,
                    lang=locale,
                )

                translated[locale] = babel.messages.pofile.read_po(
                    StringIO(translation.content.encode('utf-8'))
                )

        # now that we've pulled everything from Tx, upload to Desk
        for topic in self.desk.topics():

            for locale in translated:

                if topic.name in translated[locale]:

                    self.log.debug(
                        'Updating topic (%s) for locale (%s)' %
                        (topic.name, locale),
                    )

                    if locale in topic.translations:
                        topic.translations[locale].update(
                            name=translated[locale][topic.name].string,
                        )
                    else:
                        topic.translations.create(
                            locale=locale,
                            name=translated[locale][topic.name].string,
                        )
                else:

                    self.log.error(
                        'Topic name (%s) does not exist in locale (%s)' %
                        (topic['name'], locale),
                    )


class DeskTutorials(DeskTxSync):

    def __init__(self, *args, **kwargs):

        super(DeskTutorials, self).__init__(settings.TUTORIALS_PROJECT_SLUG,
                                            *args, **kwargs)

    def make_resource_title(self, article):
        """Given a dict of Article information, return the Tx Resource name."""

        return "%(subject)s (%(id)s)" % {
            'subject': article.subject,
            'id': article.api_href.rsplit('/')[1],
        }

    def make_resource_document(self, title, content, tags=[],):
        """Return a single HTML document containing the title and content."""

        assert "<html>" not in content
        assert "<body>" not in content

        return """
        <html>
        <head><title>%(title)s</title></head>
        <body>
        %(content)s
        </body>
        """ % dict(
            title=title,
            content=content,
        )

    def parse_resource_document(self, content):
        """Return a dict with the keys title, content, tags for content."""

        content = content.strip()

        if not content.startswith('<html>'):
            # this is not a full HTML doc, probably content w/o title, tags, etc
            return dict(body=content)

        result = {}
        if '<title>' in content and '</title>' in content:
            result['subject'] = content[content.find('<title>') + 7:content.find('</title>')].strip()
        result['body'] = content[content.find('<body>') + 6:content.find('</body>')].strip()

        return result

    def desk_to_our_locale(self, desk_locale):

        locale = self.reverse_locale_map.get(
            desk_locale, desk_locale,
        )

        pieces = locale.split('_')
        pieces[1:] = [p.upper() for p in pieces[1:]]

        return "_".join(pieces)

    def push(self):
        """Push tutorials to Transifex."""

        tx = Tx(self.tx_project_slug)

        if self.options.resources:
            articles = [
                self.desk.articles().by_id(r.strip())
                for r in self.options.resources.split(',')
            ]
        else:
            articles = self.desk.articles()

        for a in articles:

            self.log.debug(
                'Inspecting Desk resource %s', a.api_href
            )

            for translation in a.translations.items().values():
                our_locale = self.desk_to_our_locale(translation.locale)

                self.log.debug('Checking locale %s', translation.locale)

                if not self._process_locale(translation.locale):
                    self.log.debug('Skipping locale.')
                    continue

                # make sure the project exists in Tx
                tx.get_project(our_locale)

                a_id = a.api_href.rsplit('/', 1)[1]
                if (self.options.force or
                    not tx.resource_exists(a_id, our_locale) or
                    translation.outdated
                ):
                    self.log.info('Resource %(id)s out of date in %(locale)s; updating.' %
                             {'id': a_id,
                              'locale': our_locale,
                              },
                    )

                    tx.create_or_update_resource(
                        a_id,
                        our_locale,
                        self.make_resource_title(a),
                        self.make_resource_document(a.subject, a.body),
                    )

    def is_complete(self, tx, lang, resource_slug):

        statistics = tx.resource_statistics(resource_slug, lang)
        lang_statistics = getattr(statistics, lang, None)

        return lang_statistics and lang_statistics['completed'] == '100%'

    def pull(self):
        "Pull Tutorials from Transifex to Desk."""

        tx = Tx(self.tx_project_slug)

        for lang in self.enabled_locales:

            self.log.debug('Pulling tutorials for %s', lang)

            if not self._process_locale(lang):
                self.log.debug('Skipping locale %s', lang)
                continue

            try:
                resources = tx.list_resources(lang)
            except NotFoundError:
                self.log.error('No project found for locale %s', lang)
                continue

            if self.options.resources:
                pull_resources = [
                    r.strip() for r in self.options.resources.split(',')
                ]

                resources = [
                    r for r in resources
                    if r['slug'] in pull_resources
                ]

            for resource in resources:

                if self.is_complete(tx, lang, resource['slug']):

                    self.log.info('Pulling translation for %s in %s' % (resource['slug'], lang))

                    translation = tx.translation_exists(resource['slug'], lang)

                    desk_translation = self.parse_resource_document(translation.content)

                    desk_article = self.desk.articles().by_id(resource['slug'])
                    desk_translations = desk_article.translations
                    if self.desk_locale(lang) in desk_translations:
                        desk_translations[self.desk_locale(lang)].update(
                            **desk_translation
                        )
                    else:
                        desk_translations.create(
                            locale=self.desk_locale(lang),
                            **desk_translation
                        )
