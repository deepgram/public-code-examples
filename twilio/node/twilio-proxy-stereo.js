const WebSocketServer = require("ws");
const { createClient, LiveTranscriptionEvents } = require("@deepgram/sdk");

const websocketServer = new WebSocketServer.Server({ port: 5000 });
const deepgramApiKey = "INSERT_YOUR_API_KEY_HERE";

websocketServer.on("connection", (ws) => {
  console.log("new client connected");

  const deepgram = createClient(deepgramApiKey);
  const connection = deepgram.listen.live({
    model: "nova-2",
    smart_format: true,
    encoding: "mulaw",
    sample_rate: 8000,
    channels: 1,
  });

  const inboundSamples = [];
  const outboundSamples = [];

  connection.on(LiveTranscriptionEvents.Open, () => {
    connection.on(LiveTranscriptionEvents.Close, () => {
      console.log("Connection closed.");
    });

    connection.on(LiveTranscriptionEvents.Transcript, (transcription) => {
      console.dir(transcription, { depth: null });
    });

    ws.on("message", (data) => {
      const twilioMessage = JSON.parse(data);
      if (
        twilioMessage["event"] === "connected" ||
        twilioMessage["event"] === "start"
      ) {
        console.log("received a twilio connected or start event");
      }
      if (twilioMessage["event"] === "media") {
        const media = twilioMessage["media"];
        var audio = Buffer.from(media["payload"], "base64");
        if (media["track"] === "inbound") {
          for (let i = 0; i < audio.length; i++) {
            inboundSamples.push(audio[i]);
          }
        }
        if (media["track"] === "outbound") {
          for (let i = 0; i < audio.length; i++) {
            outboundSamples.push(audio[i]);
          }
        }
        let mixable_length = Math.min(
          inboundSamples.length,
          outboundSamples.length
        );
        if (mixable_length > 0) {
          var mixedSamples = Buffer.alloc(mixable_length * 2);
          for (let i = 0; i < mixable_length; i++) {
            mixedSamples[2 * i] = inboundSamples[i];
            mixedSamples[2 * i + 1] = outboundSamples[i];
          }

          inboundSamples = inboundSamples.slice(mixable_length);
          outboundSamples = outboundSamples.slice(mixable_length);

          if (connection) {
            connection.send(Buffer.from(mixedSamples));
          }
        }
      }
    });

    ws.on("close", () => {
      console.log("client has disconnected");
      connection.finish();
    });

    ws.onerror = function () {
      console.log("some error occurred");
      connection.finish();
    };
  });
});

console.log("the websocket server is running on port 5000");
