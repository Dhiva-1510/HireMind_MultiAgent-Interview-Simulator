import os
from twilio.rest import Client

def send_twilio_sms(to_number, message_body):
    """
    Sends an SMS using Twilio to the candidate with their feedback summary.
    Returns (True, message_sid) on success, (False, reason) on failure.
    This function is designed to NEVER raise an exception — all errors are
    caught and returned gracefully so the interview flow is never interrupted.
    """
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()

        # Validate all credentials exist
        if not account_sid:
            return False, "TWILIO_ACCOUNT_SID not set."
        if not auth_token:
            return False, "TWILIO_AUTH_TOKEN not set."
        if not from_number:
            return False, "TWILIO_FROM_NUMBER not set. Please add a Twilio phone number."
        if not to_number or not str(to_number).strip():
            # Fall back to default number from .env
            to_number = os.getenv("TWILIO_TO_NUMBER", "").strip()
        
        if not to_number:
            return False, "No candidate phone number provided and TWILIO_TO_NUMBER not set."

        to_number = str(to_number).strip()

        # Twilio messages have a 1600-character limit
        if len(message_body) > 1600:
            message_body = message_body[:1597] + "..."

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_number
        )
        return True, message.sid

    except Exception as e:
        # Return the error cleanly — never crash the main application
        return False, f"Twilio error: {str(e)}"
