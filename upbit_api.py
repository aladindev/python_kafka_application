import os
import jwt
import uuid
import hashlib
from urllib.parse import urlencode

import requests

# git Test git merge
# 환경 변수에서 Access Key와 Secret Key를 가져온다.
# Open-WebUi / model gemma 4.8GB / Repository => open-webui => AIVenv 
# with jenkins 03.31 
access_key = os.environ['UPBIT_OPEN_API_ACCESS_KEY']
secret_key = os.environ['UPBIT_OPEN_API_SECRET_KEY']
server_url = os.environ['UPBIT_SERVER_URL']

payload = {
    'access_key': access_key,
    'nonce': str(uuid.uuid4()), 
}

jwt_token = jwt.encode(payload, secret_key)
authorize_token = 'Bearer {}'.format(jwt_token) 
headers = {"Authorization": authorize_token}

res = requests.get(server_url + "/v1/accounts", headers=headers)

print(res.json())

