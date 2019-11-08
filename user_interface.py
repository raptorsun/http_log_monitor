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
        self._slider_10s.entry_widget.out_of = self._slider_max
        self._slider_2m.entry_widget.out_of = self._slider_max
        self._slider_lifetime.entry_widget.out_of = self._slider_max

        self._slider_10s.value = self._10s_value
        self._slider_2m.value = self._2m_value
        self._slider_lifetime.value = self._lifetime_value

    def make_contained_widget(self, contained_widget_arguments=None):
        self._my_widgets = []
        _rely = self.rely+1
        _relx = self.relx+2
        width = self.width

        self._slider_max = 10
        self._10s_value = 0
        self._2m_value = 0
        self._lifetime_value = 0
        self._slider_10s = TitleOneDecimalSlider(
            self.parent,
            rely=_rely,
            relx=_relx,
            max_width=width - 4,
            name='LPS 10s',
            out_of=self._slider_max,
            value=self._10s_value,
            editable=False
        )
        self._my_widgets.append(self._slider_10s)
        _rely += 1
        self._slider_2m = TitleOneDecimalSlider(
            self.parent,
            rely=_rely,
            relx=_relx,
            max_width=width - 4,
            name='LPS 2m',
            out_of=self._slider_max,
            value=self._2m_value,
            editable=False
        )
        self._my_widgets.append(self._slider_2m)
        _rely += 1
        self._slider_lifetime = TitleOneDecimalSlider(
            self.parent,
            rely=_rely,
            relx=_relx,
            max_width=width - 4,
            name='LPS Lifetime',
            out_of=self._slider_max,
            value=self._lifetime_value,
            editable=False
        )
        self._my_widgets.append(self._slider_lifetime)
        _rely += 1

        self.entry_widget = weakref.proxy(self._my_widgets[0])


class StatusBox(npyscreen.BoxTitle):
    def set_values(self, timestr, alert_on=None, alert_msg=None):
        self._time_text.value = timestr
        if not alert_on is None:
            self._alert_on = alert_on
            self._alert_msg = alert_msg
            self._alert_on_text.value = 'ON' if self._alert_on else 'OFF'
            self._alert_on_text.entry_widget.color = 'WARNING' if self._alert_on else 'SAFE'

    def make_contained_widget(self, contained_widget_arguments=None):
        self._my_widgets = []
        _rely = self.rely+1
        _relx = self.relx+2
        width = self.width
        self._time_text = npyscreen.TitleFixedText(
            self.parent, name='Time', value='0', editable=False, rely=_rely, relx=_relx, max_width=width - 4)
        self._my_widgets.append(self._time_text)
        _rely += 1
        self._alert_on_text = npyscreen.TitleFixedText(
            self.parent, name='Alert', value='OFF', editable=False, rely=_rely, relx=_relx, max_width=width - 4, color='SAFE')
        self._my_widgets.append(self._alert_on_text)
        _rely += 1
        self.entry_widget = weakref.proxy(self._my_widgets[0])


class BufferPagerBox(npyscreen.BoxTitle):
    _contained_widget = npyscreen.BufferPager

    def clearBuffer(self):
        return self.entry_widget.clearBuffer()

    def buffer(self, *args, **values):
        return self.entry_widget.buffer(*args, **values)


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

        height_lps_status_box = 5
        rely = 2
        self._lps_box = self.add(TrafficBox, name='Traffic', editable=False,
                                 relx=2,
                                 rely=rely,
                                 max_width=(width // 2 - 2),
                                 max_height=height_lps_status_box)
        self._lps_box.set_values(val_10s=0, val_2m=0, val_lifetime=0)

        self._status_box = self.add(StatusBox, name="Status", editable=False,
                                    relx=(width // 2 + 1),
                                    rely=rely,
                                    max_width=(width // 2 - 2),
                                    max_height=height_lps_status_box)

        rely += height_lps_status_box + 2
        available_height = height - 4 - height_lps_status_box - 5
        self._section_hit_list = self.add(
            npyscreen.BoxTitle, name="Popular Sections", editable=True, scroll_exit=True,
            relx=2,
            rely=rely,
            max_height=available_height//2,
            max_width=(width // 2 - 2))
        self._hot_host_list = self.add(
            npyscreen.BoxTitle, name="Top Bandwidth Consumer", editable=True, scroll_exit=True,
            relx=(width // 2 + 1),
            rely=rely,
            max_height=available_height//2,
            max_width=(width // 2 - 2))
        rely += available_height//2 + 2
        self._alert_list = self.add(
            BufferPagerBox, name="Alerts", editable=False,
            relx=2,
            max_height=available_height//2,
            color='WARNING')

    def afterEditing(self):
        self.parentApp.NEXT_ACTIVE_FORM = None

    def while_waiting(self):
        self._lps_box.set_values(
            val_10s=self._stats.get('lps_frame', 0),
            val_2m=self._stats.get('lps_scene', 0),
            val_lifetime=self._stats.get('lps_lifetime', 0)
        )
        self._lps_box.display()

        self._status_box.set_values(timestr=time.asctime())
        self._status_box.display()

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
            self._status_box.set_values(
                timestr=time.asctime(), alert_on=alert_on, alert_msg=alert_msg)
            self._status_box.display()

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
