import os
from twilio.rest import Client

def send_twilio_sms(to_number, message_body):
    """
    Sends an SMS using Twilio to the candidate containing their feedback summary
    and learning resources.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    
    if not account_sid or not auth_token or not from_number:
        return False, "Twilio credentials not fully configured in .env."
        
    if not to_number:
        return False, "No phone number provided."
        
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_number
        )
        return True, message.sid
    except Exception as e:
        return False, str(e)
