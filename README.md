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
referance: https://github.com/mailchimp/mailchimp-marketing-python?

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


# Load

After extracting and processing event data from Amplitude, the next step is to upload the JSON files to an S3 bucket for storage, backup, or further processing. This step ensures that the data is accessible to other systems and keeps local storage clean.

## Requirements

```
import os from dotenv import load_dotenv import boto3
```



## Set Up

![Alt text](https://github.com/OttoRichardson/MailChimp/blob/main/images/Load%20mailchimp.png)

Create S3 client
```
s3_client = boto3.client( 's3', aws_access_key_id=aws_access_key, aws_secret_access_key=AWS_ACCESS_SECRET_KEY )
```

### Collect all filenames in the output folder

```
files_to_upload = [] for root, _, filenames in os.walk(output_folder): files_to_upload.extend(filenames)

for file in files_to_upload: aws_file_destination = "python-import/" + file output_path = os.path.join(output_folder, file) s3_client.upload_file(output_path, bucket, aws_file_destination) print(f"Uploaded: {file}")
```

## SNOWPIPE AND STORAGE INTERGRATION 
A Storage Integration is a Snowflake object that allows Snowflake to securely read data from Amazon S3 without storing long-lived AWS credentials

Snowflake creates a short-lived AWS IAM role session, and AWS enforces access using IAM trust policies

```
CREATE OR REPLACE STORAGE INTEGRATION OR_MAILCHIMP_STORAGE_INTEGRATION
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam:::role/ottorichardson-snowflake-amplitude-python'
  STORAGE_ALLOWED_LOCATIONS = ('s3://ottorichardson-amplitude-storage/mailchimp/');

```

After creation, inspect the integration:
``` DESC INTEGRATION OR_MAILCHIMP_STORAGE_INTEGRATION; ```

This returns values you must include in the AWS role trust policy:

STORAGE_AWS_EXTERNAL_ID

STORAGE_AWS_IAM_USER_ARN

### File Format (JSON)
We define a dedicated JSON file format to ensure consistent parsing—especially the STRIP_OUTER_ARRAY option, which expands arrays of objects into individual rows.

```
CREATE OR REPLACE FILE FORMAT ottorichardson_json_format
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = TRUE;

```

### SNOWPIPE 

Event notifications (S3  → SQS → Snowflake)
to set this up
Go to s3 bucket, click on Properties and scroll to event notificationsConfigure

In Snowflake:

```
CREATE OR REPLACE PIPE OR_RAW_MAILCHIMP_PIPE
AUTO_INGEST = TRUE
AS
COPY INTO RAW_MAILCHIMP_JSON
FROM @OR_MAILCHIMP_STAGE
FILE_FORMAT = (FORMAT_NAME = ottorichardson_json_format)
;
```

## STAGING


### Campaign-level table

Granularity: One row per campaign.

- Each row represents a single campaign.

- No nested arrays—this is your “base” table.

Candidate unique key:

- campaign_id (Mailchimp already provides this)

| Column           | Purpose                    | Key?          |
| ---------------- | -------------------------- | ------------- |
| campaign_id      | Unique campaign ID         | ✅ Primary key |
| title            | Campaign title             |               |
| send_time        | Send time                  |               |
| last_updated     | Last updated timestamp     |               |
| total_clicks     | Total clicks               |               |
| total_urls       | Count of URLs              |               |
| total_recipients | Count of recipients/emails |               |

```
CREATE OR REPLACE TABLE BASE_CAMPAIGNS AS
SELECT
    json_data:campaign_id::STRING       AS campaign_id, --PRIMARY_KEY
    json_data:title::STRING             AS title,
    json_data:send_time::STRING  AS send_time,
    json_data:last_updated::STRING AS last_updated,
    json_data:click_details:total_items::NUMBER AS total_clicks,
    json_data:email_activity:total_items::NUMBER AS total_recipients
FROM RAW_MAILCHIMP_JSON
;

```


### URL-level click details

Granularity: One row per campaign per URL.

- Each row is a URL clicked in a campaign.

- Nested array urls_clicked is flattened.

Candidate unique key:
- url_id

| Column                  | Purpose                 | Key?     |
| ----------------------- | ----------------------- | -------- |
| campaign_id             | FK to campaign          |          |
| url_id                  | URL identifier          | ✅  Primary key     |
| url                     | URL string              |          |
| total_clicks            | Total clicks            |          |
| unique_clicks           | Unique clicks           |          |
| click_percentage        | Click %                 |          |
| unique_click_percentage | Unique click %          |          |
| last_click              | Timestamp of last click |          |


```
CREATE OR REPLACE TABLE BASE_URL_CLICKS AS
SELECT
    c.json_data:campaign_id::STRING AS campaign_id,
    url.value:id::STRING         AS url_id,   -- PRIMARY_KEY
    url.value:url::STRING        AS url,
    url.value:total_clicks::NUMBER AS total_clicks,
    url.value:unique_clicks::NUMBER AS unique_clicks,
    url.value:click_percentage::FLOAT AS click_percentage,
    url.value:unique_click_percentage::FLOAT AS unique_click_percentage,
    url.value:last_click::TIMESTAMP_NTZ AS last_click
FROM RAW_MAILCHIMP_JSON c,
     LATERAL FLATTEN(input => c.json_data:click_details:urls_clicked) url;
```

### Email-level activity

Granularity: One row per email per activity.

- Flatten emails array and then activity array.

Candidate unique key:

- campaign_id + email_id + action + timestamp
  ``` MD5(email.value:campaign_id::STRING || email.value:email_id::STRING || a.value:action::STRING || TO_VARCHAR(a.value:timestamp)) AS email_activity_hash```

| Column              | Purpose                             | Key?     |
| ------------------- | ----------------------------------- | -------- |
| campaign_id         | FK to campaign                      | ✅        |
| email_id            | Recipient email ID                  | ✅        |
| email_address       | Email address                       |          |
| list_id             | Mailchimp list ID                   |          |
| list_is_active      | List status                         |          |
| action              | Activity action (click, open, etc.) | ✅        |
| timestamp           | Timestamp of activity               | ✅        |
| ip                  | IP address from event               |          |
| email_activity_hash | Hash for uniqueness |✅  Primary key    | 

```

CREATE OR REPLACE TABLE BASE_EMAIL_ACTIVITY AS
SELECT
    MD5(e.value:campaign_id::STRING || e.value:email_id::STRING || a.value:action::STRING || TO_VARCHAR(a.value:timestamp)) AS activity_id,
    e.value:campaign_id::STRING    AS campaign_id,
    e.value:list_id::STRING        AS list_id,
    e.value:list_is_active::BOOLEAN AS list_is_active,
    e.value:email_id::STRING       AS email_id,
    e.value:email_address::STRING  AS email_address,
    a.value:action::STRING         AS action,
    a.value:timestamp::TIMESTAMP_NTZ AS timestamp,
    a.value:ip::STRING             AS ip
FROM RAW_MAILCHIMP_JSON c,
     LATERAL FLATTEN(input => c.json_data:email_activity:emails) e,
     LATERAL FLATTEN(input => e.value:activity) a;

     SELECT * FROM BASE_EMAIL_ACTIVITY;
```

# Orchestration 

when we come to automating the extraction we need master campaign data to perform our de-duping but we dont wanr to store or publish JSON data directly in the repository.
Instead, i've used our S3 bucket as the storage layer for both reading and writing to the campaign summary.

![Alt text](https://github.com/OttoRichardson/MailChimp/blob/main/images/Master%20file%20in%20S3.png)

This means are script needs adapting in the following ways:

### Loading the Existing Summary From S3
```
try:
    obj = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=SUMMARY_FILE_NAME)
    campaign_summary = json.loads(obj['Body'].read().decode('utf-8'))
    print(f"Loaded {len(campaign_summary)} campaigns from S3")
except s3_client.exceptions.NoSuchKey:
    print("No existing summary found on S3. Starting empty.")
    campaign_summary = []

```

### Uploading the Updated Summary Back to S3

```
s3_client.put_object(
    Bucket=AWS_BUCKET_NAME,
    Key=SUMMARY_FILE_NAME,
    Body=json.dumps(campaign_summary, indent=2).encode('utf-8')
)
print("Updated summary saved to S3")

```

Using GitHub Actions as our python orchestration tool we can schedule this extraction and the load to run daily 


![Alt text](https://github.com/OttoRichardson/MailChimp/blob/main/images/github%20action%20path.png)


## 1. Add Required credentials into GitHub Environments
Navigate to your repository.
Go to Settings → Environments.
Create a new environment (e.g., dev, uat, prod).
Add secrets (API keys, passwords, buckets)

## 2: Create a Workflow in YAML 

Here’s the structure we will follow:

```
on:
  schedule:
  #ONCE A DAY AT 8:00
    - cron: '0 8 * * *' 
  #ALLOW THE WORKFLOW TO RUN MANUALLY
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    environment: Mail Chimp Environment
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v2
        
      - name: Setup python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12.10'
      - name: Install packages
        run: pip install -r requirements.txt

      - name: Run the Extract Python script
      env:
      SECRET_KEY: ${{secrets.SECRET_KEY}}
      run: python extract.py
      
      - name: Run the Load Python script
      env:
      SECRET_KEY: ${{secrets.SECRET_KEY}}
      run: python load.py

```

- name: – gives your workflow a name.
- on: – defines when it triggers (scheduled and/or manual).
- jobs: – defines what you want to happen
- build: – is the name/ID of a job (can be called anything test, deploy, ingest-data, etc.).
- runs-on: – specifies the virtual environment (Ubuntu, Windows, macOS).
- steps are the individual actions the job performs.
- run: a step that can run shell commands
- uses: prebuilt GitHub Actions


## REMOVING OUTDATED CAMPAIGN DATA

Over time, as the Mailchimp extraction runs, multiple JSON files with the same campaign IDs but different timestamps accumulate in S3. These outdated files will also propagate to the RAW table in Snowflake, creating duplicate or superseded campaign data.

![Alt text](https://github.com/OttoRichardson/MailChimp/blob/main/images/thinking%20about%20removing%20duplicated%20data.png)


In Snowflake, the first staging table uses a ROW_NUMBER calculation to identify the most recent record per campaign. Only the latest version is moved forward for downstream processing.

We also want to periodically remove older campaigns from the RAW table, we use a stored procedure and a scheduled task:


Stored Procedure: DELETE_OLD_CAMPAIGN_ROWS_PROC
```
CREATE OR REPLACE PROCEDURE DELETE_OLD_CAMPAIGN_ROWS_PROC()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    DELETE FROM RAW_MAILCHIMP_JSON
    WHERE (CAMPAIGN_ID, file_ts) IN (
        SELECT CAMPAIGN_ID, file_ts
        FROM (
            SELECT CAMPAIGN_ID, file_ts,
                   ROW_NUMBER() OVER (PARTITION BY CAMPAIGN_ID ORDER BY file_ts DESC) AS RN
            FROM RAW_MAILCHIMP_JSON
        ) t
        WHERE RN != 1
    );

    RETURN 'Old campaign rows deleted successfully';
END;
$$;
```
Scheduled Task: DELETE_OLD_CAMPAIGN_ROWS_TASK
```
CREATE OR REPLACE TASK DELETE_OLD_CAMPAIGN_ROWS_TASK
WAREHOUSE = DATASCHOOL_WH
SCHEDULE = 'USING CRON 0 10 1,15 * * UTC'  -- Runs twice a month at 10:00 UTC
AS
CALL DELETE_OLD_CAMPAIGN_ROWS_PROC();
```


## Managing Outdated Files in s3
Here we might want to build a python script to remove the  multiple campaign JSON files 

# Transformation


![Alt text](https://github.com/OttoRichardson/MailChimp/blob/main/images/DBT%20plan%20mailchimp.png)


## Source Configuration

```yaml
version: 2

sources:
  - name: RAW_MAILCHIMP
    database: TIL_DATA_ENGINEERING
    schema: OR_MAILCHIMP
    tables:
      - name: RAW_MAILCHIMP_JSON
        columns:
          - name: JSON_DATA
            data_type: variant
            description: "Raw JSON payload from Mailchimp"
            data_tests:
              - not_null
          - name: CAMPAIGN_ID
            data_type: STRING
            description: "Primary key for campaigns"
            data_tests:
              - not_null
          - name: FILE_TS
            data_type: TIMESTAMP_NTZ
            description: "Timestamp that the file was extracted"
            data_tests:
              - not_null
        loaded_at_field: FILE_TS
        freshness:
          warn_after: {count: 24, period: hour}
```

> This setup tells dbt where to find the raw JSON table, which column to use for freshness tracking, and basic data tests.

---

### Transformation Workflow

1. **Raw Data Selection**

```sql
WITH RAW_MAILCHIMP_JSON AS (
    SELECT * 
    FROM {{ source('RAW_MAILCHIMP', 'RAW_MAILCHIMP_JSON') }}
)
```

* Pulls all raw records from the Mailchimp source table.

2. **Staging & Deduplication**

```sql
, STG_MAILCHIMP_JSON AS (
    SELECT 
        ROW_NUMBER() OVER (PARTITION BY CAMPAIGN_ID ORDER BY file_ts DESC) AS RN,
        json_data:campaign_id::STRING       AS campaign_id,
        json_data:title::STRING             AS title,
        json_data:send_time::STRING         AS send_time,
        json_data:last_updated::STRING      AS last_updated,
        json_data:click_details:total_items::NUMBER AS total_clicks,
        json_data:email_activity:emails::variant  AS email_activity,
        json_data:click_details:urls_clicked::variant AS click_details
    FROM RAW_MAILCHIMP_JSON
)
```

* Converts JSON fields into structured columns.
* Assigns a row number (`RN`) to deduplicate campaigns, keeping the latest record by `file_ts`.

3. **Final Selection**

```sql
SELECT * FROM STG_MAILCHIMP_JSON
-- WHERE RN = 1
```

* filter `RN = 1` to retain only the newest record per campaign.

---

### Staging Model

```yaml
version: 2

models:
  - name: stg_mailchimp_json
    description: "Staging model for Mailchimp campaign JSON. Deduplicates campaigns by keeping only the newest file_ts per campaign."
    columns:
      - name: campaign_id
        description: "Unique ID for each campaign."
        tests:
          - not_null
          - unique
      - name: title
        description: "Campaign title."
      - name: send_time
        description: "Time the campaign was sent."
      - name: last_updated
        description: "Timestamp of the last update for the campaign."
      - name: total_clicks
        description: "Total clicks recorded in the campaign."
      - name: email_activity
        description: "Nested JSON array of email activity events."
      - name: click_details
        description: "Nested JSON array of click details for each URL."
      - name: rn
        description: "Row number assigned by window function (used for deduplication)."
```





