""" A simple example which prints out parsed streaming responses.
    Python version: 3.6+
    Dependencies (use `pip install X` to install a dependency):
      - websockets
    Usage:
      python deepgram_streaming.py -u USERNAME:PASSWORD /path/to/audio.wav
    Limitations:
      - Only parses signed, 16-bit little-endian encoded WAV files.
"""

import argparse
import asyncio
import base64
import json
import sys
import wave
import websockets
import subprocess

# Mimic sending a real-time stream by sending this many seconds of audio at a time.
REALTIME_RESOLUTION = 0.100

async def run(data, auth, channels, sample_width, sample_rate, filepath):
    # How many bytes are contained in one second of audio.
    byte_rate = sample_width * sample_rate * channels
    print('This demonstration will print all finalized results, not interim results.')

    # Connect to the real-time streaming endpoint, attaching our credentials.
    async with websockets.connect(
        # Alter the protocol and base URL below.
        f'wss://cab2b5852c84ae12.deepgram.com/v2/listen/stream?punctuate=true&channels={channels}&sample_rate={sample_rate}&encoding=linear16',
        extra_headers={
            'Authorization': 'Basic {}'.format(base64.b64encode(auth.encode()).decode())
        }
    ) as ws:
        async def sender(ws):
            """ Sends the data, mimicking a real-time connection.
            """
            nonlocal data
            try:
                total = len(data)
                while len(data):
                    # How many bytes are in `REALTIME_RESOLUTION` seconds of audio?
                    i = int(byte_rate * REALTIME_RESOLUTION)
                    chunk, data = data[:i], data[i:]
                    # Send the data
                    await ws.send(chunk)
                    # Mimic real-time by waiting `REALTIME_RESOLUTION` seconds
                    # before the next packet.
                    await asyncio.sleep(REALTIME_RESOLUTION)

                # An empty binary message tells Deepgram that no more audio
                # will be sent. Deepgram will close the connection once all
                # audio has finished processing.
                await ws.send(b'')
            except Exception as e:
                print(f'Error while sending: {e}')
                raise

        async def receiver(ws):
            """ Print out the messages received from the server.
            """
            async for msg in ws:
                res = json.loads(msg)
                try:
                    # To see interim results in this demo, remove the conditional `if res['is_final']:`.
                    if res['is_final']:
                        transcript = res['channel']['alternatives'][0]['transcript']
                        start = res['start']
                        print(f'{transcript}')
                except KeyError:
                    print(msg)

        await asyncio.wait([
            asyncio.ensure_future(sender(ws)),
            asyncio.ensure_future(receiver(ws))
        ])
        print()

def parse_args():
    """ Parses the command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Submits data to the real-time streaming endpoint.')
    parser.add_argument('-u', '--user', required=True, help='USER:PASS authorization.')
    parser.add_argument('input', help='Input file.')
    return parser.parse_args()

def main():
    """ Entrypoint for the example.
    """
    # Parse the command-line arguments.
    args = parse_args()

    # Open the audio file.
    with wave.open(args.input, 'rb') as fh:
        (channels, sample_width, sample_rate, num_samples, _, _) = fh.getparams()
        assert sample_width == 2, 'WAV data must be 16-bit.'
        data = fh.readframes(num_samples)
    print(f'Channels = {channels}, Sample Rate = {sample_rate} Hz, Sample width = {sample_width} bytes, Size = {len(data)} bytes', file=sys.stderr)

    # Run the example.
    asyncio.get_event_loop().run_until_complete(run(data, args.user, channels, sample_width, sample_rate, args.input))

if __name__ == '__main__':
    sys.exit(main() or 0)
