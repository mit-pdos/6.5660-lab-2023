#!/bin/bash

HOST=localhost
PORT=8080
STRACELOG=/tmp/strace.log
need_cleanup=1

cleanup() {
  if [ "$need_cleanup" = 1 ]; then
    killall -qw zookld zookd zookfs zookd-nxstack zookfs-nxstack zookd-exstack zookfs-exstack
    need_cleanup=0
  fi
}

PASS="\033[1;32mPASS\033[m"
FAIL="\033[1;31mFAIL\033[m"

cleanup
trap cleanup EXIT

touch /tmp/zook-start-wait

# launch the server. strace so we can see SEGVs.
strace -f -e none -o "$STRACELOG" ./clean-env.sh ./$1 8080 &
STRACEPID=$!
need_cleanup=1

# wait until we can connect
inotifywait -qqe delete_self -t 20 /tmp/zook-start-wait 2>/dev/null
if ! curl --connect-timeout 30 -s $HOST:$PORT &>/dev/null ; then
  echo "failed to connect to $HOST:$PORT"
  exit 1
fi

# run the attack script.
$2 $HOST $PORT >/dev/null &
ATTACKPID=$!

# wait for the server to crash.
tail --pid=$STRACEPID -f -n +0 "$STRACELOG" | grep -q SIGSEGV &
GREPPID=$!

# give it 20 seconds to crash.
( sleep 20; kill -9 $STRACEPID 2>/dev/null ) &

# see whether we got a crash.
wait $GREPPID 2>/dev/null
OK=$?

kill $ATTACKPID 2>/dev/null
cleanup

if [ $OK = 0 ]; then
  echo -e "$PASS $2"
else
  echo -e "$FAIL $2"
fi
