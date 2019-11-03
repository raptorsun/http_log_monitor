# Log Monitor Entry Point
from multiprocessing import Process, Queue, Value, Manager
from queue import Empty
from datetime import datetime, timedelta
from collections import OrderedDict

from file_watcher import watch_file
from user_interface import show_ui
from user_interface import MonitorUI


# stat refreshes every 10 seconds, called a "frame"
REFRESH_INTERVAL = 10
# alert is based on 2 minutes' sliding window, called a "scene"
ALERT_WINDOW = 120
# number of frames in a scene
NB_REFRESH_PER_ALERT_WINDOW = int(ALERT_WINDOW / REFRESH_INTERVAL)

# wait for maximum 1 second when polling log queue
LOG_QUEUE_TIMEOUT = 1


def aggregate(log_q, alert_q, section_heat_map, aggregated_map, alert_threshold_lps, running):
    total_hit_count = 0
    frame_hit_count = 0
    frame_heat_map = dict()
    # circular buffer for hit counter in alert window
    frames_in_scene_hit_counts = [
        None for _ in range(NB_REFRESH_PER_ALERT_WINDOW)]
    frame_index_in_scene = 0
    start_time = aggregated_map['start_time']
    alter_start_time = start_time + timedelta(seconds=ALERT_WINDOW)
    alert_on = False
    aggregated_map['lps_frame'] = 0
    aggregated_map['lps_scene'] = 0
    aggregated_map['lps_lifetime'] = 0

    next_aggregate_time = datetime.now() + timedelta(seconds=REFRESH_INTERVAL)
    while running.value == 1:
        try:
            log_item = log_q.get(timeout=LOG_QUEUE_TIMEOUT)
            frame_hit_count = frame_hit_count + 1
            hit_count = frame_heat_map.get(log_item.section, 0)
            frame_heat_map[log_item.section] = hit_count + 1
        except Empty as err:
            log_item = None

        # aggregate results of frame
        if datetime.now() > next_aggregate_time:
            lps = 1.0 * frame_hit_count / REFRESH_INTERVAL
            aggregated_map['lps_frame'] = lps
            total_hit_count = total_hit_count + frame_hit_count

            time_delta = datetime.now() - start_time
            total_lps = total_hit_count / time_delta.seconds
            aggregated_map['lps_lifetime'] = total_lps

            frames_in_scene_hit_counts[frame_index_in_scene] = frame_hit_count
            frame_index_in_scene = (
                frame_index_in_scene + 1) % NB_REFRESH_PER_ALERT_WINDOW
            if datetime.now() > alter_start_time:
                scene_lps = sum(frames_in_scene_hit_counts) * \
                    1.0 / ALERT_WINDOW
            else:
                scene_lps = total_lps
            aggregated_map['lps_scene'] = scene_lps
            if scene_lps > total_lps + alert_threshold_lps.value:
                alert_on = True
                alert_msg = 'High traffic generated an alert - hits = {}, triggered at {}'.format(
                    scene_lps, datetime.now())
                alert_q.put((alert_on, alert_msg))
            elif alert_on:
                alert_on = False
                alert_msg = 'Alert Off - Traffic returned to normal at {}'.format(
                    datetime.now())
                alert_q.put((alert_on, alert_msg))

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
        self._alert_threshold = Value('L', 5)
        self._section_hits = self._resource_manager.dict()
        self._aggregated_statistics = self._resource_manager.dict()
        self._aggregated_statistics['total_hit_count'] = 0
        self._aggregated_statistics['lps_frame'] = 0
        self._ui = MonitorUI(self._aggregated_statistics,
                             self._alert_q, self._running)

    def initialize(self):
        # watch files
        for filename in self._filenames:
            proc = Process(target=watch_file, args=(
                filename, self._log_q, self._running))
            self._processes.append(proc)
        # aggregate statistics
        proc = Process(target=aggregate, args=(
            self._log_q, self._alert_q, self._section_hits, self._aggregated_statistics, self._alert_threshold, self._running))
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
