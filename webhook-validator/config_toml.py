import toml

output_file_name = "output.toml"



data = {
  'validation': {
    'key_error': 'one of the keys {} could not be found in webhook',
    'json_decode_error': 'Wrong JSON format provided as input'
  },
  'database_opr': {
    'insertion_success': 'insertion successful for alert_id {} from aws_account_id at {}'

  }
}


# toml_string = toml.dumps(data)  # writes to above data toml file

# with open(output_file_name, "w") as toml_file:
#     toml.dump(data, toml_file)



with open(output_file_name, "r") as toml_file: # reads from toml file
  toml_string = toml.load(toml_file)

print(toml_string)


