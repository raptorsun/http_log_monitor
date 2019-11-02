import getopt
import sys
import os
import time

DEFAULT_LOG_SOURCE_FILE = 'sample_logs/access.log'
DEFAULT_OUTPUT_FILE = 'sample_logs/test.log'
DEFAULT_LPS = 1  # lines per second


def generate_file(src_filename, dest_filename, lps):
    src_file = open(src_filename, 'r')
    dest_file = open(dest_filename, 'a+')
    sleep_duration = 1.0 / lps
    for line in src_file.readlines():
        dest_file.write(line)
        dest_file.flush()
        os.fsync(dest_file.fileno())
        print(line)
        time.sleep(sleep_duration)


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
    source = DEFAULT_LOG_SOURCE_FILE
    destination = DEFAULT_OUTPUT_FILE
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

    generate_file(source, destination, lines_per_second)


if __name__ == "__main__":
    main()
