import argparse
import json
import time
import jwt
import requests
import csv
import os
from requests_toolbelt.multipart.encoder import MultipartEncoder

### STEPS ###
# 1. Read headers from CSV file
# 2. Generate access token
# 3. Fetch AEP schema class list looking for "Generic CJA Lookup" class
# 4. If it doesn't exist, create a "Generic CJA Lookup" schema class
# 5. Create a fieldgroup to match our csv lookup columns
# 6. Create a schema using the schema class and field group we just created
# 7. Create a dataset using our schema we just created
# 8. Convert the csv file into json format
# 9. Upload our josn data into our dataset

# Command line invoke:
# python your_script.py --file_path "/path/to/file.csv" --dataset_name "dataset_name" --creds "/path/to/credentials.json"

# Global Credentials
api_key = None
client_secret = None
org_id = None
technical_account_id = None
sandbox = None
private_key = None
access_token = None

# Generate Access Token
def get_access_token():
    expiration = int(time.time()) + 24*60*60
    claim = {
        "exp": expiration,
        "iss": org_id,
        "sub": technical_account_id,
        "https://ims-na1.adobelogin.com/s/ent_dataservices_sdk": True,
        "https://ims-na1.adobelogin.com/s/ent_cja_sdk": True,
        "aud": f"https://ims-na1.adobelogin.com/c/{api_key}"
    }
    jwt_token = jwt.encode(claim, private_key, algorithm='RS256')
    
    payload = MultipartEncoder({
        "client_id": api_key,
        "client_secret": client_secret,
        "jwt_token": jwt_token
    })
    
    response = requests.post(
        "https://ims-na1.adobelogin.com/ims/exchange/jwt",
        headers={"Content-Type": payload.content_type},
        data=payload
    )
    access_token = json.loads(response.text)['access_token']
    return access_token


# Detect whether a file is a SAINT classification file or a csv file
def detect_file_type(file_path):
    # Check the file extension
    _, ext = os.path.splitext(file_path)

    # Open the file to read the first line
    with open(file_path, 'r') as f:
        first_line = f.readline().strip()

    # If the extension is .csv and the first line doesn't start with '#', it's likely a CSV
    if ext.lower() == '.csv' and not first_line.startswith("## SC"):
        return "csv"
    # If the first line starts with '#', it's likely a SAINT file
    elif first_line.startswith("## SC"):
        return "saint"
    else:
        return "unknown"


# Read headers from a csv or SAINT file
def read_csv_headers(file_path, file_type):
    headers = None  # Initialize headers to None
    
    try:
        if file_type == "saint":        
            with open(file_path, 'r') as file:  # Use the dynamic file_path
                csv_reader = csv.reader(file, delimiter='\t')  # Assuming the delimiter is a tab character
                for row in csv_reader:
                    if row and not row[0].startswith("#"):  # Skip empty rows and rows starting with '#'
                        headers = row  # This should be your header row
                        break  # Exit the loop once the header is found
        
        elif file_type == "csv":
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)
        else:
            print("Invalid file_type argument. Use 'saint' or 'csv'.")
            
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return headers


# Sanitize csv headers so that they only contain letters, numbers, and underscores
def sanitize_strings(headers):
    single_string = False

    # Check if the input is a single string
    if isinstance(headers, str):
        headers = [headers]
        single_string = True
    
    sanitized_headers = []
    header_count = {}

    for header in headers:
        # Trim leading and trailing whitespaces
        header = header.strip()
        
        # Replace spaces with underscores
        header = header.replace(" ", "_")

        # Remove any character that is not a letter, number, or underscore
        header = ''.join(ch for ch in header if ch.isalnum() or ch == "_")

        # Lowercase everything
        header = header.lower()

        # If header starts with an underscore, prepend with "a"
        if header.startswith("_"):
            header = "a" + header

        # Ensure header uniqueness (append _n if not unique)
        if header in header_count:
            header_count[header] += 1
            header = f"{header}_{header_count[header]}"
        else:
            header_count[header] = 1

        sanitized_headers.append(header)

    # If input was a single string, return single string, otherwise return array
    if single_string:
        return sanitized_headers[0]
    else:
        return sanitized_headers


# Convert a csv or SAINT file into a json file and return the path to the json file
def csv_to_json(file_path, tenant_id, lookup_dataset_name, file_type):
    folder_path = os.path.dirname(file_path)
    json_file_name = os.path.splitext(os.path.basename(file_path))[0] + '.json'
    json_file_path = os.path.join(folder_path, json_file_name)
    
    try:
        with open(json_file_path, 'w') as json_file:
            if file_type == "csv":
                with open(file_path, 'r') as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    csv_reader.fieldnames = sanitize_strings(csv_reader.fieldnames)
                    for row in csv_reader:
                        write_to_json(json_file, row, tenant_id, lookup_dataset_name)
            
            elif file_type == "saint":
                version = None  # Initialize version to None
                with open(file_path, 'r') as saint_file:
                    csv_reader = csv.reader(saint_file, delimiter='\t')
                    headers = None
                    for row in csv_reader:
                        if row and row[0].startswith("##"):
                            if any("v:2.1" in cell for cell in row):
                                version = "v2.1"
                                print("Detected v2.1 SAINT file.")
                            elif any("v:2.0" in cell for cell in row):
                                version = "v2.0"
                                print("Detected v2.0 SAINT file.")
                        elif row:
                            if headers is None:
                                headers = row
                                headers = sanitize_strings(headers)
                            else:
                                row_dict = dict(zip(headers, row))
                                if version == "v2.1":
                                    # For v2.1, strip exterior quotes and replace double interior quotes with single quotes
                                    row_dict = {k: v.strip('"').replace('""', '"') for k, v in row_dict.items()}
                                # For v2.0 or if version is not specified, keep as is
                                write_to_json(json_file, row_dict, tenant_id, lookup_dataset_name)
            else:
                print("Invalid file_type. Use 'csv' or 'saint'.")
                return None
    
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
    return json_file_path


def write_to_json(json_file, row, tenant_id, lookup_dataset_name):
    # Assuming sanitize_strings is a function you've defined to sanitize strings
    sanitized_lookup_name = sanitize_strings(lookup_dataset_name)
    
    # Nest the row under the tenant ID and lookup dataset name (to avoid collisions)
    nested_row = {
        tenant_id: {
            sanitized_lookup_name: row
        }
    }
    
    # Write the nested row as a single line in the JSON file
    json_file.write(json.dumps(nested_row) + '\n')



# Fetch AEP schema class list searching for whatever is specified as the standard schema class name
def fetch_schema_class(standard_schema_class_name):
    headers = {
        "Content-Type": "application/json",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Accept": "application/vnd.adobe.xed-id+json"
    }
    
    response = requests.get(
        f"https://platform.adobe.io/data/foundation/schemaregistry/tenant/classes?limit=1&property=title=={standard_schema_class_name}",
        headers=headers
    )

    try:
        json_response = json.loads(response.text)
        results = json_response.get("results", [])
        
        if results: # if this schema class already exists (the array is not empty)
            schema_class_id = results[0].get("$id", None)
            print(f"Existing schema class found: {schema_class_id}")
            return schema_class_id  # Return the schema ID
        else:  # If results array is empty
            print("No existing lookup schema class found. Proceeding to create one...")
            return None  # Return None to indicate that no results were found

    except json.JSONDecodeError:
        return f"Failed to decode JSON. Raw response: {response.text}"

# Create Generic CJA Schema Class (used if it doesn't already exist)
def create_schema_class(standard_schema_class_name):
    headers = {
        "Content-Type": "application/json",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Accept": "application/vnd.adobe.xed-id+json"
    }
    
    payload = {
        "title": standard_schema_class_name,
        "description": "A generic lookup class for creating schemas for lookup datasets for CJA.",
        "imsOrg": org_id,
        "type": "object",
        "allOf": [
            {
                "$ref": "https://ns.adobe.com/xdm/data/record",
            }
        ]
    }

    response = requests.post(
        "https://platform.adobe.io/data/foundation/schemaregistry/tenant/classes",
        headers = headers,
        json = payload
    )

    try:
        json_response = json.loads(response.text)
        if response.status_code == 201:
            schema_class_id = json_response.get('$id', None)
            print(f"Created schema class ID: {schema_class_id}")
            return schema_class_id  # Return the schema class ID
        else:
            print(f"Failed to create schema class. Status code: {response.status_code}, Details: {json_response}")
            return None  # Return None to indicate failure
    except json.JSONDecodeError:
        print(f"Failed to decode JSON. Raw response: {response.text}")
        return None  # Return None to indicate an error

# Create a field group to create a schema
def create_field_group(schema_class_id, tenant_id, csv_headers, lookup_dataset_name):
    headers = {
        "Content-Type": "application/json",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Accept": "application/vnd.adobe.xed-id+json"
    }
    
    dynamic_properties = {}
    for header in csv_headers:
        dynamic_properties[header] = {
            "type": "string",
            "title": f"{header}"
        }

    payload = {
        "title": f"{lookup_dataset_name} field group",
        "description": "A field group created programatically for CJA.",
        "type": "object",
        "meta:intendedToExtend": [schema_class_id],
        "definitions": {
            "customFields": {
                "properties": {
                    f"{tenant_id}": {
                        "type": "object",
                        "properties": {
                            f"{sanitize_strings(lookup_dataset_name)}": {
                                "type": "object",
                                "properties": dynamic_properties
                            }
                        }
                    }
                }
            }
        },
        "allOf": [
            {
                "$ref": "#/definitions/customFields",
            }
        ]
    }

    response = requests.post(
        "https://platform.adobe.io/data/foundation/schemaregistry/tenant/fieldgroups",
        headers = headers,
        json = payload
    )
    
    try:
        json_response = json.loads(response.text)
        if response.status_code == 201:
            field_group_id = json_response.get('$id', None)
            print(f"Created field group ID: {field_group_id}")
            return field_group_id  # Return the field_group_id
        else:
            print(f"Failed to create field group. Status code: {response.status_code}, Details: {json_response}")
            return None  # Return None to indicate failure
    except json.JSONDecodeError:
        print(f"Failed to decode JSON. Raw response: {response.text}")
        return None  # Return None to indicate an error

# Create a schema using the generic schema class and field group created above
def create_schema(schema_class_id, field_group_id, lookup_dataset_name):
    headers = {
        "Content-Type": "application/json",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Accept": "application/vnd.adobe.xed-id+json"
    }
    
    payload = {
        "title": f"{lookup_dataset_name} schema",
        "description": "A lookup schema created programatically for CJA.",
        "type": "object",
        "allOf": [
            {
                "$ref": schema_class_id,
            },
            {
                "$ref": field_group_id
            }
        ]
    }

    response = requests.post(
        "https://platform.adobe.io/data/foundation/schemaregistry/tenant/schemas",
        headers = headers,
        json = payload
    )
    
    try:
        json_response = json.loads(response.text)
        if response.status_code == 201:
            schema_id = json_response.get('$id', None)
            print(f"Created schema ID: {schema_id}")
            return schema_id  # Return the schema_id
        else:
            print(f"Failed to create schema. Status code: {response.status_code}, Details: {json_response}")
            return None  # Return None to indicate failure
    except json.JSONDecodeError:
        print(f"Failed to decode JSON. Raw response: {response.text}")
        return None  # Return None to indicate an error

# Create a dataset using the schema created above
def create_dataset(schema_id, lookup_dataset_name):
    headers = {
        "Content-Type": "application/json",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "Accept": "application/vnd.adobe.xed-id+json"
    }
    
    payload = {
        "name": lookup_dataset_name,
        "description": "A dataset created programatically for CJA.",
        "schemaRef": {
            "id": schema_id,
            "contentType": "application/vnd.adobe.xed+json;version=1"
        }
    }

    response = requests.post(
        "https://platform.adobe.io/data/foundation/catalog/dataSets?requestDataSource=true",
        headers = headers,
        json = payload
    )
    
    try:
        json_response = json.loads(response.text)
        if response.status_code == 201:
            # Assuming the response is a list and we want the first item
            dataset_path = json_response[0] if json_response else None
            
            # Extract the alphanumeric code after "dataSets/"
            dataset_id = dataset_path.split("/dataSets/")[-1] if dataset_path else None
            
            print(f"Created dataset ID: {dataset_id}")
            return dataset_id  # Return the dataset_id
        else:
            print(f"Failed to create dataset. Status code: {response.status_code}, Details: {json_response}")
            return None  # Return None to indicate failure
    except json.JSONDecodeError:
        print(f"Failed to decode JSON. Raw response: {response.text}")
        return None  # Return None to indicate an error



# Create a batch in the dataset we created earlier
def create_batch(dataset_id):
    headers = {
        "Content-Type": "application/json",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key
    }

    payload = {
        "datasetId": dataset_id,
        "inputFormat": {
            "format": "json"
        }
    }

    response = requests.post(
        "https://platform.adobe.io/data/foundation/import/batches",
        headers = headers,
        json = payload
    )
    
    try:
        json_response = json.loads(response.text)
        if response.status_code == 201:
            batch_id = json_response.get('id', None)
            print(f"Created batch ID: {batch_id}")
            return batch_id  # Return the batch_id
        else:
            print(f"Failed to create dataset batch. Status code: {response.status_code}, Details: {json_response}")
            return None  # Return None to indicate failure
    except json.JSONDecodeError:
        print(f"Failed to decode JSON. Raw response: {response.text}")
        return None  # Return None to indicate an error

# Upload json file to the new batch
def add_json_to_batch(batch_id, dataset_id, json_file_path):
    headers = {
        "content-type": "application/octet-stream",
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key
    }

    with open(json_file_path, "rb") as f:
        data_binary = f.read()

    print("Uploading json to dataset...")

    response = requests.put(
        f"https://platform.adobe.io/data/foundation/import/batches/{batch_id}/datasets/{dataset_id}/files/lookup_json_data.json",
        headers = headers,
        data = data_binary
    )
    
    if response.status_code == 200:
        print(f"Successfully loaded json to batch {batch_id}.")
        return None
    else:
        print(f"Failed to upload json to batch. Status code: {response.status_code}")
        return None  # Return None to indicate failure

# Close the batch when we've written to it
def close_batch(batch_id):

    headers = {
        "x-gw-ims-org-id": org_id,
        "x-sandbox-name": sandbox,
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key
    }

    response = requests.post(
        f"https://platform.adobe.io/data/foundation/import/batches/{batch_id}?action=COMPLETE",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"Successfully closed batch {batch_id}.")
        return None
    else:
        print(f"Failed to close batch. Status code: {response.status_code}")
        return None  # Return None to indicate failure

# Main function
def main(args):
    
    # Grab command line arguments
    file_path = args.file_path
    lookup_dataset_name = args.dataset_name
    creds_path = args.creds_file

    # Set global credential variables for functions to use
    global api_key
    global client_secret
    global org_id
    global technical_account_id
    global sandbox
    global private_key
    global access_token
    
    # Open the credentials file supplied by user
    with open(creds_path, 'r') as f:
        config = json.load(f)

    # Set global credentials variables from file
    api_key = config['API_KEY']
    client_secret = config['CLIENT_SECRET']
    org_id = config['ORG_ID']
    technical_account_id = config['TECHNICAL_ACCOUNT_ID']
    sandbox = config['SANDBOX']
    with open(config['PRIVATE_KEY'], 'r') as f:
        private_key = f.read()

    # Fetch access token
    access_token = get_access_token()

    # Check if the file is a SAINT file or a CSV file
    file_type = detect_file_type(file_path)

    if file_type == "saint":
        print("SAINT classification file detected.")
    elif file_type == "csv":
        print("csv file detected.")
    else:
        print("Unrecognized file format detected (not csv or SAINT). Exiting...")
        return

    # Read CSV file headers
    csv_headers = read_csv_headers(file_path, file_type)

    # Sanitize the csv headers to be acceptable as AEP schema fields
    csv_headers = sanitize_strings(csv_headers)
    print(f"Read {file_type} file. Headers are: {csv_headers}")
    
    # Check for existing schema class called "CJA Generic Lookup Class", if nonexistant, create one
    standard_schema_class_name = "CJA Generic Lookup Class"
    schema_class_id = fetch_schema_class(standard_schema_class_name)
    if not schema_class_id:
        schema_class_id = create_schema_class(standard_schema_class_name)

    # Extract the tenant ID for use later
    schema_class_id_parts = schema_class_id.split("/")
    tenant_id = "_" + schema_class_id_parts[schema_class_id_parts.index("ns.adobe.com") + 1]

    # Create field group
    field_group_id = create_field_group(schema_class_id, tenant_id, csv_headers, lookup_dataset_name)

    # Create schema
    schema_id = create_schema(schema_class_id, field_group_id, lookup_dataset_name)

    # Create dataset
    dataset_id = create_dataset(schema_id, lookup_dataset_name)

    # Read the CSV file and convert to a JSON file in same folder location
    json_file_path = csv_to_json(file_path, tenant_id, lookup_dataset_name, file_type)

    # Open a dataset batch
    batch_id = create_batch(dataset_id)

    # Add json file to batch
    add_json_to_batch(batch_id, dataset_id, json_file_path)

    # Close the batch when done
    close_batch(batch_id)

    # Delete the json file that was created
    if os.path.exists(json_file_path):
        os.remove(json_file_path)
        print(f"The temporary file {json_file_path} has been deleted.")
    else:
        print(f"The temporary file {json_file_path} does not exist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='This script will accept a csv or SAINT classification file using the "file_path" argument and convert it into a dataset in AEP named by the "dataset_name" argment.')
    parser.add_argument('--file_path', type=str, help='Path to the CSV or SAINT classification file', required=True)
    parser.add_argument('--dataset_name', type=str, help='Name of the lookup dataset you want in AEP', required=True)
    parser.add_argument('--creds_file', type=str, help='Path to the JSON file containing your API credentials', required=True)
    
    args = parser.parse_args()
    main(args)