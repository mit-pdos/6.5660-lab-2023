#!/usr/bin/python3

acme_dir_url = 'http://zoobar-ca.csail.mit.edu:5000/directory'
zoobar_hostname = 'zoobar-localhost.csail.mit.edu'
key_pn = 'tls.key'
cert_pn = 'tls.cert'

## Your job is to set up a TLS key and certificate for your Zoobar web server.
## The TLS key goes into key_pn, and the certificate goes into cert_pn.
## Use the ACME CA server at acme_dir_url to get a certificate for the
## server name specified in zoobar_hostname.

## The "zoobar-localhost.csail.mit.edu" name is treated specially by our CA:
## it uses port 8080 to send the challenge, instead of port 80.

pass
