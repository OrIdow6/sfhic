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
		print(dat)
		if not dat:
			break
		h.update(dat)
	sock.close()
	return h.hexdigest()

# Actual if rudimentary HTTP client
# Requests having problems due to connection close/open stuff

def get_resp_body(request):
	sock = socket.create_connection((host, port))
	sock.sendall(request)
	sock.shutdown(socket.SHUT_WR)
	recieved = b""
	while True:
		dat = sock.recv(1024)
		if not dat:
			break
		recieved += dat
	sock.close()
	body = recieved.split(b"\r\n\r\n", 1)[1]
	return body


outline_req = b'GET /outline HTTP/1.1\r\nHost: 127.0.0.1:8888\r\nUser-Agent: Content integrity checker\r\nAccept:*/*\r\n\r\n' # TODO change host
j = json.loads(gzip.decompress(get_resp_body(outline_req)))

for item in j:
	req_body = base64.b64decode(item["request"])
	expected_hash = item["resp_hash"]
	assert get_hash_of_resp(req_body) == expected_hash
