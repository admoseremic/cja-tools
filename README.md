# cja-tools
A repository for tools that make using CJA easier!


# Setup:
To make things work, you'll need to set up your API credentials. To set that up, just follow Ben Woodard's guide here: https://cran.r-project.org/web/packages/cjar/readme/README.html (specifically the "Create an Adobe Console API Project" and ignore the rest)

Once you've followed the steps above, you'll need to create a credentials json file (e.g. "credentials.json"). It should contain this text (with your own values pasted in of course):

```
{
    "API_KEY":"somelettersandnumbers",
    "CLIENT_SECRET":"p8e-somelettersandnumbers",
    "ORG_ID":"somelettersandnumbers@AdobeOrg",
    "TECHNICAL_ACCOUNT_ID":"somelettersandnumbers@techacct.adobe.com",
    "SANDBOX": "prod",
    "PRIVATE_KEY": "/path/to/your/mc_private.key"
}
```

Once you've got that set up, you can use the tools as follows:

# lookup_creator.py:
This tool accepts a file which can be either a csv or SAINT classification file (the script will auto-detect which it is) and automatically do the following:
1. Create a generic CJA lookup schema class if one does not exist already
2. Create a field group based on your file headers
3. Create a schema from your csv headers
4. Create a dataset from this schema
5. Convert your csv or SAINT file into json format and automatically upload it to the AEP dataset

Currently, everything is treated as a string (no support yet for numerics or dates or other field types). If the script detects SAINT v2.1 is used, it will get rid of all the quotations on the outside of the values and replace "" with " to mimic how SAINT v2.1 files work in Adobe Analytics.

Also, I've only tested this on a Mac - not sure if it will work on a PC. Example command line command below:

python lookup_creator.py --file_path "/path/to/file.csv" --dataset_name "aep_dataset_name" --creds "/path/to/credentials.json"