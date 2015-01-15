from cStringIO import StringIO
import logging

import babel.messages.catalog
import babel.messages.pofile
from deskapi.models import DeskApi2
import txlib.api.translations
from txlib.http.exceptions import NotFoundError

from translators.transifex import Tx

from shuttle.sync import DeskTxSync


class DeskEnglishTxSync(DeskTxSync):

    def __init__(self, *args, **kwargs):

        return super(DeskEnglishTxSync, self).__init__(None, *args, **kwargs)

    def _process_locale(self, locale):

        if not locale.lower().startswith('en'):

            return False

        return locale.lower() in self.lower_locales


class DeskEnglishTopics(DeskEnglishTxSync):

    def push(self):

        self.log.info("Refusing to Push topics for English locales.")

    def pull(self):

        for topic in self.desk.topics():

            if topic.in_support_center:

                for locale in self.enabled_locales:

                    if not self._process_locale(locale):
                        continue

                    log.info('Preparing to copy topic %s (%s) for %s' % (
                        topic.name,
                        topic.api_href,
                        locale,
                        ))

                    locale_kwargs = dict(
                        name=topic.name,
                        description=topic.description,
                        in_support_center=True,
                    )

                    if locale not in topic.translations:
                        success = topic.translations.create(
                            locale=locale,
                            **locale_kwargs
                        )
                    else:
                        success = topic.translations[locale].update(
                            **locale_kwargs
                        )

                    if not success:
                        log.error('Error updating topic %s (%s)' % (
                            topic.name,
                            topic.api_href,
                            ))


class DeskEnglishTutorials(DeskEnglishTxSync):

    def push(self):

        self.log.info("Refusing to Push tutorials for English locales.")

    def pull(self):

        if self.options.resources:
            articles = [
                self.desk.articles().by_id(r.strip())
                for r in self.options.resources.split(',')
            ]
        else:
            articles = self.desk.articles()

        for a in articles:

            for translation in a.translations:

                if not self._process_locale(translation.locale):
                    self.log.debug('Skipping locale %s.', translation.locale)
                    continue

                if (self.options.force or
                    translation.out_of_date
                ):

                    log.info('Preparing to push %s for %s',
                             a.id,
                             translation.locale,
                    )

                    success = translation.update(
                        subject=a.subject,
                        body=a.body,
                    )

                    if not success:
                        log.error('Error updating %s (desk ID %s).',
                                  translation.locales,
                                  a.id,
                        )
