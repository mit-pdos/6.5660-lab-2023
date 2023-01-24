#!/bin/bash

if [ $# -eq 0 ]; then
	echo "Usage: $0 BIN PORT"
	echo "clean-env runs the given server binary BIN using the configuration CONFIG in"
	echo "a pristine environment to ensure predictable memory layout between executions."
	exit 0
fi

killall -qw zookld zookd zookfs zookd-nxstack zookfs-nxstack zookd-exstack zookfs-exstack

ulimit -s unlimited

DIR=$(pwd -P)
if [ "$DIR" != /home/student/lab ]; then
    echo "========================================================"
    echo "WARNING: Lab directory is $DIR"
    echo "Make sure your lab is checked out at /home/student/lab or"
    echo "your solutions may not work when grading."
    echo "========================================================"
fi
# setarch -R disables ASLR

exec env - PWD="$DIR" SHLVL=0 setarch "$(uname -m)" -R "$@"

ERR=$?
echo Failed: exec env - PWD="$DIR" SHLVL=0 setarch "$(uname -m)" -R "$@"
exit $ERR
