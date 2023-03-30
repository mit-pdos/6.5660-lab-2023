## ACME specification: https://www.rfc-editor.org/rfc/rfc8555.html

import datetime
import flask
import os
import base64
import json
import requests
import cryptography
import util
import authlib.jose

class ACME:
    def __init__(self, ca):
        self.ca = ca
        self.orders = {}
        self.accounts = {}
        self.nonces = set()
        self.debug = False

    def flask_init(self, app):
        app.add_url_rule("/ca.crt", "ca.crt", self.root_cert, methods=['GET'])
        app.add_url_rule("/directory", "directory", self.directory, methods=['GET'])
        app.add_url_rule("/nonce", "nonce", self.nonce, methods=['GET', 'HEAD'])
        app.add_url_rule("/account", "new_account", self.new_account, methods=['POST'])
        app.add_url_rule("/account/<account_id>", "account", self.account, methods=['POST'])
        app.add_url_rule("/account/<account_id>/orders", "account_orders", self.account_orders, methods=['POST'])
        app.add_url_rule("/order", "new_order", self.new_order, methods=['POST'])
        app.add_url_rule("/order/<order_id>", "order", self.order, methods=['POST'])
        app.add_url_rule("/order/<order_id>/authorize", "authorize", self.authorize, methods=['POST'])
        app.add_url_rule("/order/<order_id>/challenge", "challenge", self.challenge, methods=['POST'])
        app.add_url_rule("/order/<order_id>/finalize", "finalize", self.finalize, methods=['POST'])
        app.add_url_rule("/order/<order_id>/cert", "cert", self.cert, methods=['POST'])

    def directory(self):
        return {
            'newNonce': self.url('nonce'),
            'newAccount': self.url('account'),
            'newOrder': self.url('order'),
        }

    def add_nonce(self, resp):
        n = base64.urlsafe_b64encode(os.urandom(18)).decode('ascii')
        self.nonces.add(n)
        resp.headers['Replay-Nonce'] = n

    def nonce(self):
        resp = flask.Response('')
        self.add_nonce(resp)
        return (resp, 204)

    def kid_to_account_id(self, kid):
        prefix = self.url('account/')
        if kid.startswith(prefix):
            return kid[len(prefix):]
        return None

    def jws(self, require_account_id = None):
        def get_public_key(header, payload):
            if 'jwk' in header and 'kid' in header:
                flask.abort(flask.make_response('both jwk and kid present', 400))
            if 'jwk' in header:
                return header['jwk']
            if 'kid' in header:
                account_id = self.kid_to_account_id(header['kid'])
                if account_id is not None:
                    return self.accounts[account_id]['pubkey']
            flask.abort(flask.make_response('cannot validate jws signature', 400))

        req = flask.request.get_json()
        jws = authlib.jose.JsonWebSignature()
        data = jws.deserialize(req, get_public_key)

        if data['header']['url'] != flask.request.base_url:
            flask.abort('wrong URL in JWS header', 401)
        if data['header']['nonce'] not in self.nonces:
            flask.abort(flask.make_response('urn:ietf:params:acme:error:badNonce', 400))
        self.nonces.remove(data['header']['nonce'])

        if require_account_id is not None and data['header']['kid'] != self.url('account/' + require_account_id):
            flask.abort(flask.make_response('signed with wrong kid', 401))

        if self.debug:
            print(data)
        return data

    def new_account(self):
        req = self.jws()

        account_id = base64.b32encode(os.urandom(20)).decode('ascii')
        account_url = self.url('account/' + account_id)
        acct = {
            'orders_url': account_url + '/orders',
            'orders': [],
            'pubkey': req['header']['jwk'],
        }
        self.accounts[account_id] = acct

        resp = flask.jsonify(self.account_status(acct))
        resp.headers['Location'] = account_url
        self.add_nonce(resp)
        return resp

    def account(self, account_id):
        req = self.jws(account_id)
        acct = self.accounts[account_id]
        resp = flask.jsonify(self.account_status(acct))
        self.add_nonce(resp)
        return resp

    def account_status(self, acct):
        return {
            'status': 'valid',
            'orders': acct['orders_url'],
        }

    def account_orders(self, account_id):
        req = self.jws(account_id)
        acct = self.accounts[account_id]

        order_urls = [self.url('order/' + order_id) for order_id in acct['orders']]
        resp = flask.jsonify({
            'orders': order_urls,
        })
        self.add_nonce(resp)
        return resp

    def new_order(self):
        req = self.jws()
        payload = json.loads(req['payload'])

        if len(payload['identifiers']) != 1:
            return ('Unsupported multiple identifiers', 500)
        id = payload['identifiers'][0]
        if id['type'] != 'dns':
            return ('Unsupported identifier type; only DNS supported', 500)

        order_id = base64.b32encode(os.urandom(20)).decode('ascii')
        order_url = self.url('order/' + order_id)
        now = datetime.datetime.today()

        order = {
            'status': 'pending',
            'dns_name': id['value'],
            'notBefore': now - datetime.timedelta(1),
            'notAfter': now + datetime.timedelta(365),
            'finalize': order_url + '/finalize',
            'authorize': order_url + '/authorize',
            'challenge': order_url + '/challenge',
            'certificate': order_url + '/cert',
            'token': base64.b32encode(os.urandom(20)).decode('ascii'),
            'account': self.kid_to_account_id(req['header']['kid']),
        }
        self.orders[order_id] = order

        acct = self.accounts[order['account']]
        acct['orders'].append(order_id)

        resp = flask.jsonify(self.order_status(order))
        resp.headers['Location'] = order_url
        self.add_nonce(resp)
        return (resp, 201)

    def order_status(self, order):
        stat = {
            'status': order['status'],
            'notBefore': order['notBefore'].isoformat(),
            'notAfter': order['notAfter'].isoformat(),
            'identifiers': [
                {
                    'type': 'dns',
                    'value': order['dns_name'],
                },
            ],
            'finalize': order['finalize'],
            'authorizations': [
                order['authorize'],
            ],
        }
        if 'cert' in order:
            stat['certificate'] = order['certificate']
        return stat

    def order(self, order_id):
        order = self.orders[order_id]
        req = self.jws(order['account'])

        resp = flask.jsonify(self.order_status(order))
        self.add_nonce(resp)
        return resp

    def authorize(self, order_id):
        order = self.orders[order_id]
        req = self.jws(order['account'])

        resp = flask.jsonify({
            'status': order['status'],
            'identifier': {
                'type': 'dns',
                'value': order['dns_name'],
            },
            'challenges': [
                {
                    'type': 'http-01',
                    'url': order['challenge'],
                    'token': order['token'],
                },
            ],
        })
        self.add_nonce(resp)
        return resp

    def challenge(self, order_id):
        order = self.orders[order_id]
        req = self.jws(order['account'])

        acct_key = self.accounts[order['account']]['pubkey']
        jwk = authlib.jose.JsonWebKey.import_key(acct_key)
        expected = order['token'] + "." + jwk.thumbprint()

        hostname = order['dns_name']
        token = order['token']
        port = 80
        if hostname == 'zoobar-localhost.csail.mit.edu':
            port = 8080

        r = requests.get('http://{}:{}/.well-known/acme-challenge/{}'.format(hostname, port, token))
        if r.text == expected:
            order['status'] = 'valid'

        resp = flask.jsonify({
            'status': order['status'],
            'identifier': {
                'type': 'dns',
                'value': order['dns_name'],
            },
        })
        self.add_nonce(resp)
        return resp

    def finalize(self, order_id):
        order = self.orders[order_id]
        req = self.jws(order['account'])
        payload = json.loads(req['payload'])

        if order['status'] != 'valid':
            return ('Order not validated yet', 401)

        csr = payload['csr']
        csr = base64.urlsafe_b64decode(csr + "==")
        csr = cryptography.x509.load_der_x509_csr(csr)

        cn = csr.subject.get_attributes_for_oid(cryptography.x509.oid.NameOID.COMMON_NAME)
        if cn[0].value != order['dns_name']:
            return ('CSR subject %s does not match validated name %s' % (cn[0].name, order['dns_name']), 401)

        order['cert'] = self.ca.issue_cert(order['dns_name'], csr.public_key(),
                                           order['notBefore'], order['notAfter'])
        resp = flask.jsonify(self.order_status(order))
        self.add_nonce(resp)
        return resp

    def cert(self, order_id):
        order = self.orders[order_id]
        req = self.jws(order['account'])

        cert_data = util.cert_to_bytes(order['cert'])
        resp = flask.Response(
            util.cert_to_bytes(order['cert']),
            mimetype = 'application/pem-certificate-chain',
        )
        self.add_nonce(resp)
        return resp

    def root_cert(self):
        return flask.Response(
            util.cert_to_bytes(self.ca.root_cert(datetime.timedelta(365))),
            mimetype = 'application/x-x509-ca-cert',
        )

    def url(self, suffix):
        base = 'http://{}'.format(flask.request.headers['Host'])
        return base + '/' + suffix
