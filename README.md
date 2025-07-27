# neo2-networktester
Python3 and Bash scripts to use the ARM Neo2 as a network tester


For now add to the `/etc/rc.local`

```
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.
cd /usr/local/bin
nice -n 10 /usr/bin/python3 oled-start.py &

exit 0
```
