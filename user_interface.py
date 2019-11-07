import datetime
import time
from collections import Counter
import threading
import weakref

import npyscreen

UI_REFRESH_INTERVAL = 0.5


class OneDecimalSlider(npyscreen.Slider):
    def translate_value(self):
        return f'{self.value:.1f} / {self.out_of:.1f}'


class TitleOneDecimalSlider(npyscreen.TitleSlider):
    _entry_type = OneDecimalSlider


class TrafficBox(npyscreen.BoxTitle):
    def set_values(self, val_10s, val_2m, val_lifetime):
        self._10s_value = val_10s
        self._2m_value = val_2m
        self._lifetime_value = val_lifetime

        # automatically increase slider range
        tmp_max = max(val_10s, val_2m, val_lifetime)
        if tmp_max == 0:
            self._slider_max = 50
        elif self._slider_max < tmp_max:
            self._slider_max = tmp_max * 1.3
        elif tmp_max < self._slider_max * 0.6:
            self._slider_max = self._slider_max * 0.6
        self._my_widgets[0].entry_widget.out_of = self._slider_max
        self._my_widgets[1].entry_widget.out_of = self._slider_max
        self._my_widgets[2].entry_widget.out_of = self._slider_max

        self._my_widgets[0].value = self._10s_value
        self._my_widgets[1].value = self._2m_value
        self._my_widgets[2].value = self._lifetime_value

    def make_contained_widget(self, contained_widget_arguments=None):
        self._my_widgets = []
        _rely = self.rely+1
        _relx = self.relx+1
        width = self.width

        self._slider_max = 10
        self._10s_value = 0
        self._2m_value = 0
        self._lifetime_value = 0

        self._my_widgets.append(TitleOneDecimalSlider(
            self.parent,
            rely=_rely,
            relx=_relx,
            max_width=width - 4,
            name='LPS 10s',
            out_of=self._slider_max,
            value=self._10s_value,
            editable=False
        ))
        _rely += 1
        self._my_widgets.append(TitleOneDecimalSlider(
            self.parent,
            rely=_rely,
            relx=_relx,
            max_width=width - 4,
            name='LPS 2m',
            out_of=self._slider_max,
            value=self._2m_value,
            editable=False
        ))
        _rely += 1
        self._my_widgets.append(TitleOneDecimalSlider(
            self.parent,
            rely=_rely,
            relx=_relx,
            max_width=width - 4,
            name='LPS Lifetime',
            out_of=self._slider_max,
            value=self._lifetime_value,
            editable=False
        ))
        _rely += 1

        self.entry_widget = weakref.proxy(self._my_widgets[0])


class Dashboard(npyscreen.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stats = kwargs.get('stats', {})
        self._alert_q = kwargs.get('alert_q', None)

    def create(self):
        self.keypress_timeout = 10

        # press Escape to quit
        self.how_exited_handers[npyscreen.wgwidget.EXITED_ESCAPE] = self.exit_application

        height, width = self.useable_space()

        self._time_text = self.add(
            npyscreen.TitleFixedText, name='Time', value='0', editable=False)

        self._lps_box = self.add(
            TrafficBox, name='Traffic', max_height=10, max_width=width / 2, editable=False)
        self._lps_box.set_values(val_10s=0, val_2m=0, val_lifetime=0)

        available_height = height - 4 - self._time_text.height - \
            self._lps_box.height
        self._section_hit_list = self.add(
            npyscreen.TitlePager, name="Popular Sections", editable=False, max_height=int(available_height/2))

        self._alert_list = self.add(
            npyscreen.TitleBufferPager, name="Alerts", editable=False, max_height=int(available_height/2))

    def afterEditing(self):
        self.parentApp.NEXT_ACTIVE_FORM = None

    def while_waiting(self):
        self._lps_box.set_values(
            val_10s=self._stats.get('lps_frame', 0),
            val_2m=self._stats.get('lps_scene', 0),
            val_lifetime=self._stats.get('lps_lifetime', 0)
        )
        self._lps_box.display()

        self._time_text.value = time.asctime()
        self._time_text.display()

        heatmap = self._stats.get('heat_map_frame', {})
        top_sections = Counter(heatmap).most_common()
        top_sections_hits_str = [
            '{} {}'.format(x[0], x[1]) for x in top_sections
        ]
        self._section_hit_list.values = top_sections_hits_str
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
        self.addForm('MAIN', Dashboard, name='HTTP Log Monitor',
                     stats=self._stats_dict, alert_q=self._alert_q)

    def signal_exit(self):
        self._running.value = 0

    def onCleanExit(self):
        self.signal_exit()


if __name__ == '__main__':
    stats = {
        'lps_frame': 1.5,
    }
    ui = MonitorUI(stats)
    ui.run()
