import datetime
import time
from collections import Counter
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
        self._alert_q = kwargs.get('alert_q', None)

    def create(self):
        self.keypress_timeout = 10

        self.how_exited_handers[npyscreen.wgwidget.EXITED_ESCAPE] = self.exit_application

        height, width = self.useable_space()
        max_widget_width = int(0.4 * width)

        self._lps_frame_text = self.add(
            npyscreen.TitleFixedText, name='LPS 10s', value='0', editable=False,
            max_width=max_widget_width, max_height=1)
        self._lps_scene_text = self.add(
            npyscreen.TitleFixedText, name='LPS 2min', value='0', editable=False,
            max_width=max_widget_width, max_height=1)
        self._lps_lifetime_text = self.add(
            npyscreen.TitleFixedText, name='LPS Lifetime', value='0', editable=False,
            max_width=max_widget_width, max_height=1)
        self._time_text = self.add(
            npyscreen.TitleFixedText, name='Time', value='0', editable=False,
            max_width=max_widget_width, max_height=1)

        available_height = height - 4 - 4  # margin  = 4px, 4 text boxes = 4px
        self._section_hit_list = self.add(
            npyscreen.TitlePager, name="Popular Sections", editable=False,
            max_width=max_widget_width, max_height=int(available_height/2))
        self._alert_list = self.add(
            npyscreen.TitleBufferPager, name="Alerts", editable=False,
            max_width=max_widget_width, max_height=int(available_height/2))

    def afterEditing(self):
        self.parentApp.NEXT_ACTIVE_FORM = None

    def while_waiting(self):
        self._lps_frame_text.value = '{:10.3f}'.format(
            self._stats.get('lps_frame', 0))
        self._lps_frame_text.display()
        self._lps_lifetime_text.value = '{:10.3f}'.format(
            self._stats.get('lps_lifetime', 0))
        self._lps_lifetime_text.display()
        self._lps_scene_text.value = '{:10.3f}'.format(
            self._stats.get('lps_scene', 0))
        self._lps_scene_text.display()
        self._time_text.value = time.asctime()
        self._time_text.display()

        heatmap = self._stats.get('heat_map_frame', {})
        top_5_sections = Counter(heatmap).most_common(5)
        top_5_sections_str = [
            '{} {}'.format(x[0], x[1]) for x in top_5_sections
        ]
        self._section_hit_list.values = top_5_sections_str
        self._section_hit_list.display()

        if self._alert_q and not self._alert_q.empty():
            alert_item = self._alert_q.get()
            alert_on = alert_item[0]
            alert_msg = alert_item[1]
            self._alert_list.buffer([alert_msg, ], scroll_end=True)
            self._alert_list.display()

    def exit_application(self):
        self.parentApp.setNextForm(None)
        self.editing = False
        self.parentApp.signal_exit()


class MonitorUI(npyscreen.NPSAppManaged):
    def __init__(self, stats_dict={}, alert_q=None, running=None):
        super().__init__()
        self._stats_dict = stats_dict
        self._running = running
        self._alert_q = alert_q

    def onStart(self):
        self.addForm('MAIN', Dashboard, name='Dashboard',
                     stats=self._stats_dict, alert_q=self._alert_q)

    def signal_exit(self):
        self._running.value = 0


if __name__ == '__main__':
    stats = {
        'lps_frame': 1.5,
    }
    ui = MonitorUI(stats)
    ui.run()
