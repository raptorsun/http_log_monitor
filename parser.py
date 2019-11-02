import re

# pattern to get [date], "request" and space delimitd string
PATTERN_LINE_ITEM = '\[.+\]|[^"\s]\S*|".+?"'
PATTERN_SECTION = '/[^"\s/]+'


class LogParser(object):
    def __init__(self, pattern_item=PATTERN_LINE_ITEM, pattern_section=PATTERN_SECTION):
        self._pattern_item = re.compile(pattern_item)
        self._pattern_section = re.compile(pattern_section)

    def parse_line(self, line):
        # fields are defined as https://www.w3.org/Daemon/User/Config/Logging.html#common-logfile-format
        remotehost = ''
        rfc931 = ''
        authuser = ''
        date = None
        request = ''
        status = 0
        size = 0

        items = self._pattern_item.findall(line)
        if len(items) < 7:
            return remotehost, rfc931, authuser, date, request, status, size

        remotehost = items[0]
        rfc931 = items[1]
        authuser = items[2]
        date = items[3]
        request = items[4]
        status = items[5]
        size = items[6]

        return remotehost, rfc931, authuser, date, request, status, size

    def section_from_request(self, request):
        section = self._pattern_section.search(request)
        return section.group(0) if section else ''


# tests
def test():
    INPUT_1 = '9.169.248.247 - - [12/Dec/2015:18:25:11 +0100] "GET /administrator/ HTTP/1.1" 200 4263 "-" "Mozilla/5.0 (Windows NT 6.0; rv:34.0) Gecko/20100101 Firefox/34.0" "-"'
    lp = LogParser()
    remotehost, rfc931, authuser, date, request, status, size = lp.parse_line(
        INPUT_1)
    print((remotehost, rfc931, authuser, date, request, status, size))
    section = lp.section_from_request(request)
    print(section)


if __name__ == "__main__":
    test()
