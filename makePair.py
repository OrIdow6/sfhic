#!/usr/bin/python3

# This program is not meant to have its output passed directly into a client/server (i.e. middlebox), as with csmith or similar;
# rather it is meant to provide a semi-random base response that you can modify in a hex editor.

# I relearn how to use argparse for the 11th time
import argparse

from collections import OrderedDict
import random
from pathlib import Path

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-"

def random_string(length):
	return "".join([random.choice(ALPHABET) for _ in range(length)])

parser = argparse.ArgumentParser(description='Make a normal HTTP response body for you to alter.')

body_group = parser.add_mutually_exclusive_group()
body_group.add_argument('-b', '--exact-body', help="Exact string to use for the response body", action="store")
body_group.add_argument('--load-body', help="File to load as the response body", action="store")
body_group.add_argument('--random-body', help="Use a random string as the body (default)", action="store_true", default=True)

path_group = parser.add_mutually_exclusive_group()
path_group.add_argument('-p', '--exact-path', help="Exact string to use for the path")
path_group.add_argument('--random-path', help="Use a random string as the path (default)", action="store_true", default=True)
parser.add_argument('--no-query', help="Do not add a query to the path (default is to add)" , action="store_false", dest="include_query")

parser.add_argument('-S', '--response-header', action='append', help="Header to add to the response, in the form \"Name: Value\" - warning, whitespace is normalized")
parser.add_argument('-Q', '--request-header', action='append', help="Header to add to the request, in the form \"Name: Value\" - warning, whitespcae is normalized")

parser.add_argument('-d', '--no-default-headers', action='store_false', help="Do not add any extraneous (it still adds e.g. Content-Length) headers to the request and response", dest="add_default_headers")

parser.add_argument('filename', help="Filename for the request/response files")


args = parser.parse_args()

def build_request():
	# First build the request
	req = b''

	if args.exact_path:
		path = args.exact_path
	else:
		assert args.random_path
				
		path = "/" + random_string(random.randint(10, 20))
		# Add on some GET params too
		if args.include_query:
			rand_string_rand_range = lambda: random_string(random.randint(5, 16))
			path += "?" + "&".join((rand_string_rand_range() + "=" + rand_string_rand_range() for _ in range(random.randint(1, 4))))
			
	req += f'GET {path} HTTP/1.1\r\n'.encode("utf-8")

	default_headers = OrderedDict()
	if args.add_default_headers:
		# Default headers, largely taken from the Firefox I'm running
		default_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
		default_headers["Accept-Encoding"] = ", ".join(list(random.sample(["gzip", "deflate", "br"], k=3)))
		default_headers["Accept-Language"] = "en-US,en;q=0.5,de;q=0.3" # How ArchiveTeam operates
		default_headers["Cache-Control"] = "max-age=0"
		default_headers["Connection"] = "keep-alive"
		default_headers["Host"] = "460cc7e83624a591e6c50f3a54d5936a0f95ad3c112ec729dbced74873cd"
		default_headers["Referer"] = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language"
		default_headers["Upgrade-Insecure-Requests"] = "1"
		default_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0"

	if args.request_header:
		for header in args.request_header:
			[k, v] = header.split(":")
			k = k.strip()
			v = v.strip()
			default_headers[k] = v

	req += b"\r\n".join((f"{k}: {v}".encode("utf-8") for k, v in default_headers.items()))
	
	if req.endswith(b"\r\n"):
		# If there were no headers it will already have this
		req += b"\r\n"
	else:
		req += b"\r\n\r\n"
	return req

def build_response():
	resp = b""
	resp += b"HTTP/1.1 "
	
	status_code_and_message = "200 OK" # TODO
	resp += status_code_and_message.encode("utf-8") + b"\r\n"
	
	# Need to load the body first for content-length
	if args.exact_body:
		body = args.exact_body.encode("utf-8")
		binary_body = False
	elif args.load_body:
		with Path(args.load_body).open("rb") as f:
			body = f.read()
		try:
			body.decode("utf-8")
			binary_body = False
		except UnicodeDecodeError:
			binary_body = True
	else:
		assert args.random_body
		if random.random() > 0.5:
			body = random.randbytes(random.randint(10, 120))
			binary_body = True
		else:
			body = random_string(random.randint(10, 200)).encode("utf-8")
			binary_body = False
	
	headers = OrderedDict()
	if args.add_default_headers:
		# Most copied from https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Connection (i.e. the HTTP response I got loading this page)
		headers["Connection"] = "close"
	
	# Insert body stuff
	headers["Content-Length"] = len(body)
	if binary_body:
		headers["Content-Type"] = "application/octet-stream"
	else:
		headers["Content-Type"] = "text/plain; charset=utf-8"
		
	
	if args.response_header:
		for header in args.response_header:
			k, v = header.split(":")
			k = k.strip()
			v = v.strip()
			headers[k] = v
	
	resp += b"\r\n".join((f"{k}: {v}".encode("utf-8") for k, v in headers.items()))
	
	if resp.endswith(b"\r\n"):
		# If there were no headers it will already have this
		resp += b"\r\n"
	else:
		resp += b"\r\n\r\n"
	
	resp += body
	
	return resp

req_dir = Path("requests")
resp_dir = Path("responses")
filename = Path(args.filename)
with req_dir.joinpath(filename).open("wb") as f:
	f.write(build_request())

with resp_dir.joinpath(filename).open("wb") as f:
	f.write(build_response())
