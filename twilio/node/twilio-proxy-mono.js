const WebSocketServer = require('ws');
const { Deepgram } = require('@deepgram/sdk')

const websocketServer = new WebSocketServer.Server({ port: 5000 })
const deepgram = new Deepgram("INSERT_YOUR_API_KEY_HERE")

websocketServer.on("connection", ws => {
  console.log("new client connected");

  const deepgramLive = deepgram.transcription.live({
    encoding: "mulaw",
    sample_rate: 8000,
    channels: 1
  });

  deepgramLive.addListener('transcriptReceived', (transcription) => {
    console.dir(transcription, { depth: null });
  });

  ws.on("message", data => {
    var twilio_message = JSON.parse(data);
    if (twilio_message["event"] === "connected" || twilio_message["event"] === "start") {
      console.log("received a twilio connected or start event");
    }
    if (twilio_message["event"] === "media") {
      var media = twilio_message["media"];
      var audio = Buffer.from(media["payload"], "base64");
      if (deepgramLive && deepgramLive.getReadyState() === 1) {
        deepgramLive.send(audio);
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
