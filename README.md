# MailChimp Campaign 

# Extract
Fetch all campaign data up to the current date and save it to a JSON file. This script uses the Mailchimp Marketing API to extract detailed campaign information for further analysis.

## Features

- Retrieves campaigns created within a specified date range.

- Extracts:

  - Click details per campaign

  - Email activity per campaign

- describes any API errors or exceptions if present.

- Saves data in structured JSON files for further analysis.



## Requirements

Mailchimp Marketing Python SDK: mailchimp-marketing
```
pip install mailchimp-marketing
```
referance: https://github.com/mailchimp/mailchimp-marketing-python?utm_source=chatgpt.com

------

How It Works

1. It calculates the date range:
  - since_create_time: 60 days ago by default.
  - before_create_time: end of yesterday.

2. initializes the Mailchimp client and retrieves campaigns created within the date range.

3. For each campaign:

  - Fetches detailed click data. ```mailchimp.reports.get_campaign_click_details(campaign_id)```
  
  - Fetches email activity data.
  ```mailchimp.reports.get_email_activity_for_campaign(campaign_id)```
  
  - Records the extraction timestamp.

4. Stores the combined campaign data in a JSON file inside data/ folder.
file format: ```data/campaigns_<start_date>_to_<end_date>.json```

If no campaigns are found, the script prints No campaigns and exits.
