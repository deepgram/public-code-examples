// Twilio helper library
const twilio = require("twilio");

// Your account SID and auth token from twilio.com/console
const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

// The Twilio client
const client = twilio(accountSid, authToken);

// Make the outgoing call
client.calls
  .create({
    twiml:
      '<Response><Start><Stream url="wss://url.to.deepgram.twilio.proxy" track="both_tracks" /></Start><Dial>+11231231234</Dial></Response>', // replace number with person B, replace url
    to: "+11231231234", // person A
    from: "+11231231234", // your Twilio number
  })
  .then((call) => console.log(call.sid))
  .catch((err) => console.error(err));
