import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError


# Load environment variables

load_dotenv()
API_KEY = os.getenv("MAILCHIMP_API_KEY")
SERVER = os.getenv("MAILCHIMP_SERVER_PREFIX")

if not API_KEY or not SERVER:
    raise ValueError("MAILCHIMP_API_KEY or MAILCHIMP_SERVER_PREFIX missing in .env")


# Create folders

os.makedirs("data", exist_ok=True)
os.makedirs("data/campaigns", exist_ok=True)

SUMMARY_FILE = "data/campaigns_summary.json"


# Load or create persistent summary list

if os.path.exists(SUMMARY_FILE):
    with open(SUMMARY_FILE, "r") as f:
        campaign_summary = json.load(f)
else:
    campaign_summary = []  # start empty on first run

# Maintain quick lookup for existing campaign IDs
existing_ids = {c["id"] for c in campaign_summary}


# Init Mailchimp client

mailchimp = Client()
mailchimp.set_config({
    "api_key": API_KEY,
    "server": SERVER
})


#Find new campaigns (Daily Scan)


# LOOKBACK_DAYS = 2  # scan the last 48 hours

# today = datetime.now() - timedelta(days=LOOKBACK_DAYS)

# start_date = today - timedelta(days=LOOKBACK_DAYS)



today = datetime.now() - timedelta(days=160)
start_date = today - timedelta(days=20)


since_create_time = f"{start_date}T00:00:00+00:00"
before_create_time = f"{today}T23:59:59+00:00"

print(f"Scanning for campaigns created between {since_create_time} → {before_create_time}")

try:
    response = mailchimp.campaigns.list(
        count=1000,
        offset=0,
        since_create_time=since_create_time,
        before_create_time=before_create_time
    )
except ApiClientError as e:
    print("Mailchimp error:", e.text)
    exit()

campaigns = response.get("campaigns", [])

print(f"Found {len(campaigns)} campaigns in scan window.")


# Append NEW campaigns to master summary


new_campaigns = []

for camp in campaigns:
    camp_id = camp["id"]
    if camp_id not in existing_ids:
        summary = {
            "id": camp_id,
            "title": camp.get("settings", {}).get("title", "Untitled"),
            "send_time": camp.get("send_time", None),
            "found_time": datetime.utcnow().isoformat()
        }

        new_campaigns.append(summary)
        campaign_summary.append(summary)
        existing_ids.add(camp_id)

print(f"New campaigns added: {len(new_campaigns)}")

# Save updated summary
with open(SUMMARY_FILE, "w") as f:
    json.dump(campaign_summary, f, indent=2)



# STEP 3 — Loop all known campaigns and fetch reports


print(f"Refreshing reports for {len(campaign_summary)} total campaigns...")

for camp in campaign_summary:
    camp_id = camp["id"]

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    output_file = f"data/campaigns/{camp_id}_{timestamp}.json"

    print(f" → Updating {camp_id}...")

    try:
        try:
            clicks = mailchimp.reports.get_campaign_click_details(camp_id)
        except ApiClientError as e:
            clicks = {"error": e.text}

        try:
            activity = mailchimp.reports.get_email_activity_for_campaign(camp_id)
        except ApiClientError as e:
            activity = {"error": e.text}

        full_data = {
            "campaign_id": camp_id,
            "title": camp["title"],
            "send_time": camp["send_time"],
            "last_updated": datetime.utcnow().isoformat(),
            "click_details": clicks,
            "email_activity": activity
        }

        # Save this campaign file
        with open(output_file, "w") as f:
            json.dump(full_data, f, indent=2)

    except Exception as e:
        print(f"Error updating {camp_id}: {e}")

print("Done.")

