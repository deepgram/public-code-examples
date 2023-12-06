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
        const audio = Buffer.from(media["payload"], "base64");
        connection.send(audio);
      }
    });

    ws.on("close", () => {
      console.log("client has disconnected");
      if (connection) {
        connection.finish();
      }
    });

    ws.onerror = function () {
      console.log("some error occurred");
      connection.finish();
    };
  });
});

console.log("the websocket server is running on port 5000");
