import toml

output_file_name = "output.toml"



data = {
  'validation': {
    'key_error': 'one of the keys {} could not be found in webhook',
    'json_decode_error': 'Wrong JSON format provided as input'
  },
  'database_opr': {
    'insertion_success': 'insertion successful for alert_id {} from aws_account_id at {}'

  },
  'url': {
    'local_server_url': 'http://127.0.0.1:8000/processpayload'
  }
}


# toml_string = toml.dumps(data)  

# with open(output_file_name, "w") as toml_file:  # writes 'data' to toml file
#     toml.dump(data, toml_file)



with open(output_file_name, "r") as toml_file: # reads from toml file
  toml_string = toml.load(toml_file)

print(toml_string)


