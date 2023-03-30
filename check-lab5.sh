#!/bin/bash

cleanup() {
    rm -rf tls.key tls.cert
    sudo killall -w zookd run.py https-proxy.py &> /dev/null
}

wait_for_http() {
    i=0
    while ! curl --connect-timeout 1 -s $1 &>/dev/null; do
        ((i=i+1))
        if ((i>5)); then
            echo "failed to connect to $1"
            exit 1
        fi
        sleep 1
    done
}

setup_server() {
    cleanup
    make &> /dev/null
    sudo rm -rf zoobar/db &> /dev/null
    ( ./zookd 8080 & ) &> /tmp/zookd.out
    ( ./ca/run.py & ) &> /tmp/ca.out
    ( ./https-proxy.py & ) &> /tmp/https-proxy.out

    wait_for_http localhost:8080
    wait_for_http localhost:5000
}

cleanup
trap cleanup EXIT
setup_server

npm install node-fetch
npm link puppeteer

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

printf "${INFO}: Testing exercise 1: ACME client\n"

./acme-client.py

## Wait a bit for ghostunnel to restart with the new cert
sleep 1

rm -f /tmp/ca.crt /tmp/zoobar-wget.out
wget -q http://localhost:5000/ca.crt -O /tmp/ca.crt
wget --ca-certificate=/tmp/ca.crt --no-http-keep-alive https://zoobar-localhost.csail.mit.edu:8443/zoobar/index.cgi -O /tmp/zoobar-wget.out

if grep -q 'Zoobar Foundation' /tmp/zoobar-wget.out; then
    printf "${PASS}: Exercise 1: HTTPS works\n"
else
    printf "${FAIL}: Exercise 1: HTTPS does not work\n"
    exit
fi

printf "${INFO}: Testing exercise 2: WebAuthn\n"

## Install the root CA certificate.
PHOME=/tmp/puppeteer-home
NSSDB=$PHOME/.pki/nssdb
rm -rf $PHOME
mkdir -p $NSSDB
certutil -d sql:$NSSDB -N --empty-password
certutil -d sql:$NSSDB -A -t "CP,," -n "6.5660 CA" -i /tmp/ca.crt
ln -s $HOME/.cache $PHOME/.cache

HOME=$PHOME node lab5-tests/grade-webauthn.mjs
