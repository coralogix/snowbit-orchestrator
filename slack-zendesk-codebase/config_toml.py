data = {
  "slack_details": {
    "post_message_to_slack": {
      "text": "An alert with description as {} has been raised in coralogix account {}. "
              "Is it approved operation or not?",
      "color": "#3AA3E3",
      "alert_message": "Alert Raised!"
    },
    "thanks_for_response": {
      "text": f"Thanks <@{{}}>!"
    }
  },
  "zendesk_details": {
    "ticket_fields_api_url": {
      "url": "https://antstackhelp.zendesk.com/api/v2/ticket_fields"

    },
    "ttl_data": {
      "low/med": 86400,
      "high/critical": 1800
    }

  },
  "database_messages": {
    ""
  }
}

import toml

output_file_name = "output.toml"

# toml_string = toml.dumps(data)  # writes to toml file
#
with open(output_file_name, "w") as toml_file:
    toml.dump(data, toml_file)


# Read from toml file
# with open(output_file_name, "r") as toml_file:
#   toml_string = toml.load(toml_file)

# print(toml_string)

# user = {'name': 'Mahesh M'}

# print(toml_string['slack_details']['thanks_for_response']['text'].format(user['name']))


