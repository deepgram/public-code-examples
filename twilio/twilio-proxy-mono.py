import asyncio
import websockets
import sys
import json
import base64
import ssl
import time

def deepgram_connect():
	basic_auth = base64.b64encode(b"username:password").decode("ascii")
	headers = { 'Authorization' : 'Basic %s' %  basic_auth}
	deepgram_ws = websockets.connect("wss://brain.deepgram.com/v2/listen/stream?encoding=mulaw&sample_rate=8000&endpointing=true", extra_headers = headers)

	return deepgram_ws

async def proxy(client_ws, path):
	# inbox = asyncio.Queue() # not needed unless sending ws messages back to the client
	outbox = asyncio.Queue()

	print('started proxy')

	# use these for timing
	audio_cursor = 0.
	conn_start = time.time()

	async with deepgram_connect() as deepgram_ws:
		async def deepgram_sender(deepgram_ws):
			print('started deepgram sender')
			while True:
				chunk = await outbox.get()
				await deepgram_ws.send(chunk)
			print('finished deepgram sender')

		async def deepgram_receiver(deepgram_ws):
			print('started deepgram receiver')
			nonlocal audio_cursor
			async for message in deepgram_ws:
				try:
					dg_json = json.loads(message)

					# print the results from deepgram!
					print(dg_json)

					# do this logic for timing
					# NOTE: it only makes sense to measure timing for interim results, see this doc for more details: https://docs.deepgram.com/streaming/tutorials/latency.html
#					try:
#						if dg_json["is_final"] == False:
#							transcript = dg_json["channel"]["alternatives"][0]["transcript"]
#							start = dg_json["start"]
#							duration = dg_json["duration"]
#							latency = audio_cursor - (start + duration)
#							conn_duration = time.time() - conn_start
#							print('latency: ' + str(latency) + '; transcript: ' + transcript)
#					except:
#						print('did not receive a standard streaming result')
#						continue
				except:
					print('was not able to parse deepgram response as json')
					continue
			print('finished deepgram receiver')

		async def client_receiver(client_ws):
			print('started client receiver')
			nonlocal audio_cursor

			# we will use a buffer of 20 messages (20 * 160 bytes, 0.4 seconds) to improve throughput performance
			# NOTE: twilio seems to consistently send media messages of 160 bytes
			BUFFER_SIZE = 20 * 160
			buffer = bytearray(b'')
			empty_byte_received = False
			async for message in client_ws:
				try:
					data = json.loads(message)
					if data["event"] in ("connected", "start"):
						print("Media WS: Received event connected or start")
						continue
					if data["event"] == "media":
						media = data["media"]
						chunk = base64.b64decode(media["payload"])
						time_increment = len(chunk) / 8000.0
						audio_cursor += time_increment
						buffer.extend(chunk)
						if chunk == b'':
							empty_byte_received = True
					if data["event"] == "stop":
						print("Media WS: Received event stop")
						break

					# check if our buffer is ready to send to our outbox (and, thus, then to deepgram)
					if len(buffer) >= BUFFER_SIZE or empty_byte_received:
						outbox.put_nowait(buffer)
						buffer = bytearray(b'')
				except:
					print('message from client not formatted correctly, bailing')
					break

			# if the empty byte was received, the async for loop should end, and we should here forward the empty byte to deepgram
			# or, if the empty byte was not received, but the WS connection to the client (twilio) died, then the async for loop will end and we should forward an empty byte to deepgram
			outbox.put_nowait(b'')
			print('finished client receiver')

		await asyncio.wait([
			asyncio.ensure_future(deepgram_sender(deepgram_ws)),
			asyncio.ensure_future(deepgram_receiver(deepgram_ws)),
			asyncio.ensure_future(client_receiver(client_ws))
		])

		client_ws.close()
		print('finished running the proxy')

def main():
	# use this if using ssl
#	ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#	ssl_context.load_cert_chain('/cert.pem', 'key.pem')
#	proxy_server = websockets.serve(proxy, '0.0.0.0', 443, ssl=ssl_context)

	# use this if not using ssl
	proxy_server = websockets.serve(proxy, 'localhost', 5000)

	asyncio.get_event_loop().run_until_complete(proxy_server)
	asyncio.get_event_loop().run_forever()

if __name__ == '__main__':
	sys.exit(main() or 0)
