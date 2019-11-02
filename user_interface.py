import datetime
import time
from collections import OrderedDict
import threading

import npyscreen

UI_REFRESH_INTERVAL = 0.5


def show_ui(statistics, section_hit_dict):
    while True:
        frame_lps = statistics.get('lps_frame', 0)
        print('current LPS:', frame_lps)
        frame_heat_map = statistics.get('heat_map_frame', {})
        sorted_frame_heat_map = OrderedDict({k: v for k, v in sorted(
            frame_heat_map.items(), key=lambda x: x[1])})
        print('frame heat map')
        for key, value in sorted_frame_heat_map.items():
            print(key,  value)

        time.sleep(1.0)


class Dashboard(npyscreen.Form):

    def create(self):
        self.lps_text = self.add(
            npyscreen.TitleFixedText, name='LPS', value='', editable=False)
        self.time_text = self.add(
            npyscreen.TitleFixedText, name='Time', value='', editable=False)

    def afterEditing(self):
        self.parentApp.setNextForm(None)


class MonitorUI(npyscreen.NPSAppManaged):
    def __init__(self, stats_dict={}, running=None):
        super().__init__()
        self._stats_dict = stats_dict
        self._running = running

    def onStart(self):

        self.addForm('MAIN', Dashboard, name='Dashboard')

        self.thread_time = threading.Thread(target=self.update_stats)
        self.thread_time.daemon = True
        self.thread_time.start()

    def update_stats(self):
        while not self._running or self._running.value == 1:
            self.getForm('MAIN').lps_text.value = str(self._stats_dict.get(
                'lps_frame', 0))
            self.getForm('MAIN').lps_text.display()
            self.getForm('MAIN').time_text.value = str(datetime.datetime.now())
            self.getForm('MAIN').time_text.display()
            time.sleep(UI_REFRESH_INTERVAL)

    # def while_waiting(self):
    #     self.getForm('MAIN').lps_text.value = self._stats_dict.get(
    #         'lps_frame', 0)
    #     self.getForm('MAIN').lps_text.display()
    #     self.getForm('MAIN').time_text.value = str(datetime.datetime.now())
    #     self.getForm('MAIN').time_text.display()

    def show_stat(self):
        while self._running.value == 1:
            lps = self._stats_dict['lps_frame']
            print('lps:', lps, ', runnning:', self._running.value)
            time.sleep(1)


if __name__ == '__main__':
    stats = {
        'lps_frame': 1.5,
    }
    TestApp = MonitorUI(stats).run()
