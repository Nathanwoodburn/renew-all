# Get env
import os
import sys
from dotenv import load_dotenv
import requests
import json
import subprocess

load_dotenv()
api_key = os.getenv("API_KEY")
account = os.getenv("ACCOUNT")
password = os.getenv("PASSWORD")
renewType = os.getenv("RENEW_TYPE")
expireThreshold = 365
if os.getenv("RENEW_DAYS") is not None:
    try:
        expireThreshold = int(os.getenv("RENEW_DAYS"))
    except:
        print("Invalid RENEW_DAYS value")
        sys.exit()

def escape_json_for_shell(json_data):
    # Convert Python object to JSON string
    json_string = json.dumps(json_data)
    
    # Escape special characters for shell usage
    escaped_string = json_string.replace('\\', '\\\\')
    escaped_string = escaped_string.replace('"', '\\"')
    escaped_string = escaped_string.replace("'", "\\'")
    escaped_string = escaped_string.replace('\n', '\\n')
    escaped_string = escaped_string.replace('\r', '\\r')
    escaped_string = escaped_string.replace('\t', '\\t')
    escaped_string = escaped_string.replace(' ', '\\ ')
    
    return escaped_string


# Get the domain list
domainslist = []
domainRequest = requests.get(f'http://x:{api_key}@127.0.0.1:12039/wallet/{account}/name?own=true')
if renewType == "all":
    for domain in domainRequest.json():
        domainslist.append(domain["name"])
elif renewType == "expiring":
    for domain in domainRequest.json():
        if domain["stats"]["daysUntilExpire"] < expireThreshold:
            domainslist.append(domain["name"])

    
# Verify the domain list
print("Renewing the following domains:")
if len(domainslist) == 0:
    print("No domains to renew")
    sys.exit()


for domain in domainslist:
    print(domain, end=" ")

print("\nDo you want to edit the list? (y/n) ", end="")
editList = input()
if editList == "y":
    while True:
        print("Do you want to add or remove a domain or done? (a/r/d) ", end="")
        action = input()
        if action == "a":
            print("Enter the domain you want to add:")
            domain = input()
            domainslist.append(domain)
        elif action == "r":
            print("Enter the domain you want to remove:")
            domain = input()
            domainslist.remove(domain)
        else:
            break
    print("Renewing the following domains:")
    for domain in domainslist:
        print(domain, end=" ")


# Create the batch
batch = []

for domain in domainslist:
    batch.append(f'["RENEW", "{domain}"]')


batchTX = "[" + ", ".join(batch) + "]"
responseContent = f'{{"method": "createbatch","params":[ {batchTX} ]}}'
print("Creating batch...")
response = requests.post(f'http://x:{api_key}@127.0.0.1:12039', data=responseContent)
if response.status_code != 200:
    print("Failed to create batch")
    print(response.json())
    sys.exit()

batch = response.json()
# Verify the batch
print("Verifying batch...")
if batch["error"]:
    if batch["error"] != "":
        print("Failed to verify batch")
        print(batch["error"]["message"])
        sys.exit()

batch = json.dumps(batch)
domainslist = json.dumps(domainslist)

# Send the batch
print("Sending batch to hsd...")

command = [
    "hsd-ledger/bin/hsd-ledger",
    "sendraw",
    batch,
    domainslist,
    "--api-key",
    api_key,
    "-w",
    account
]
try:
    output = subprocess.run(command, capture_output=True, text=True)
    print(output.stdout)
    print(output.stderr)

    # Try to extract the txid
    txid = output.stdout.split("Submitted TXID: ")[1].split("\n")[0]
    print(f"https://niami.io/tx/{txid}")

except Exception as e:
    print(f"Error running command: {str(e)}")
    sys.exit()


