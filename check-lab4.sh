#!/bin/bash

HOST=localhost
PORT=8080

need_cleanup=1

cleanup() {
    sudo killall -w zookld zookd zookfs zookd-nxstack zookfs-nxstack zookd-exstack zookfs-exstack auth-server.py echo-server.py bank-server.py &> /dev/null
}

setup_server() {
    cleanup
    make &> /dev/null
    sudo rm -rf zoobar/db &> /dev/null
    ( ./zookd 8080 & ) &> /tmp/zookd.out

    i=0
    while ! curl --connect-timeout 1 -s $HOST:$PORT &>/dev/null; do
        ((i=i+1))
        if ((i>5)); then
            echo "failed to connect to $HOST:$PORT"
            exit 1
        fi
        sleep .1
    done
}

# colors from http://stackoverflow.com/questions/4332478/read-the-current-text-color-in-a-xterm/4332530#4332530
NORMAL=$(tput sgr0)
RED=$(tput setaf 1)
FAIL="[ ${RED}FAIL${NORMAL} ]"
OHNO="[ ${RED}OHNO${NORMAL} ]"
GREEN=$(tput setaf 2)
PASS="[ ${GREEN}PASS${NORMAL} ]"
BLUE=$(tput setaf 4)
INFO="[ ${BLUE}INFO${NORMAL} ]"
YELLOW=$(tput setaf 3)
DOTS="[ ${YELLOW}....${NORMAL} ]"

run_test() {
    printf "${INFO}: Testing exploit for $1...\n"
    setup_server
    node $2 .
}

cleanup
trap cleanup EXIT

## if this is the first time we're using puppeteer..
npm install node-fetch
npm link puppeteer

echo "Generating reference images..."
setup_server
node lab4-tests/make-reference-images.mjs

### Part 1 ###
run_test "Exercise 1" lab4-tests/grade-ex01.mjs
run_test "Exercise 2" lab4-tests/grade-ex02.mjs
run_test "Exercise 3" lab4-tests/grade-ex03.mjs
run_test "Exercise 4" lab4-tests/grade-ex04.mjs
run_test "Exercise 5" lab4-tests/grade-ex05.mjs

### Part 2 ###
run_test "Exercise 6" lab4-tests/grade-ex06.mjs
run_test "Exercise 7" lab4-tests/grade-ex07.mjs
run_test "Exercise 8" lab4-tests/grade-ex08.mjs
run_test "Exercise 9" lab4-tests/grade-ex09.mjs

### Challenge ###
run_test "Challenge" lab4-tests/grade-chal.mjs

### Part 3 ###
run_test "Exercise 10" lab4-tests/grade-ex10.mjs

