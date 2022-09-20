import pyaudio
import asyncio
import sys
import websockets
import time
import json
import argparse
import beepy

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 8000

audio_queue = asyncio.Queue()

def callback(input_data, frame_count, time_info, status_flag):
    audio_queue.put_nowait(input_data)
    return (input_data, pyaudio.paContinue)

async def run(key):
    clock_cursor = 0.
    audio_cursor = 0.
    transcript_cursor = 0.

    extra_headers={
        'Authorization': 'Token {}'.format(key)
    }
    async with websockets.connect('wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&interim_results=false', extra_headers = extra_headers) as ws:
        async def microphone():
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                frames_per_buffer = CHUNK,
                stream_callback = callback
            )

            stream.start_stream()

            while stream.is_active():
                await asyncio.sleep(0.1)

            stream.stop_stream()
            stream.close()

        async def sender(ws):
            nonlocal clock_cursor, audio_cursor, transcript_cursor
            clock_start = time.perf_counter()
            try:
                while True:
                    data = await audio_queue.get()
                    clock_cursor = time.perf_counter() - clock_start
                    audio_cursor += float(len(data)) / float(RATE) / 2.0
                    await ws.send(data)
            except Exception as e:
                print('Error while sending: ', + string(e))
                raise

        async def receiver(ws):
            nonlocal clock_cursor, audio_cursor, transcript_cursor
            transcript = ''
            async for msg in ws:
                msg = json.loads(msg)

                transcript_cursor = msg['start'] + msg['duration']

                if len(msg['channel']['alternatives'][0]['transcript']) > 0:
                    transcript += ' '
                    transcript += msg['channel']['alternatives'][0]['transcript']
                    print(f'Clock: {clock_cursor:07.3f}, Audio: {audio_cursor:07.3f}, Transcript: {transcript_cursor:07.3f}; {transcript}', end = '\r')

                    if msg['speech_final']:
                        print(f'Clock: {clock_cursor:07.3f}, Audio: {audio_cursor:07.3f}, Transcript: {transcript_cursor:07.3f}; {transcript}')
                        beepy.beep(sound=1)
                        transcript = ''

        await asyncio.wait([
            asyncio.ensure_future(microphone()),
            asyncio.ensure_future(sender(ws)),
            asyncio.ensure_future(receiver(ws))
        ])

def parse_args():
    """ Parses the command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Submits data to the real-time streaming endpoint.')
    parser.add_argument('-k', '--key', required=True, help='YOUR_DEEPGRAM_API_KEY (authorization)')
    return parser.parse_args()

def main():
    args = parse_args()

    asyncio.run(run(args.key))

if __name__ == '__main__':
    sys.exit(main() or 0)
