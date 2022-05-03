# twilio integration

Two python scripts are provided which can do basic twilio-deepgram proxying. Run `python3 twilio-proxy-mono.py` or `python3 twilio-proxy-stereo.py`
to run the proxy server for either just the inbound track, or both the inbound and outbound tracks, respectively. Refer to the twilio documentation on streaming tracks for more info:

https://www.twilio.com/docs/voice/twiml/stream#attributes-track

In either script, you will need to change your `username` and `password`, as well as set up twilio to send websockets data to the server running the scripts. Refer to the following
twilio documentation to do this (don't use the example python Flask application though, use our `twilio-proxy-mono` or `twilio-proxy-stereo` script instead):

https://www.twilio.com/docs/voice/tutorials/consume-real-time-media-stream-using-websockets-python-and-flask
https://www.twilio.com/docs/runtime/tutorials/twiml-bins

My TwiML Bin files ended up looking like the following for mono:

```
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream url="wss://my-server-address" />
     </Start>
     <Dial>my-phone-number</Dial>
</Response>
```

and the following for stereo (just adding the extra `track` parameter):

```
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream url="wss://my-server-address" track="both_tracks" />
     </Start>
     <Dial>my-phone-number</Dial>
</Response>
```

(Alternatively, you can try initiating a call between "Person A" and "Person B", and having the call data forwarded to the twilio-deepgram proxy using the script in `twilio-api-scripts/stream.py`.)

When calling your twilio number, the call will be forwarded to the number you set in your TwiML Bin. The
conversation will then be forked to this `twilio-proxy-mono`/`twilio-proxy-stereo` app which sends the audio to Deepgram, receives
transcriptions, and prints the transcriptions to the screen. You will likely want to do something like
provide an `http` (or websockets) callback to send transcriptions to.
