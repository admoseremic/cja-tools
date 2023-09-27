# cja-tools
A repository for tools that make using CJA easier!


#Setup:
To make things work, you'll need to set up your API credentials. To set that up, just follow Ben Woodard's guide here: https://cran.r-project.org/web/packages/cjar/readme/README.html (specifically the "Create an Adobe Console API Project" and ignore the rest)

Once you've followed the steps above, you'll need to create a credentials json file (e.g. "credentials.json"). It should contain this text (with your own values pasted in of course):

{
    "API_KEY":"somelettersandnumbers",
    "CLIENT_SECRET":"p8e-somelettersandnumbers",
    "ORG_ID":"somelettersandnumbers@AdobeOrg",
    "TECHNICAL_ACCOUNT_ID":"somelettersandnumbers@techacct.adobe.com",
    "SANDBOX": "prod",
    "PRIVATE_KEY": "/path/to/your/mc_private.key"
}

Once you've got that set up, you can use the tools as follows:

#lookup_creator:

Command line invoke:
python lookup_creator.py --file_path "/path/to/file.csv" --dataset_name "aep_dataset_name" --creds "/path/to/credentials.json"