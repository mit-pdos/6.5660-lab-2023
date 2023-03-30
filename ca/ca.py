from cryptography import x509
from cryptography.hazmat.primitives import hashes

import datetime

class CA:
    def __init__(self, privkey, ca_name):
        self.privkey = privkey
        self.ca_name = ca_name

    def builder(self, name, pubkey, not_before, not_after):
        b = x509.CertificateBuilder()
        b = b.issuer_name(x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, self.ca_name),
        ]))
        b = b.subject_name(x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, name),
        ]))
        b = b.public_key(pubkey)
        b = b.not_valid_before(not_before)
        b = b.not_valid_after(not_after)
        b = b.serial_number(x509.random_serial_number())
        return b

    def sign_builder(self, b):
        return b.sign(private_key = self.privkey, algorithm = hashes.SHA256())

    def root_cert(self, lifetime):
        now = datetime.datetime.today()
        b = self.builder(self.ca_name, self.privkey.public_key(),
                         now - datetime.timedelta(1), now + lifetime)
        b = b.add_extension(
            x509.BasicConstraints(ca = True, path_length = None),
            critical = True,
        )
        return self.sign_builder(b)

    def issue_cert(self, name, pubkey, not_before, not_after):
        ## To help with grading the WebAuthn exercise, we want to have
        ## another origin that will not match.
        names = [name]
        if name == 'zoobar-localhost.csail.mit.edu':
            names.append('zoobar-localhost-other.csail.mit.edu')

        b = self.builder(name, pubkey, not_before, not_after)
        b = b.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(n) for n in names]),
            critical = False,
        )
        b = b.add_extension(
            x509.BasicConstraints(ca = False, path_length = None),
            critical = True,
        )
        return self.sign_builder(b)
