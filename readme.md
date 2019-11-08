HTTP Log Monitor
================

This program monitors multiple HTTP access log files and show the following information in its text-based user interface:
- Traffic in Log Per Second (LPS), over time window of 3 lengths
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
