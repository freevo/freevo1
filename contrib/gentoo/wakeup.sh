#!/bin/sh

source /etc/conf.d/clock

if [[ ${CLOCK} == "UTC" ]] ; then
    hwopts="--utc"
    offset=`date +%z`
else
    hwopts="--localtime"
    offset="+0000"
fi

wakedate=`date -u -d "$1 ${offset}" "+%F %H:%M:%S"`
wakesecs=`date -d "$1 ${offset}" +%s`

#uncomment this line if you MB resets alarms
#when hardware clock is updated on shutdown
#and you had to disable it in /etc/conf.d/clock
#hwclock --systohc ${hwopts} >& /dev/null

if [ -e /sys/class/rtc/rtc0/wakealarm ]; then
    echo 0 > /sys/class/rtc/rtc0/wakealarm
    echo ${wakesecs} > /sys/class/rtc/rtc0/wakealarm
fi
if [ -e /proc/acpi/alarm ]; then
    echo ${wakedate} > /proc/acpi/alarm
fi
