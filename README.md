# MailChimp Campaign 

# Extract
Fetch all campaign data up to the current date and save it to a JSON file. This script uses the Mailchimp Marketing API to extract detailed campaign information for further analysis.

## Features

- Retrieves campaigns created within a specified date range.

- Extracts:

  - Click details per campaign

  - subscriber activity per campaign

- describes any API errors or exceptions if present.

- Saves data in structured JSON files for further analysis.


![Alt text](https://github.com/OttoRichardson/MailChimp/blob/main/images/mailchimp%20workings.png)

## Requirements

Mailchimp Marketing Python SDK: mailchimp-marketing
```
pip install mailchimp-marketing
```
referance: https://github.com/mailchimp/mailchimp-marketing-python?utm_source=chatgpt.com

------

## How It Works

1. It calculates the date range:
  - since_create_time: e.g. 60 days ago .
  - before_create_time: end of yesterday.

2. initializes the Mailchimp client and retrieves campaigns created within the date range.

3. For each campaign:

  - Fetches detailed click data. ```mailchimp.reports.get_campaign_click_details(campaign_id)```
  
  - Fetches email activity data.
  ```mailchimp.reports.get_email_activity_for_campaign(campaign_id)```
  
  - Records the extraction timestamp.

4. Stores the combined campaign data in a JSON file

If no campaigns are found, the script prints No campaigns and exits.

## Orchestrating Extraction

A Daily Scan for New Campaigns

Each time the script runs, it looks back over a defined time window, Mailchimp returns any campaigns that were created or sent during that time.

```
LOOKBACK_DAYS = 2  # scan the last 48 hours

today = datetime.utcnow().date()
start_date = today - timedelta(days=LOOKBACK_DAYS)

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

```

Create a file to store all of the campaign id in 

```
SUMMARY_FILE = "data/campaigns_summary.json"

if os.path.exists(SUMMARY_FILE):
    with open(SUMMARY_FILE, "r") as f:
        campaign_summary = json.load(f)
else:
    campaign_summary = []  # start empty on first run

# lookup for existing campaign IDs
existing_ids = {c["id"] for c in campaign_summary}
```

Append and Save and new Campaigns to a Summary List


```new_campaigns = []

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
```




Here is the format of the output
```
{
  "id": "abc123",
  "title": "Weekly Newsletter",
  "send_time": "2024-02-12T13:02:55+00:00",
  "found_time": "2025-11-25T14:32:07.273851"
}

```

Once we have the master list of campaign IDs, the next part script updates to the most recent activitys by looping through ids

- Fetches detailed click data. ```mailchimp.reports.get_campaign_click_details(campaign_id)```
- Fetches email activity data.
  ```mailchimp.reports.get_email_activity_for_campaign(campaign_id)```

```
for campaign in campaigns:
            campaign_id = campaign["id"]

            try:
                    clicks = mailchimp.reports.get_campaign_click_details(campaign_id)
            except  ApiClientError as e:
                        clicks = {"error": str(e)}


            try:
                    activity  = mailchimp.reports.get_email_activity_for_campaign(campaign_id)
            except  ApiClientError as e:
                        activity  = {"error": str(e)}    



            campaign_full = {
                "campaign": campaign,
                "clicks": clicks,
                "activity": activity,
                "extract_time" : extract_time
            }
```

  output each campaign is a new json file

```
   output_file = f"data/campaigns/{camp_id}.json"

```
