#!/usr/bin/env python

# Log Monitor Entry Point
from multiprocessing import Process, Queue, Value, Manager
import queue
from datetime import datetime, timedelta
from collections import OrderedDict
import getopt
import sys

from file_watcher import FileWatcher
from user_interface import MonitorUI


# stat refreshes every 10 seconds, called a "frame"
REFRESH_INTERVAL = 10
# alert is based on 2 minutes' sliding window, called a "scene"
ALERT_WINDOW = 120
# wait for maximum 1 second when polling log queue
LOG_QUEUE_TIMEOUT = 1


class Monitor(object):

    def __init__(self, filenames, threshold_lps,
                 frame_interval=REFRESH_INTERVAL,
                 scene_interval=ALERT_WINDOW):
        self._filenames = filenames
        self._processes = list()
        self._resource_manager = Manager()
        self._log_q = Queue()
        self._alert_q = Queue()
        self._running = Value('b', 1)
        self._alert_threshold = Value('L', threshold_lps)
        self._frame_interval = frame_interval
        self._scene_interval = scene_interval
        self._frames_per_scene = int(scene_interval / frame_interval)
        self._section_hits = self._resource_manager.dict()
        self._aggregated_statistics = self._resource_manager.dict()
        self._aggregated_statistics['total_hit_count'] = 0
        self._aggregated_statistics['lps_frame'] = 0
        self._ui = MonitorUI(self._aggregated_statistics,
                             self._alert_q, self._running)

    def initialize(self):
        # watch files
        for filename in self._filenames:
            fw = FileWatcher(filename)
            proc = Process(target=fw.watch, args=(self._log_q, self._running))
            self._processes.append(proc)
        # aggregate statistics
        proc = Process(target=self.aggregate)
        self._processes.append(proc)
        # UI
        proc = Process(target=self._ui.run)
        self._processes.append(proc)

    def start(self):
        self._aggregated_statistics['start_time'] = datetime.now()
        for process in self._processes:
            process.start()

    def stop(self):
        self._running.value = 0

    def wait_for_finish(self):
        for proc in self._processes:
            proc.join()

    def aggregate(self):
        total_hit_count = 0
        frame_hit_count = 0
        frame_heat_map = dict()
        host_heat_map = dict()

        # circular buffer for hit counter in alert window
        frames_in_scene_hit_counts = [
            None for _ in range(self._frames_per_scene)]
        frame_index_in_scene = 0
        start_time = self._aggregated_statistics['start_time']
        alter_start_time = start_time + timedelta(seconds=self._scene_interval)
        alert_on = False
        self._aggregated_statistics['lps_frame'] = 0
        self._aggregated_statistics['lps_scene'] = 0
        self._aggregated_statistics['lps_lifetime'] = 0

        next_aggregate_time = datetime.now() + timedelta(seconds=self._frame_interval)
        while self._running.value == 1:
            try:
                log_item = self._log_q.get(timeout=LOG_QUEUE_TIMEOUT)
                frame_hit_count = frame_hit_count + 1
                hit_count = frame_heat_map.get(log_item.section, 0)
                frame_heat_map[log_item.section] = hit_count + 1
                bandwidth_consumed = host_heat_map.get(log_item.remotehost, 0)
                host_heat_map[log_item.remotehost] = bandwidth_consumed + \
                    int(log_item.size)
            except queue.Empty as err:
                log_item = None

            # aggregate results of frame
            if datetime.now() > next_aggregate_time:
                lps = 1.0 * frame_hit_count / self._frame_interval
                self._aggregated_statistics['lps_frame'] = lps
                total_hit_count = total_hit_count + frame_hit_count

                time_delta = datetime.now() - start_time
                total_lps = total_hit_count / time_delta.seconds
                self._aggregated_statistics['lps_lifetime'] = total_lps

                frames_in_scene_hit_counts[frame_index_in_scene] = frame_hit_count
                frame_index_in_scene = (
                    frame_index_in_scene + 1) % self._frames_per_scene
                if datetime.now() > alter_start_time:
                    scene_lps = sum(frames_in_scene_hit_counts) * \
                        1.0 / self._scene_interval
                else:
                    scene_lps = total_lps
                self._aggregated_statistics['lps_scene'] = scene_lps
                if scene_lps > total_lps + self._alert_threshold.value:
                    alert_on = True
                    alert_msg = 'High traffic generated an alert - hits = {:.2f}, triggered at {}'.format(
                        scene_lps, datetime.now().strftime('%H:%M:%S'))
                    self._alert_q.put((alert_on, alert_msg))
                elif alert_on:
                    alert_on = False
                    alert_msg = 'Alert Off - Traffic returned to normal at {}'.format(
                        datetime.now().strftime('%H:%M:%S'))
                    self._alert_q.put((alert_on, alert_msg))

                self._aggregated_statistics['heat_map_frame'] = frame_heat_map
                self._aggregated_statistics['host_heat_map'] = host_heat_map
                # update total heat map
                for section, hit in frame_heat_map.items():
                    hit_count = self._section_hits.get(section, 0) + hit
                    self._section_hits[section] = hit_count

                # new frame
                frame_hit_count = 0
                frame_heat_map = dict()
                next_aggregate_time = datetime.now() + timedelta(seconds=self._frame_interval)


def usage():
    print('''
    HTTP Log Monitor
    Usage:
    monitor.py -s access.log [-s other_access.log] [-t 10]
    -s --source     HTTP access log,
                    multiple log files can be passed by adding "-s log1 -s log2"
    -t --threshold  Threshold in Access Per Second to trigger alarm when 2 minute
                    average is above the lifetime average of this threshold. Default is 10.
    ''')


DEFAULT_LOG_FILES = ['sample_logs/test.log']
if __name__ == "__main__":
    log_files = list()
    threshold_aps = 10

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:t:', [
                                   'help', 'source=', 'threshold='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s", "--source"):
            log_files.append(a)
        elif o in ("-t", "--threshold"):
            threshold_aps = int(a)
        else:
            assert False, "unhandled option"
    monitor = Monitor(log_files, threshold_aps)
    monitor.initialize()
    monitor.start()
    monitor.wait_for_finish()
