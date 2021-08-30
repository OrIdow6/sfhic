#!/usr/bin/python3

import asyncio

from pathlib import Path

import hashlib
import base64
import json
import gzip

from functools import cache


# New version, largely based on feedback from Rewby
# New new version, changed to asyncio per suggestion from JAA


def replace_templates(data):
	# Simple templates in the data.
	# Meant for the Host header, etc.
	# Not a good way to manage this, but whatever.
	mapping = {b"460cc7e83624a591e6c50f3a54d5936a0f95ad3c112ec729dbced74873cd": b"127.0.0.1:8888"} # TODO need a config file or something
	for m, r in mapping.items():
		data = data.replace(m, r)
	
	return data


def make_pairs(req_dir=Path("requests"), resp_dir=Path("responses")):
	
	def dir_to_dict(path):
		out = {}
		for file in filter(lambda f: f.is_file() and not f.name.startswith("_"), path.iterdir()):
			with file.open("rb") as f:
				out[file.name] = replace_templates(f.read())
		return out
	
	requests = dir_to_dict(req_dir) # name -> content
	responses = dir_to_dict(resp_dir) # name -> content
	
	
	if (diff := requests.keys() - responses.keys()) > set():
		raise Exception("Exist in requests but not responses:", diff)
	
	if (diff := responses.keys() - requests.keys()) > set():
		raise Exception("Exist in responses but not requests:", diff)
	
	to_ret = {}
	names = {}
	for name in requests.keys():
		to_ret[requests[name]] = responses[name]
		names[requests[name]] = name
	
	return to_ret, names


req_resp_pairs, request_names = make_pairs() # Dict from binary request content to binary response content; dict from binary request content to filename


# Take a dict of req/resp pairs, and of req->filename, and generate the encoding of a req -> hash(resp) that can be sent to a client, ordered by filename.
@cache
def make_expectation_bundle(pairs=req_resp_pairs, names=request_names):
	overall = []
	for req, resp in sorted(pairs.items(), key=lambda p: names[p[0]]):
		overall.append({"request": base64.b64encode(req).decode("utf-8"),
				  "resp_hash": hashlib.sha1(resp).hexdigest()})
	return gzip.compress(json.dumps(overall).encode("utf-8"))


print("Num pairs is", len(req_resp_pairs))


def makeHttpResponse(body, content_type="text/plain", status_code=200, status_message="OK"):
	if isinstance(body, str):
		body = body.encode("utf-8")
	return "HTTP/1.1 {} {}\r\nContent-Type: {}; charset=utf-8\r\nContent-Length: {}\r\n\r\n".format(
		status_code, status_message, content_type, len(body)).encode("utf-8") + body



class ResponderProtocol(asyncio.Protocol):
	def connection_made(self, transport):
		self.transport = transport
		self.buf = b""
	
	def data_received(self, data):
		if len(data) + len(self.buf) < 10000:
			self.buf += data
		else:
			self.transport.write(makeHttpResponse("Too much header data - make sure you are using a CRLFCRLF",
				status_code=431, status_message="Request Header Fields Too Large"))
		
		if b"\r\n\r\n" in self.buf:
			self.send_response(self.buf.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n")
		
		if b"\n\n" in self.buf:
			self.send_response(self.buf.split(b"\n\n", 1)[0] + b"\n\n")
	
	def eof_received(self):
		self.send_response(self.buf)
	
	# Sends a response based on the assumption that the client has sent the data given.
	# This does not use self.buf.
	def send_response(self, data):
		# First try matching against a known req/resp pair
		if data in req_resp_pairs:
				self.transport.write(req_resp_pairs[data])
		else:
			try:
				[method, path, *_] = data.decode("utf-8").split(None, 2)
			except (UnicodeDecodeError, ValueError):
				method, path = None, None
			
			if (method, path) == ("GET", "/echohash"):
				digest = hashlib.sha1(data).hexdigest()
				assert len(digest) == 40
				self.transport.write(makeHttpResponse(digest.encode("utf-8")))
			elif (method, path) == ("GET", "/outline"):
				self.transport.write(makeHttpResponse(make_expectation_bundle(), "application/gzip"))
			else:
				self.transport.write(makeHttpResponse("No appropriate response was found for your request.", status_code=404, status_message="Not found"))
		self.transport.close()

# Stolen from JAA
loop = asyncio.get_event_loop()
coro = loop.create_server(ResponderProtocol, '127.0.0.1', 8888)
server = loop.run_until_complete(coro)
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
	loop.run_forever()
except KeyboardInterrupt:
	pass
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
