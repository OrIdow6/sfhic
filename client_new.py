import hashlib
import socket
import requests
import json
import base64
import gzip

host = "127.0.0.1"
port = 8888

def get_hash_of_resp(request):
	sock = socket.create_connection((host, port))
	sock.sendall(request)
	sock.shutdown(socket.SHUT_WR)
	h = hashlib.sha1()
	while True:
		dat = sock.recv(1024)
		if not dat:
			break
		h.update(dat)
	sock.close()
	return h.hexdigest()

j = json.loads(gzip.decompress(requests.get(f"http://{host}:{port}/outline").content))

for item in j:
	req_body = base64.b64decode(item["request"])
	expected_hash = item["resp_hash"]
	assert get_hash_of_resp(req_body) == expected_hash
