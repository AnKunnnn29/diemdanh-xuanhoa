"""Opaque server sessions; password format remains compatible with existing users."""
import base64
import hashlib
import hmac
import secrets


class CloudError(Exception):
    def __init__(self, message, status=409, code='invalid_request'):
        self.status, self.code = status, code
        super().__init__(message)


def audit_details(value):
    """Passwords and authentication material never belong in an audit view."""
    private = {'password','passwordhash','temporarypassword','newpassword','currentpassword',
               'token','csrftoken','secret','databaseurl','xhdatabaseurl'}
    if isinstance(value,dict):
        return {key:audit_details(item) for key,item in value.items()
                if str(key).replace('_','').casefold() not in private}
    if isinstance(value,list):
        return [audit_details(item) for item in value]
    return value


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**17, r=8, p=1,
                            maxmem=256*1024*1024, dklen=32)
    return 'scrypt$'+base64.b64encode(salt).decode()+'$'+base64.b64encode(digest).decode()


def password_matches(password, encoded):
    try:
        algorithm, salt, expected = encoded.split('$')
        if algorithm != 'scrypt' or not isinstance(password, str):
            return False
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt, validate=True),
                                n=2**17, r=8, p=1, maxmem=256*1024*1024, dklen=32)
        return hmac.compare_digest(actual, base64.b64decode(expected, validate=True))
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(str(token or '').encode()).hexdigest()


def validate_password(value):
    if not isinstance(value, str) or not 10 <= len(value) <= 128:
        raise CloudError('Mật khẩu mới cần từ 10 đến 128 ký tự.')
    return value
