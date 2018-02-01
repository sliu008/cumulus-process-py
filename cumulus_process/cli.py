#!/usr/bin/env python

import os
import sys
import argparse
import json
import logging
from cumulus_process.version import __version__

logger = logging.getLogger(__name__)


def parse_args(cls, args):
    """ Parse arguments for data processing """
    desc = '%s Processing' % cls.__name__
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser0 = argparse.ArgumentParser(description=desc)

    pparser = argparse.ArgumentParser(add_help=False)
    pparser.add_argument('--version', help='Print version and exit', action='version', version=__version__)
    pparser.add_argument('--path', help='Local working path', default='')
    pparser.add_argument('--loglevel', default=2, type=int,
                         help='0:all, 1:debug, 2:info, 3:warning, 4:error, 5:critical')

    subparsers = parser0.add_subparsers(dest='command')

    parser = subparsers.add_parser('process', parents=[pparser], help='Process local files', formatter_class=dhf)
    parser.add_argument('filenames', nargs='*', default=[])

    recipe_parser = subparsers.add_parser('recipe', parents=[pparser], help='Process recipe file', formatter_class=dhf)
    recipe_parser.add_argument('recipe', help='Granule recipe (JSON, S3 address, or local file)')
    recipe_parser.add_argument('--noclean', action='store_true', default=False,
                               help='Do not remove local files when done')

    h = 'Start Step Function Activity'
    activity_parser = subparsers.add_parser('activity', parents=[pparser], help=h, formatter_class=dhf)
    activity_parser.add_argument('--arn', help='ARN for Step Function Activity', default=os.getenv('ACTIVITY_ARN'))

    parser0 = cls.add_parser_args(parser0)

    parsed_args = vars(parser0.parse_args(args))

    return parsed_args


def cli(cls):
    """ Command Line Interface for a specific Granule class """
    args = parse_args(cls, sys.argv[1:])

    logger.setLevel(args.pop('loglevel') * 10)
    cmd = args.pop('command')

    # process local files
    if cmd == 'process':
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        process = cls.run(noclean=True, **args)
    # process with a recipe
    elif cmd == 'recipe':
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        payload = cls.run(**args)
        bname = os.path.splitext(os.path.basename(args['recipe']))[0]
        fname = os.path.join(args['path'], bname + '_out.json')
        with open(fname, 'w') as f:
            f.write(json.dumps(payload))
    # run as a service
    elif cmd == 'activity':
        cls.activity(args['arn'])
    else:
        logger.error('Unknown command %s (choose between: process, recipe, activity)' % cmd)