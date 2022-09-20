import pyaudio
import asyncio
import sys
import websockets
import time
import json
import beepy
import shutil
import argparse

SILENCE_INTERVAL = 2.0

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 8000

terminal_size = shutil.get_terminal_size()

audio_queue = asyncio.Queue()

def callback(input_data, frame_count, time_info, status_flag):
    audio_queue.put_nowait(input_data)
    return (input_data, pyaudio.paContinue)

async def run(key):
    clock_cursor = 0.
    audio_cursor = 0.
    transcript_cursor = 0.

    async with websockets.connect(
        'wss://api.deepgram.com/v1/listen?interim_results=true&encoding=linear16&sample_rate=16000&channels=1', 
        extra_headers={
            'Authorization': 'Token {}'.format(key)
        }
    ) as ws:
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
                print(f'Error while sending: {str(e)}')
                raise

        async def receiver(ws):
            nonlocal clock_cursor, audio_cursor, transcript_cursor
            transcript = ''
            last_word_end = 0.0
            latest_final_result_processed = False
            async for msg in ws:
                msg = json.loads(msg)

                transcript_cursor = msg['start'] + msg['duration']

                if msg['is_final'] and len(msg['channel']['alternatives'][0]['transcript']) > 0:
                    latest_final_result_processed = False
                    transcript += ' '
                    transcript += msg['channel']['alternatives'][0]['transcript']
                    last_word_end = msg['channel']['alternatives'][0]['words'][-1]['end']
                    line = f'Clock: {clock_cursor:07.3f}, Audio: {audio_cursor:07.3f}, Transcript: {transcript_cursor:07.3f}; {transcript}'
                    print(line)
                    # using end='\r' doesn't work if the line wraps
                    # this moves the cursor up and overwrites the line regardless of length
                    # https://stackoverflow.com/a/47170056
                    print("\033[{}A".format(len(line) // int(terminal_size.columns) + 1), end='')

                elif not msg['is_final']:
                    if len(msg['channel']['alternatives'][0]['transcript']) > 0:
                        current_word_begin = msg['channel']['alternatives'][0]['words'][0]['start']
                        if current_word_begin - last_word_end > SILENCE_INTERVAL:
                            if len(transcript) > 0:
                                print(f'Clock: {clock_cursor:07.3f}, Audio: {audio_cursor:07.3f}, Transcript: {transcript_cursor:07.3f}; {transcript}')
                                beepy.beep(sound=1)
                                transcript = ''
                            latest_final_result_processed = True
                    else:
                        if transcript_cursor - last_word_end > SILENCE_INTERVAL:
                            if len(transcript) > 0:
                                print(f'Clock: {clock_cursor:07.3f}, Audio: {audio_cursor:07.3f}, Transcript: {transcript_cursor:07.3f}; {transcript}')
                                beepy.beep(sound=1)
                                transcript = ''
                            latest_final_result_processed = True


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
