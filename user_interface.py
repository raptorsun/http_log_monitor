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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stats = kwargs.get('stats', {})

    def create(self):
        self.keypress_timeout = 10
        self._lps_frame_text = self.add(
            npyscreen.TitleFixedText, name='LPS Frame', value='0', editable=False)
        self._lps_lifetime_text = self.add(
            npyscreen.TitleFixedText, name='LPS Lifetime', value='0', editable=False)
        self._time_text = self.add(
            npyscreen.TitleFixedText, name='Time', value='0', editable=False)

    def afterEditing(self):
        self.parentApp.NEXT_ACTIVE_FORM = None

    def while_waiting(self):
        self._lps_frame_text.value = self._stats.get('lps_frame', 0)
        self._lps_frame_text.display()
        self._lps_lifetime_text.value = self._stats.get('lps_lifetime', 0)
        self._lps_lifetime_text.display()
        self._time_text.value = time.asctime()
        self._time_text.display()


class MonitorUI(npyscreen.NPSAppManaged):
    def __init__(self, stats_dict={}, running=None):
        super().__init__()
        self._stats_dict = stats_dict
        self._running = running

    def onStart(self):
        self.addForm('MAIN', Dashboard, name='Dashboard',
                     stats=self._stats_dict)


if __name__ == '__main__':
    stats = {
        'lps_frame': 1.5,
    }
    ui = MonitorUI(stats)
    ui.run()
