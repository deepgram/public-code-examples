import asyncio
import base64
import json
import sys
import time
import websockets
import ssl
from pydub import AudioSegment

def deepgram_connect():
   	extra_headers = {
       		'Authorization': 'Token YOUR_DEEPGRAM_API_KEY'
   	}
	deepgram_ws = websockets.connect("wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=2&multichannel=true", extra_headers = extra_headers)

	return deepgram_ws

async def proxy(client_ws, path):
	# inbox = asyncio.Queue() # not needed unless sending ws messages back to the client
	outbox = asyncio.Queue()

	print('started proxy')

	async with deepgram_connect() as deepgram_ws:
		async def deepgram_sender(deepgram_ws):
			print('started deepgram sender')
			while True:
				chunk = await outbox.get()
				await deepgram_ws.send(chunk)
			print('finished deepgram sender')

		async def deepgram_receiver(deepgram_ws):
			print('started deepgram receiver')
			async for message in deepgram_ws:
				try:
					dg_json = json.loads(message)

					# print the results from deepgram! you may want to send this somewhere else, like a callback server, instead of just printing it out
					print(dg_json)
				except:
					print('was not able to parse deepgram response as json')
					continue
			print('finished deepgram receiver')

		async def client_receiver(client_ws):
			print('started client receiver')

			# directly outputting the audio to a file can be useful
			# the audio can be converted to a regular wav file via something like:
			# $ ffmpeg -f mulaw -ar 8000 -ac 2 -i mixed mixed.wav
#			file_inbound = open('inbound', 'wb')
#			file_outbound = open('outbound', 'wb')
#			file_mixed = open('mixed', 'wb')
#			file_manually_mixed = open('manually_mixed', 'wb')

			# we will use a buffer of 20 messages (20 * 160 bytes, 0.4 seconds) to improve throughput performance
			# NOTE: twilio seems to consistently send media messages of 160 bytes
			BUFFER_SIZE = 20 * 160
			# the algorithm to deal with mixing the two channels is ever so slightly sophisticated
			# I try here to implement an algorithm which fills in silence for channels if that channel is either
			#   A) not currently streaming (e.g. the outbound channel when the inbound channel starts ringing it)
			#   B) packets are dropped (this happens, and sometimes the timestamps which come back for subsequent packets are not aligned, I try to deal with this)
			inbuffer = bytearray(b'')
			outbuffer = bytearray(b'')
			empty_byte_received = False
			inbound_chunks_started = False
			outbound_chunks_started = False
			latest_inbound_timestamp = 0
			latest_outbound_timestamp = 0
			async for message in client_ws:
				try:
					data = json.loads(message)
					if data["event"] in ("connected", "start"):
						print("Media WS: Received event connected or start")
						continue
					if data["event"] == "media":
						media = data["media"]
						chunk = base64.b64decode(media["payload"])
						if media['track'] == 'inbound':
							# fills in silence if there have been dropped packets
							if inbound_chunks_started:
								if latest_inbound_timestamp + 20 < int(media['timestamp']):
									bytes_to_fill = 8 * (int(media['timestamp']) - (latest_inbound_timestamp + 20))
									print ('INBOUND WARNING! last timestamp was ' + str(latest_inbound_timestamp) + ' but current packet is for timestamp ' + media['timestamp'] + ', filling in ' + str(bytes_to_fill) + ' bytes of silence')
									inbuffer.extend(b"\xff" * bytes_to_fill) # NOTE: 0xff is silence for mulaw audio, and there are 8 bytes per ms of data for our format (8 bit, 8000 Hz)
							else:
								print ('started receiving inbound chunks!')
								# make it known that inbound chunks have started arriving
								inbound_chunks_started = True
								latest_inbound_timestamp = int(media['timestamp'])
								# this basically sets the starting point for outbound timestamps
								latest_outbound_timestamp = int(media['timestamp']) - 20
							latest_inbound_timestamp = int(media['timestamp'])
							# extend the inbound audio buffer with data
							inbuffer.extend(chunk)
						if media['track'] == 'outbound':
							# make it known that outbound chunks have started arriving
							outbound_chunked_started = True
							# fills in silence if there have been dropped packets
							if latest_outbound_timestamp + 20 < int(media['timestamp']):
								bytes_to_fill = 8 * (int(media['timestamp']) - (latest_outbound_timestamp + 20))
								print ('OUTBOUND WARNING! last timestamp was ' + str(latest_outbound_timestamp) + ' but current packet is for timestamp ' + media['timestamp'] + ', filling in ' + str(bytes_to_fill) + ' bytes of silence')
								outbuffer.extend(b"\xff" * bytes_to_fill) # NOTE: 0xff is silence for mulaw audio, and there are 8 bytes per ms of data for our format (8 bit, 8000 Hz)
							latest_outbound_timestamp = int(media['timestamp'])
							# extend the outbound audio buffer with data
							outbuffer.extend(chunk)
						if chunk == b'':
							empty_byte_received = True
					if data["event"] == "stop":
						print("Media WS: Received event stop")
						break

					# check if our buffer is ready to send to our outbox (and, thus, then to deepgram)
					while len(inbuffer) >= BUFFER_SIZE and len(outbuffer) >= BUFFER_SIZE or empty_byte_received:
						if empty_byte_received:
							break

						print ( str(len(inbuffer)) + ' ' + str(len(outbuffer)) )
						asinbound = AudioSegment(inbuffer[:BUFFER_SIZE], sample_width=1, frame_rate=8000, channels=1)
						asoutbound = AudioSegment(outbuffer[:BUFFER_SIZE], sample_width=1, frame_rate=8000, channels=1)
						mixed = AudioSegment.from_mono_audiosegments(asinbound, asoutbound)

						# if you don't have a nice library for mixing, you can always trivially manually mix the channels like so
#						manually_mixed = bytearray(b'')
#						for i in range(BUFFER_SIZE):
#							manually_mixed.append(inbuffer[i])
#							manually_mixed.append(outbuffer[i])

#						file_inbound.write(asinbound.raw_data)
#						file_outbound.write(asoutbound.raw_data)
#						file_mixed.write(mixed.raw_data)
#						file_manually_mixed.write(manually_mixed)

						# sending to deepgram
						outbox.put_nowait(mixed.raw_data)
#						outbox.put_nowait(manually_mixed)

						# clearing buffers
						inbuffer = inbuffer[BUFFER_SIZE:]
						outbuffer = outbuffer[BUFFER_SIZE:]
				except:
					print('message from client not formatted correctly, bailing')
					break

			# if the empty byte was received, the async for loop should end, and we should here forward the empty byte to deepgram
			# or, if the empty byte was not received, but the WS connection to the client (twilio) died, then the async for loop will end and we should forward an empty byte to deepgram
			outbox.put_nowait(b'')
			print('finished client receiver')

#			file_inbound.close()
#			file_outbound.close()
#			file_mixed.close()
#			file_manually_mixed.close()

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
#	ssl_context.load_cert_chain('cert.pem', 'key.pem')
#	proxy_server = websockets.serve(proxy, '0.0.0.0', 443, ssl=ssl_context)

	# use this if not using ssl
	proxy_server = websockets.serve(proxy, 'localhost', 5000)

	asyncio.get_event_loop().run_until_complete(proxy_server)
	asyncio.get_event_loop().run_forever()

if __name__ == '__main__':
	sys.exit(main() or 0)
