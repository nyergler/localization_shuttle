import argparse
import logging

from shuttle import (
    english,
    sync,
)

import shuttle.content.desk
import shuttle.translators.transifex

HANDLERS = dict(
    topics=sync.DeskTopics,
    tutorials=sync.DeskTutorials,
    english_topics=english.DeskEnglishTopics,
    english_tutorials=english.DeskEnglishTutorials,
)

CONTENT_CLASSES = (
    ('desk', shuttle.content.desk.DeskContent),
)

TRANSLATION_CLASSES = (
    ('transifex', shuttle.translators.transifex.Tx),
)


def make_arg_parser():
    """Return a configured ArgumentParser."""

    parser = argparse.ArgumentParser(
        description='Shuttle content between sources and translators.',
    )

    parser.add_argument("-t", "--types",
                      choices=(
                          'topics',
                          'tutorials',
                          'all',
                          'english_topics',
                          'english_tutorials',
                      ),
                      help="Types of content to sync: topics, english_topics, tutorials, english_tutorials, all")

    parser.add_argument("--push", action="store_true",
                      help="Push content from Desk to Tx")
    parser.add_argument("--pull", action="store_true",
                      help="Pull content from Tx to Desk")

    parser.add_argument('--content', action='store',
                      choices=[c[0] for c in CONTENT_CLASSES])
    parser.add_argument('--translation', action='store',
                      choices=[c[0] for c in TRANSLATION_CLASSES])

    parser.add_argument('--locales', '-l', action='store',
                      help="Comma delimited list of locales to process.")
    parser.add_argument('--resources', '-r', action='store',
                      default='',
                      help="Comma delimited list of Content resource IDs to sync "
                      "(only supported for tutorials)",
    )

    parser.add_argument('--force', action='store_true',
                      help='Always push to Tx even if not out of date.',
                      )

    # add the content provider argument groups
    for name, cls in CONTENT_CLASSES:
        group = parser.add_argument_group(
            '--content=%s' % name,
        )
        cls.add_arguments(group)

    # add the translation provider argument groups
    for name, cls in TRANSLATION_CLASSES:
        group = parser.add_argument_group(
            '--translation=%s' % name,
        )
        cls.add_arguments(group)

    return parser


def main():
    log = logging.getLogger()
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)

    parser = make_arg_parser()
    options = parser.parse_args()

    locales = options.locales
    if locales:
        locales = [l.strip() for l in locales.split(',')]

    # instantiate the content handler
    content_cls = dict(CONTENT_CLASSES)[options.content]
    content_kwargs = {
        name: getattr(options, name)
        for name in content_cls.get_option_names()
    }
    content = content_cls(**content_kwargs)

    # instantiate the translation handler
    translation_cls = dict(TRANSLATION_CLASSES)[options.translation]
    translation_kwargs = {
        name: getattr(options, name)
        for name in translation_cls.get_option_names()
    }
    translation = translation_cls(**translation_kwargs)

    # figure out what sync types we're handling
    sync_types = []
    if options.types == 'all':

        # add all types
        for handler in HANDLERS:
            sync_types.append(
                HANDLERS[handler](
                    content,
                    translation,
                    log=log,
                    locales=locales,
                )
            )

    else:
        sync_types.append(
            HANDLERS[options.types](
                content,
                translation,
                log=log,
                locales=locales,
            )
        )

    for sync in sync_types:

        if options.push:
            sync.update_translations(
                resources=options.resources.split(','),
                force=options.force,
            )

        if options.pull:
            sync.update_content()

if __name__ == '__main__':
    main()
