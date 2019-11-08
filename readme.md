HTTP Log Monitor
================

This program monitors multiple HTTP access log files and show the following information in its text-based user interface:
- Traffic in Logs Per Second (LPS), over a time window of 3 lengths
  - 10 seconds
  - 2 minutes
  - its lifetime, since the application start
- Status
  - Clock shows the time now
  - Alert ON/OFF indicator. It turns on when the traffic for the past 2 minutes exceeds a certain number (10 by default) on lifetime average. It will return to OFF when the traffic drops with a certain threshold
- Popular Sections, listing section according to how many accesses it received during the last 10 seconds, in descending order
- Top Consumer Hosts, listing the hosts getting the most bytes of data in the responses
- List of most recent alert events: when alert has been triggered because of high traffic, when the alert went off as traffic drops back to normal.

![UI small 1](/images/screenshot_1.png)


How to Use
==========

Install
-------
The code depends on [npyscreen](https://npyscreen.readthedocs.io/) module to run. We need to install npyscreen by ``pip install npyscreen`` or using the requirement.txt ``pip install -r requirements.txt``
npyscreen requires ncurses library. This program has to execute on Linux/OS X/Windows with Linux Subsystem.


monitor.py
----------
Following HTTP access log files, it shows statistics and raise alert when traffic increases too fast.

```
monitor.py [-h] -s access_1.log [-s access_2.log] [-l 10]
    -s --source     HTTP access log,
                    multiple log files can be passed by adding "-s log1 -s log2"
    -t --threshold  Threshold in Access Per Second to trigger alarm when 2 minute
                    average is above the lifetime average of this threshold. Default is 10.
```
Once the monitor is running, a TUI will pop up presenting statistics on access log in 5 boxes:
- Traffic: LPS in 3 time-windows: 10s, 2m, lifetime, refreshed every 10 seconds.
- Status: Current Time and Alert Status. Alerts are shown in different colors for ON and OFF.
- Popular Sections: List of sections most accessed during the past 10 seconds
- Top Bandwidth Consumers: List of remotehosts requested the most bytes of data during the past 10 seconds.
- Alerts: List of most recent alerts, if average traffic over 2 minutes is high above the life time average exceeding the threshold, the alerts will continue pop up in this list. When traffic return under the threshold, only one alert off message will show. The list is rolling up in the same way "tail -f" does.


Swtich box: Use tab and alt-tab to switch from one box to another.
Browsing list: Use up and down arrow keys to browse a list (Popular Sections, Top Bandwidth Consumers)
Quit monitor: switch to OK button at the bottom and press enter, or press Esc key at any moment.

Statistics starts to show from the 10th second. It is normal there is no information shown just after launching the monitor.

![UI big 5](/images/screenshot_big_5.png)

traffic_generator.py
--------------------
This traffic generator will append to access log file either random generated line or copying line by line from existing access log file, with a speed regulator.

```
traffic_generator.py [-s access_src.log] -d access_dest.log -l 10
Write logs from source to destination file with a rate
    -s source file       if specified, copy line by line from this file and append it to the destination file
    -d destination file  generated logs are appended to this file
    -l lines per second  number of lines output each second
```


Design
======

Architecture
------------
The monitor is a multiprocess application, exchanging information through queues and shared memory.
There are 3 type of processes:
1. File Wather
2. Analyzer
3. User Inerface

The File Watchers read new line from monitored files, parse the log line and put the extracted information as log items into a message queue dedicated to log influx.

The Analyzer consume log items and update the memory segment shared with User Interface. When Analyzer finds out the 2 minutes average LPS is higher than the lifetime average LPS plus a threshold, the Analyzer send an alert item into the alert message queue. Which will be consumed by the User Interface.

The User Interface present a text based UI in the console, periodically update the widgets with statistics information in the shared memory. If there is message in the alert queue, update the alert status and shows alert messages in the UI.

Data Structure
--------------




Evolution
=========
