#!/usr/bin/env python3

# Usage: Pipe output into an executable version of this script.
# E.g.: curl <request here> | build_diarized_transcript.py

import json
import sys

def parse_response(res):
    res = json.loads(res)
    metadata = res['metadata']
    channels = metadata['channels']
    print('Duration: {:.3f}'.format(metadata['duration']))
    print('Channels: {}'.format('channels'))
    print()
    for channel in range(channels):
        if channel != 0:
            print()
        print('Channel: {} of {}'.format(channel+1, channels))
        words = res['results']['channels'][channel]['alternatives'][0]['words']
        speaker = None
        run = []
        for word in words:
            if speaker is not None and speaker != word["speaker"]:
                print("[{:.3f} - {:.3f}] {}: {}".format(run[0]["start"], run[-1]["end"], speaker, ' '.join(w["word"] for w in run)))
                run = []
            run.append(word)
            speaker = word["speaker"]
        if run:
            print("[{:.3f} - {:.3f}] {}: {}".format(run[0]["start"], run[-1]["end"], speaker, ' '.join(w["word"] for w in run)))

if __name__ == '__main__':
   sys.exit(parse_response(sys.stdin.read()) or 0)
