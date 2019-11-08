#!/usr/bin/env python
import getopt
import sys
import os
import time
import random
from datetime import datetime, timedelta

DEFAULT_LOG_SOURCE_FILE = 'sample_logs/access.log'
DEFAULT_OUTPUT_FILE = 'sample_logs/test.log'
DEFAULT_LPS = 1  # lines per second


HTTP_METHODS = [
    'GET', 'POST', 'PUT', 'DELETE', 'HEAD'
]

URLS_CANDIDATES = [
    '/administrator/index.php',
    '/phocadocumentation',
    '/item/3d-stroked-ink-actions/8037850',
    '/item/archi-interior-design-joomla-template/14576483',
    '/item/august/13903079',
    '/item/aves-business-theme/12854860',
    '/item/bigc-shop-responsive-woocommerce-theme/14279188',
    '/item/cartoon-cavemen/14669255',
    '/images/stories/slideshow/almhuette_raith_02.jpg',
    '/templates/jp_hotel/js/moomenu.js',
    '/modules/mod_bowslideshow/tmpl/images/image_shadow.png',

]

USERNAMES = [
    'SMITH',
    'JOHNSON',
    'WILLIAMS',
    'JONES',
    'BROWN',
    'DAVIS',
    'MILLER',
    'WILSON',
    'MOORE',
    'TAYLOR',
]

STATUS = [
    200,
    201,
    301,
    404,
    500
]


class LogGenerator(object):
    def __init__(self, source_file, dest_file, lps=DEFAULT_LPS):
        self._source_file = source_file
        self._dest_file = dest_file
        self._sleep_duration = 1.0 / lps
        random.seed(time.asctime())
        self.timestamp = datetime.now()
        self.timestamp_str = self.timestamp.strftime(
            '[%d/%b/%Y:%H:%M:%S +0100]')

    def generate_file(self):
        src_file = open(self._source_file, 'r')
        dest_file = open(self._dest_file, 'a+')

        for line in src_file.readlines():
            dest_file.write(line)
            dest_file.flush()
            os.fsync(dest_file.fileno())
            time.sleep(self._sleep_duration)

    def get_random_log_line(self):
        host = ".".join(map(str, (int(random.random()*255) for _ in range(4))))
        user = random.choice(USERNAMES)
        method = random.choice(HTTP_METHODS)
        url = random.choice(URLS_CANDIDATES)
        status = random.choice(STATUS)
        size = int(random.random()*80000)

        if self.timestamp + timedelta(seconds=1) < datetime.now():
            self.timestamp = datetime.now()
            self.timestamp_str = self.timestamp.strftime(
                '[%d/%b/%Y:%H:%M:%S +0100]')
        return f'{host} - {user} {self.timestamp_str} "{method} {url}" {status} {size} "-" "Mozilla/5.0 (Windows NT 6.0; rv:34.0) Gecko/20100101 Firefox/34.0" "-"\n'

    def generate_random_log(self):
        dest_file = open(self._dest_file, 'a+')

        while True:
            line = self.get_random_log_line()
            dest_file.write(line)
            dest_file.flush()
            os.fsync(dest_file.fileno())
            time.sleep(self._sleep_duration)


def usage():
    print('''
Write logs from source to destination file with a rate
-s source file
-d destination file
-l lines per second
''')


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:d:l:', [
                                   'help', 'source=', 'dest=', 'lps='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    source = None
    destination = None
    lines_per_second = DEFAULT_LPS
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s", "--source"):
            source = a
        elif o in ("-d", "--dest"):
            destination = a
        elif o in ("-l", "--lps"):
            lines_per_second = int(a)
        else:
            assert False, "unhandled option"

    lg = LogGenerator(source, destination, lines_per_second)
    if source:
        lg.generate_file()
    else:
        lg.generate_random_log()


if __name__ == "__main__":
    main()
