# Log Monitor Entry Point
from multiprocessing import Process, Queue, Value, Manager
from datetime import datetime, timedelta
from collections import OrderedDict

from file_watcher import watch_file
from user_interface import show_ui
from user_interface import MonitorUI


# stat refreshes every 10 seconds, called a "frame"
REFRESH_INTERVAL = 10
# alert is based on 2 minutes' sliding window, called a "scene"
ALERT_WINDOW = 120


def aggregate(log_q, alert_q, section_heat_map, aggregated_map, running):
    total_hit_count = 0
    frame_hit_count = 0
    frame_heat_map = dict()
    start_time = aggregated_map['start_time']
    next_aggregate_time = datetime.now() + timedelta(seconds=REFRESH_INTERVAL)
    while running.value == 1:
        log_item = log_q.get()
        frame_hit_count = frame_hit_count + 1
        hit_count = frame_heat_map.get(log_item.section, 0)
        frame_heat_map[log_item.section] = hit_count + 1
        # aggregate results
        if datetime.now() > next_aggregate_time:
            lps = 1.0 * frame_hit_count / REFRESH_INTERVAL
            aggregated_map['lps_frame'] = lps
            total_hit_count = total_hit_count + frame_hit_count
            time_delta = datetime.now() - start_time
            total_lps = total_hit_count / time_delta.seconds
            aggregated_map['lps_lifetime'] = total_lps

            aggregated_map['heat_map_frame'] = frame_heat_map
            # update total heat map
            for section, hit in frame_heat_map.items():
                hit_count = section_heat_map.get(section, 0) + hit
                section_heat_map[section] = hit_count

            # new frame
            frame_hit_count = 0
            frame_heat_map = dict()
            next_aggregate_time = datetime.now() + timedelta(seconds=REFRESH_INTERVAL)


class Monitor(object):

    def __init__(self, filenames):
        self._filenames = filenames
        self._processes = list()
        self._resource_manager = Manager()
        self._log_q = Queue()
        self._alert_q = Queue()
        self._running = Value('b', 1)
        self._section_hits = self._resource_manager.dict()
        self._aggregated_statistics = self._resource_manager.dict()
        self._aggregated_statistics['total_hit_count'] = 0
        self._aggregated_statistics['lps_frame'] = 0
        self._ui = MonitorUI(self._aggregated_statistics, self._running)

    def initialize(self):
        # watch files
        for filename in self._filenames:
            proc = Process(target=watch_file, args=(
                filename, self._log_q, self._running))
            self._processes.append(proc)
        # aggregate statistics
        proc = Process(target=aggregate, args=(
            self._log_q, self._alert_q, self._section_hits, self._aggregated_statistics, self._running))
        self._processes.append(proc)
        # UI
        proc = Process(target=self._ui.run)
        self._processes.append(proc)


    def start_monitor(self):
        self._aggregated_statistics['start_time'] = datetime.now()
        for process in self._processes:
            process.start()

    def wait_for_finish(self):
        for proc in self._processes:
            proc.join()


DEFAULT_LOG_FILES = ['sample_logs/test.log']
if __name__ == "__main__":
    monitor = Monitor(DEFAULT_LOG_FILES)
    monitor.initialize()
    monitor.start_monitor()
    monitor.wait_for_finish()
