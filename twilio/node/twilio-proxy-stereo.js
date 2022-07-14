const WebSocketServer = require('ws');
const { Deepgram } = require('@deepgram/sdk')

const websocketServer = new WebSocketServer.Server({ port: 5000 })
const deepgram = new Deepgram("INSERT_YOUR_API_KEY_HERE")

websocketServer.on("connection", ws => {
  console.log("new client connected");

  const deepgramLive = deepgram.transcription.live({
    encoding: "mulaw",
    sample_rate: 8000,
    channels: 2,
    multichannel: true
  });

  deepgramLive.addListener('transcriptReceived', (transcription) => {
    console.dir(transcription, { depth: null });
  });

  var inbound_samples = [];
  var outbound_samples = [];

  ws.on("message", data => {
    var twilio_message = JSON.parse(data);
    if (twilio_message["event"] === "connected" || twilio_message["event"] === "start") {
      console.log("received a twilio connected or start event");
    }
    if (twilio_message["event"] === "media") {
      var media = twilio_message["media"];
      var audio = Buffer.from(media["payload"], "base64");
      if (media["track"] === "inbound") {
        for (let i = 0; i < audio.length; i++) {
          inbound_samples.push(audio[i])
        }
      }
      if (media["track"] === "outbound") {
        for (let i = 0; i < audio.length; i++) {
          outbound_samples.push(audio[i])
        }
      }
      let mixable_length = Math.min(inbound_samples.length, outbound_samples.length);
      if (mixable_length > 0) {
        var mixed_samples = Buffer.alloc(mixable_length * 2);
        for (let i = 0; i < mixable_length; i++) {
          mixed_samples[2 * i] = inbound_samples[i];
          mixed_samples[2 * i + 1] = outbound_samples[i];
        }

        inbound_samples = inbound_samples.slice(mixable_length);
        outbound_samples = outbound_samples.slice(mixable_length);

        if (deepgramLive && deepgramLive.getReadyState() === 1) {
          deepgramLive.send(Buffer.from(mixed_samples));
        }
      }
    }
  });

  ws.on("close", () => {
    console.log("client has connected");
    if (deepgramLive && deepgramLive.getReadyState() === 1) {
      deepgramLive.finish();
    }
  });

  ws.onerror = function () {
    console.log("some error occurred")
    if (deepgramLive && deepgramLive.getReadyState() === 1) {
      deepgramLive.finish();
    }
  }
});

console.log("the websocket server is running on port 5000");
