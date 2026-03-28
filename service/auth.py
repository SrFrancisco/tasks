from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from consts import *
import json

auth = HTTPBasicAuth()

file = open(CREDENTIALS_FILE, "r")
data = json.load(file)
users = {}
for user in data:
    users[user['user']] = generate_password_hash(user['password'])
file.close()


@auth.verify_password
def verify_password(username:dict[str,str], password):
    if username in users and \
            check_password_hash(users[username], password):
        return username