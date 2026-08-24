import os, json, datetime, urllib.parse
from supabase import create_client
import boto3
from botocore.config import Config

print("--- STARTING DAILY EMAIL PROCESS ---")

# Live Supabase Edge Function URL for unsubscribes
UNSUBSCRIBE_BASE_URL = "https://sgcekdbclvtpbavbpkuf.supabase.co/functions/v1/unsubscribe"

# 1. Force Ohio Region via Botocore Config
my_config = Config(
    region_name='us-east-2',
    signature_version='v4',
    retries={'max_attempts': 10, 'mode': 'standard'}
)

aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
sender_email = os.environ.get("SENDER_EMAIL", "").strip()
supabase_url = os.environ.get("SUPABASE_URL", "").strip()
supabase_key = os.environ.get("SUPABASE_KEY", "").strip()

print("Connecting to AWS SES explicitly on region: us-east-2")
print(f"Sender Email: {sender_email}")

# Initialize Supabase and SES
supabase = create_client(supabase_url, supabase_key)

ses = boto3.client(
    'ses',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    config=my_config
)

# 2. Load Sayings
with open("sayings.json") as f:
    sayings = json.load(f)

day_index = (datetime.datetime.now().timetuple().tm_yday - 1) % len(sayings)
current_maxim = sayings[day_index]
print(f"Loaded Maxim #{current_maxim['id']}")

# 3. Query Subscribers
res = supabase.table("subscribers").select("email, is_active").execute()
print(f"Raw rows returned from Supabase: {res.data}")

active_subscribers = [row["email"] for row in res.data if row.get("is_active") is True]
print(f"Filtered active subscribers: {active_subscribers}")

if not active_subscribers:
    print("CRITICAL: No subscribers found with 'is_active' = True. Stopping email dispatch.")

# 4. Dispatch Emails with Unique Unsubscribe Links
for recipient in active_subscribers:
    # Build unique unsubscribe link for this recipient
    encoded_email = urllib.parse.quote(recipient)
    unsubscribe_url = f"{UNSUBSCRIBE_BASE_URL}?email={encoded_email}"

    # HTML Email Template
    html_template = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; background-color: #f4f4f7; font-family: 'Georgia', serif; color: #333333;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f7; padding: 40px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden;">
          <tr>
            <td style="padding: 30px 40px 20px 40px; text-align: center; border-bottom: 1px solid #f0f0f0;">
              <span style="font-size: 12px; font-family: system-ui, sans-serif; letter-spacing: 2px; text-transform: uppercase; color: #888888;">Daily Reflection</span>
              <h1 style="margin: 8px 0 0 0; font-size: 22px; color: #1a1a1a; font-weight: normal;">Maxim #{current_maxim['id']}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px; text-align: center;">
              <blockquote style="margin: 0; padding: 0; font-size: 18px; line-height: 1.7; color: #2c3e50; font-style: italic;">
                "{current_maxim['text']}"
              </blockquote>
            </td>
          </tr>
          <tr>
            <td style="padding: 25px 40px; background-color: #fafafa; border-top: 1px solid #f0f0f0; text-align: center;">
              <p style="margin: 0 0 15px 0; font-size: 13px; line-height: 1.6; color: #666666; font-family: system-ui, sans-serif;">
                These maxims were selected from H.H. Dorje Chang Buddha III's writings and included in the book "H.H. Dorje Chang Buddha" in a chapter entitled "Philosophical Sayings about Worldly Matters".
              </p>
              <p style="margin: 0; font-size: 12px; font-family: system-ui, sans-serif; color: #999999;">
                You are receiving this because you subscribed to daily maxims.<br/>
                <a href="{unsubscribe_url}" style="color: #666666; text-decoration: underline;">Unsubscribe here</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    # Plain Text Fallback Body
    plain_text = (
        f"Daily Maxim #{current_maxim['id']}:\n\n"
        f"\"{current_maxim['text']}\"\n\n"
        f"These maxims were selected from H.H. Dorje Chang Buddha III's writings and included in the book "
        f"\"H.H. Dorje Chang Buddha\" in a chapter entitled \"Philosophical Sayings about Worldly Matters\".\n\n"
        f"To unsubscribe, visit: {unsubscribe_url}"
    )

    try:
        print(f"Attempting to send email from '{sender_email}' to '{recipient}' via AWS SES (us-east-2)...")
        response = ses.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': f"Daily Philosophical Maxim #{current_maxim['id']}"},
                'Body': {
                    'Text': {'Data': plain_text},
                    'Html': {'Data': html_template}
                }
            }
        )
        print(f"SUCCESS! AWS SES Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"FAILED to send to {recipient}. Error details:\n{e}")

print("--- FINISHED PROCESS ---")
