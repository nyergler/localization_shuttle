import logging
import optparse

from deskapi.models import DeskApi2

from shuttle import (
    english,
    sync,
    transifex,
)

from shuttle.content import desk


HANDLERS = dict(
    topics=sync.DeskTopics,
    tutorials=sync.DeskTutorials,
    english_topics=english.DeskEnglishTopics,
    english_tutorials=english.DeskEnglishTutorials,
)


def parse_args():

    parser = optparse.OptionParser()
    parser.add_option("-t", "--types", type="choice",
                      choices=(
                          'topics',
                          'tutorials',
                          'all',
                          'english_topics',
                          'english_tutorials',
                      ),
                      help="Types of content to sync: topics, english_topics, tutorials, english_tutorials, all")

    parser.add_option("--push", action="store_true",
                        help="Push content from Desk to Tx")
    parser.add_option("--pull", action="store_true",
                        help="Pull content from Tx to Desk")

    parser.add_option('-l', '--locales', action='store',
                      help="Comma delimited list of locales to process.")
    parser.add_option('-r', '--resources', action='store',
                      help="Comma delimited list of Desk Resource IDs to sync "
                      "(only supported for tutorials)",
    )

    parser.add_option('--force', action='store_true',
                      help='Always push to Tx even if not out of date.',
                      )

    return parser.parse_args()


def main():
    log = logging.getLogger()
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)

    options, args = parse_args()

    locales = options.locales
    if locales:
        locales = [l.strip() for l in locales.split(',')]

    deskApi = DeskApi2(
        sitename=settings.DESK_SITENAME,
        auth=(settings.DESK_USER, settings.DESK_PASSWD),
    )
    content = desk.DeskContent(deskApi)
    translation = transifex.Tx(tx_project_slug)

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
            sync.push()

        if options.pull:
            sync.pull()

if __name__ == '__main__':
    main()
