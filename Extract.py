import os
from mailchimp_marketing import Client
from dotenv import load_dotenv
from mailchimp_marketing.api_client import ApiClientError 
from datetime import date, datetime, timedelta 
import json

load_dotenv()

# Read .env file
api_key = os.getenv('MAILCHIMP_API_KEY')
server_prefix = os.getenv('MAILCHIMP_SERVER_PREFIX')

today = date.today()

last_month = today - timedelta(days=60)

yesterday = today - timedelta(days=1)        # end of last week (up to yesterday)

since_create_time = str(last_month) + "T00:00:00+00:00"  # start of last week
before_create_time = str(yesterday) + "T23:59:59+00:00"      # end of yesterday


count = 1000
offset = 0


try:

    mailchimp = Client()
    mailchimp.set_config({
    "api_key": api_key,
    "server": server_prefix
    })

    # response = mailchimp.ping.get()
    # print(response)
    
    response = mailchimp.campaigns.list(
        count=count,
        offset=offset,
        since_create_time=since_create_time,
        before_create_time=before_create_time
    )

    campaigns = response.get('campaigns', [])  

    all_campaigns_data = []

    if len(campaigns) == 0:
        print("No campaigns")
    else: 
        print(f"Total campaigns: {len(campaigns)}")

        extract_time =datetime.now()

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
            
            all_campaigns_data.append(campaign_full)



except ApiClientError as error:
     print("Error: {}".format(error.text)) 
except Exception as e:
    print("Unexpected error:", str(e))


output_filename = "data/mailchimp_campaigns.json"

start_str = last_month.strftime("%Y-%m-%d")
end_str = yesterday.strftime("%Y-%m-%d")

output_filename = f"data/campaigns_{start_str}_to_{end_str}.json"

os.makedirs("data", exist_ok=True)
with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(all_campaigns_data, f, indent=2)
