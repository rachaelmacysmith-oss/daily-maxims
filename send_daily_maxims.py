import os, json, datetime
from supabase import create_client
import boto3

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

ses = boto3.client(
    'ses',
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

with open("sayings.json") as f:
    sayings = json.load(f)

# Rotates sequentially through maxims by day of year
day_index = (datetime.datetime.now().timetuple().tm_yday - 1) % len(sayings)
current_maxim = sayings[day_index]

res = supabase.table("subscribers").select("email").eq("is_active", True).execute()
subscribers = [row["email"] for row in res.data]

# HTML Email Template
html_template = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f7; font-family: 'Georgia', serif; color: #333333;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f7; padding: 40px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e2e8f0;">
          
          <!-- Header -->
          <tr>
            <td style="padding: 30px 40px 20px 40px; text-align: center; border-bottom: 1px solid #f0f0f0;">
              <span style="font-size: 12px; font-family: system-ui, sans-serif; letter-spacing: 2px; text-transform: uppercase; color: #888888;">Daily Reflection</span>
              <h1 style="margin: 8px 0 0 0; font-size: 22px; color: #1a1a1a; font-weight: normal;">Maxim #{current_maxim['id']}</h1>
            </td>
          </tr>

          <!-- Maxim Content -->
          <tr>
            <td style="padding: 40px; text-align: center;">
              <blockquote style="margin: 0; padding: 0; font-size: 18px; line-height: 1.7; color: #2c3e50; font-style: italic;">
                "{current_maxim['text']}"
              </blockquote>
            </td>
          </tr>

          <!-- Footer / Attribution -->
          <tr>
            <td style="padding: 25px 40px; background-color: #fafafa; border-top: 1px solid #f0f0f0; text-align: center;">
              <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #666666; font-family: system-ui, sans-serif;">
                These maxims were selected from H.H. Dorje Chang Buddha III's writings and included in the book "H.H. Dorje Chang Buddha" in a chapter entitled "Philosophical Sayings about Worldly Matters".
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

plain_text = f"Daily Maxim #{current_maxim['id']}:\n\n\"{current_maxim['text']}\"\n\nThese maxims were selected from H.H. Dorje Chang Buddha III's writings and included in the book \"H.H. Dorje Chang Buddha\" in a chapter entitled \"Philosophical Sayings about Worldly Matters\"."

for email in subscribers:
    try:
        ses.send_email(
            Source=os.environ["SENDER_EMAIL"],
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': f"Daily Philosophical Maxim #{current_maxim['id']}"},
                'Body': {
                    'Text': {'Data': plain_text},
                    'Html': {'Data': html_template}
                }
            }
        )
    except Exception as e:
        print(f"Error sending to {email}: {e}")
