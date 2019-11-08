import os
import time

from parser import LogParser


class LogItem(object):
    '''
    This structure contains information from one line in the HTTP access log
    '''

    def __init__(self, remotehost, rfc931, authuser, date, request, status, size, section):
        self.remotehost = remotehost
        self.rfc931 = rfc931
        self.authuser = authuser
        self.date = date
        self.request = request
        self.status = status
        self.size = size
        self.section = section

    def __str__(self):
        return '{} {} {} {} {} {} {} {}'.format(
            self.remotehost,
            self.rfc931,
            self.authuser,
            self.date,
            self.request,
            self.status,
            self.size,
            self.section
        )


DEFAULT_READLINE_SLEEP = 0.1
DEFAULT_READLINE_TIMEOUT = 1

# minic the "tail -f" on Linux


class FileWatcher(object):
    def __init__(self, filename, timeout=DEFAULT_READLINE_TIMEOUT):
        try:
            self._file_handle = open(filename, 'r')
            self._file_handle.seek(0, os.SEEK_END)
        except FileNotFoundError as err:
            print(err)
            raise err
        if timeout == 0:
            self._readline_max_sleep_count = 0
        else:
            self._readline_max_sleep_count = int(
                timeout / DEFAULT_READLINE_SLEEP)

    def readline(self):
        line = None
        sleep_count = 0
        while not line:
            line = self._file_handle.readline()
            if line == '':
                time.sleep(DEFAULT_READLINE_SLEEP)
                # return empty line after long time no line
                if self._readline_max_sleep_count and sleep_count > self._readline_max_sleep_count:
                    return ''
                sleep_count = sleep_count + 1

        return line

    def __iter__(self):
        return self

    def __next__(self):
        return self.readline()

    def watch(self, log_queue, running):
        parser = LogParser()
        while running.value == 1:
            line = self.readline()
            if line == '':
                continue
            remotehost, rfc931, authuser, date, request, status, size = parser.parse_line(
                line)
            if not request:
                continue
            section = parser.section_from_request(request)
            try:
                size = int(size)
            except ValueError:
                size = 0
            log_item = LogItem(remotehost, rfc931, authuser,
                               date, request, status, size, section)
            log_queue.put(log_item)
