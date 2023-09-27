# CJA Tools
A collection of utilities designed to simplify your experience with Customer Journey Analytics (CJA).

## Prerequisites
Before you can use these tools, you'll need to set up your API credentials.

### Setting Up API Credentials
1. Follow Ben Woodard's guide on [how to create an Adobe Console API Project](https://cran.r-project.org/web/packages/cjar/readme/README.html). **Note**: You only need to follow the "Create an Adobe Console API Project" section; you can ignore the rest.
2. Create a JSON file for your credentials, for example, `credentials.json`. Populate it with your own values:

```json
{
    "API_KEY": "your-api-key",
    "CLIENT_SECRET": "your-client-secret",
    "ORG_ID": "your-org-id@AdobeOrg",
    "TECHNICAL_ACCOUNT_ID": "your-technical-account-id@techacct.adobe.com",
    "SANDBOX": "prod",
    "PRIVATE_KEY": "/path/to/your/mc_private.key"
}
```

## Usage

### `lookup_creator.py`
This script automates several tasks related to CJA. It accepts either a CSV or a SAINT classification file (auto-detection enabled) and performs the following actions:

1. Creates a generic CJA lookup schema class if one doesn't already exist.
2. Generates a field group based on the headers in your file.
3. Constructs a schema using the headers from your CSV file.
4. Creates a dataset using the newly created schema.
5. Converts your CSV or SAINT file into JSON format and uploads it to the AEP dataset.

#### Limitations
- All fields are treated as strings; no support for numerics, dates, or other data types.
- Tested only on macOS; compatibility with Windows is unconfirmed.

#### Example Command
```bash
python lookup_creator.py --file_path "/path/to/file.csv" --dataset_name "aep_dataset_name" --creds "/path/to/credentials.json"
```
