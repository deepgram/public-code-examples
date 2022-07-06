# twilio integration

Two node scripts are provided which can do basic twilio-deepgram proxying. Run `node twilio-proxy-mono.js` or `node twilio-proxy-stereo.js`
to run the proxy server for either just the inbound track, or both the inbound and outbound tracks, respectively. They have the following dependencies:

```
npm install cross-fetch websocket
npm install cross-fetch @deepgram/sdk
```

Refer to the twilio documentation on streaming tracks for more info on mono vs stereo twilio streaming:

https://www.twilio.com/docs/voice/twiml/stream#attributes-track

In either script, you will need to add your Deepgram API Key where it says `INSERT_YOUR_API_KEY`,
as well as set up twilio to send websockets data to the server running the scripts. This is done via
TwiML Bin files: 

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

When calling your twilio number, the call will be forwarded to the number you set in your TwiML Bin. The
conversation will then be forked to this `twilio-proxy-mono`/`twilio-proxy-stereo` app which sends the audio to Deepgram, receives
transcriptions, and prints the transcriptions to the screen. You will likely want to do something like
provide an `http` (or websockets) callback to send transcriptions to.
