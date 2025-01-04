# eco-worthy-battery-logger
Log voltage, current, state of charge, temperature, etc. for Eco-worthy LiFePo4 batteries

This is a program to display and log battery parameters on Eco-worthy
Bluetooth LiFePo4 batteries. It was developed on the ECO-LFP1215003 model.
The program requires Python 3 and bluepy.

Usage: python ewbatlog.py -m mac-address [-i interval] [-l logfile] [-a pct] [-b pct] [-v]
Mac address format: a5:c2:37:01:2f:ed
Interval is in seconds, logfile is for csv output, -v to get cell voltages
-a pct exits with code 2 if above SOC percentage
-b pct exits with code 3 if below SOC percentage

I would be interested in hearing results from users of other Eco-worthy
batteries. If it works, please let me know. If not, please send me the
output text.

Eco-worthy https://www.eco-worthy.com/ makes various alternative energy
products including LiFePo4 batteries. Some of those batteries have a
Bluetooth interface to their BMS, allowing a smartphone app to display the
voltage, current, and state of charge of the battery. Any such battery will
have a Bluetooth symbol, and a sticker with its MAC address. The MAC address
looks similar to this: a5:c2:37:12:34:ab

The phone app can only show the current state of the battery to someone
within Bluetooth radio range. I wanted to be able to log time series, and
view status remotely. I put their app on my developer phone, enabled HCI
Bluetooth snoop log in developer options, ran the app, and connected to my
batteries. Then I ran "adb bugreport" on the laptop, and loaded the
Bluetooth log into Wireshark. The protocol is pretty simple: you send one of
two requests to the battery. One of those replies with the volts, amps, and
state of charge. The other shows the individual cell voltages. The data is
in 16-bit big endian twos complement binary.

I later found a YouTube that identified the BMS as being made by this
company: https://jiabaida-bms.com/pages/download-files
There is a PDF with some more technical information at that site.
Look for: JDB RS485-RS232-UART-Bluetooth-Communication Protocol

This program will connect to one battery and output the measurements to a
CSV file at a defined interval. The file is opened and appended with each
update, so you can access the data so far while the program is running. You
can run multiple instances to log several batteries at once. It has been
tested on a Raspberry Pi and a Lenovo laptop with Ubuntu 22.04.

The program can also exit with an error code when the state of charge either
goes above or below a chosen value. This could be used to turn off a charger
at a chosen percentage, or to send an alert when the battery is getting low.

The battery can only accept one connection at a time. The phone app will
not work while this program is attached, and vice versa. You have to
swipe-out the app to make sure it is closed, otherwise it will stay
connected for a while.
