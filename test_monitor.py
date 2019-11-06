import unittest
from multiprocessing import Value, Process
import queue
import time
from monitor import Monitor
from file_watcher import LogItem


class LogQProducer(object):
    def __init__(self, log_q, lps=1):
        self._log_q = log_q
        self._producer_proc = None
        self._sleep_interval = Value('f',  1.0 / lps)
        self._running = Value('b', 1)

    def start(self):
        self._running.value = 1
        self._producer_proc = Process(target=self.produce)
        self._producer_proc.start()

    def stop(self):
        self._running.value = 0

    def wait_for_finish(self):
        self._producer_proc.join()
        self._producer_proc = None

    def produce(self):

        while self._running.value == 1:
            item = LogItem('87.141.6.212 ',
                           '-',
                           'simon',
                           '[05/Nov/2019:01:44:46 +0100]',
                           '"POST /item/aves-business-theme/12854860"',
                           200,
                           8000,
                           '/item'
                           )
            self._log_q.put(item)
            time.sleep(self._sleep_interval.value)

    def set_lps(self, lps):
        self._sleep_interval.value = 1.0 / lps


class AlertQConsumer(object):
    def __init__(self, alert_q):
        self._alert_on = Value('b', 0)
        self._alert_q = alert_q
        self._get_timeout = 1
        self._consumer_proc = None
        self._running = Value('b', 1)

    def start(self):
        self._running.value = 1
        self._consumer_proc = Process(target=self.consume)
        self._consumer_proc.start()

    def consume(self):
        while self._running.value == 1:
            try:
                item = self._alert_q.get(timeout=self._get_timeout)
                if item and item[0]:
                    self._alert_on.value = 1
                elif item and not item[0]:
                    self._alert_on.value = 0
            except queue.Empty:
                continue

    def stop(self):
        self._running.value = 0

    def wait_for_finish(self):
        self._consumer_proc.join()

    def alert_on(self):
        return self._alert_on.value == 1


# shorter duration for faster testing
FRAME_INTERVAL = 5
SCENE_INTERVAL = 20


class MonitorTest(unittest.TestCase):
    def setUp(self):
        self._threshold = 10
        # shorter duration for faster testing
        self._monitor = Monitor([], self._threshold,
                                FRAME_INTERVAL, SCENE_INTERVAL)
        self._log_producer = LogQProducer(self._monitor._log_q)
        self._alert_consumer = AlertQConsumer(self._monitor._alert_q)

    def tearDown(self):
        self._log_producer.stop()
        self._log_producer.wait_for_finish()
        self._alert_consumer.stop()
        self._alert_consumer.wait_for_finish()
        self._monitor.stop()
        self._monitor.wait_for_finish()

    def test_alert_on_and_off(self):
        self._alert_consumer.start()
        self.assertFalse(self._alert_consumer.alert_on())
        self._monitor.initialize()
        ui_proc = self._monitor._processes.pop()
        self._monitor.start()
        self._log_producer.set_lps(1)
        self._log_producer.start()
        time.sleep(SCENE_INTERVAL)
        self.assertFalse(self._alert_consumer.alert_on())
        # increase traffic
        self._log_producer.set_lps(90)
        lps_scene = 0
        lps_total = 0

        # wait till alert triggering condition met
        while lps_scene < lps_total + self._threshold:
            lps_10s = self._monitor._aggregated_statistics['lps_frame']
            lps_scene = self._monitor._aggregated_statistics['lps_scene']
            lps_total = self._monitor._aggregated_statistics['lps_lifetime']
            time.sleep(FRAME_INTERVAL)

        # check alert
        time.sleep(1)
        self.assertTrue(self._alert_consumer.alert_on())

        # drop traffic and wait alert release condition met
        self._log_producer.set_lps(1)
        while lps_scene > lps_total + self._threshold:
            lps_10s = self._monitor._aggregated_statistics['lps_frame']
            lps_scene = self._monitor._aggregated_statistics['lps_scene']
            lps_total = self._monitor._aggregated_statistics['lps_lifetime']
            time.sleep(FRAME_INTERVAL)

        # check alert is off
        time.sleep(1)
        self.assertFalse(self._alert_consumer.alert_on())


if __name__ == "__main__":
    unittest.main(verbosity=2)
