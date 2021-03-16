# twilio helper library
from twilio.rest import Client

# other imports
import time
import requests
import json
import os
import uuid

# your account sid and auth token from twilio.com/console
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
# the twilio client
client = Client(account_sid, auth_token)
# make the outgoing call
call = client.calls.create(
  twiml = '<Response><Start><Stream url="wss://url.to.deepgram.twilio.proxy" track="both_tracks" /></Start><Dial>+11231231234</Dial></Response>', # replace number with person B, replace url
  to = '+11231231234', # person A
  from_ = '+11231231234' # your twilio number
)
