from cStringIO import StringIO
import logging

import babel.messages.catalog
import babel.messages.pofile
import txlib.api.statistics
import txlib.api.translations
from txlib.http.exceptions import NotFoundError

from shuttle.translators.transifex import Tx


DEFAULT_SOURCE_LANGUAGE = 'en_US'
DEFAULT_I18N_TYPE = 'HTML'


class Sync(object):

    def __init__(self, content, translation, log=None, locales=None):

        self.content = content
        self.translation = translation

        self.enabled_locales = locales
        self.lower_locales = [l.lower() for l in self.enabled_locales]

        self.log = log or logging.getLogger()

    def _process_locale(self, locale):
        """Return True if this locale should be processed."""

        if locale.lower().startswith('en'):
            return False

        return (locale in self.enabled_locales or

                self.content.translation_locale(locale)
                in self.enabled_locales or

                locale in self.lower_locales or

                self.content.translation_locale(locale.lower())
                in self.lower_locales
        )

    def update_translations(self, resources=None, force=False):
        """Update translations from content."""

        raise NotImplemented()

    def update_content(self, resources=None, force=False):
        """Update content translations."""

        raise NotImplemented()


class DeskTopics(Sync):

    def __init__(self, *args, **kwargs):

        super(DeskTopics, self).__init__(*args, **kwargs)

        self.TOPIC_STRINGS_SLUG = 'desk-topics'

    def update_translations(self, resources=None, force=False):
        """Update topics strings for translation from content."""

        tx = self.translation

        # asssemble the template catalog
        template = babel.messages.catalog.Catalog()
        for topic in self.content.topics():
            if self.content.topic_translatable(topic):
                template.add(self.content.topic_string(topic))

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

    def update_content(self, resources=None, force=False):
        """Pull topic strings translations into content."""

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
        for topic in self.content.topics():
            name = self.content.topic_string(topic)

            for locale in translated:

                if name in translated[locale]:

                    self.log.debug(
                        'Updating topic (%s) for locale (%s)' %
                        (name, locale),
                    )

                    self.content.update_topic_translation(
                        topic,
                        locale,
                        translated[locale][topic.name].string,
                    )

                else:

                    self.log.error(
                        'Topic name (%s) does not exist in locale (%s)' %
                        (name, locale),
                    )


class DeskTutorials(Sync):

    def __init__(self, *args, **kwargs):

        super(DeskTutorials, self).__init__(*args, **kwargs)

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

    def update_translations(self, resources=None, force=False):
        """Update translations from content."""

        if resources:
            articles = [
                self.desk.articles().by_id(r.strip())
                for r in resources
            ]
        else:
            articles = self.desk.articles()

        for a in articles:

            self.log.debug(
                'Inspecting Desk resource %s', a.api_href
            )

            for translation in a.translations.items().values():
                our_locale = self.content.translation_locale(translation.locale)

                self.log.debug('Checking locale %s', translation.locale)

                if not self._process_locale(translation.locale):
                    self.log.debug('Skipping locale.')
                    continue

                # make sure the project exists in Tx
                tx.get_project(our_locale)

                a_id = a.api_href.rsplit('/', 1)[1]
                if (force or
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

    def update_content(self, resources=None, force=False):
        "Pull Tutorials from Transifex to Desk."""

        tx = self.translation

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

            if resources:
                pull_resources = [
                    r.strip() for r in resources.split(',')
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
                    if self.content.content_locale(lang) in desk_translations:
                        desk_translations[self.content.content_locale(lang)].update(
                            **desk_translation
                        )
                    else:
                        desk_translations.create(
                            locale=self.content.content_locale(lang),
                            **desk_translation
                        )
