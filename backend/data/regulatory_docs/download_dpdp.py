"""
Script to download the DPDP Act 2023 PDF from the official MeitY source.
Run this once to populate the regulatory_docs folder.
"""
import urllib.request
import os

DOCS = [
    {
        "url": "https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf",
        "filename": "dpdp_act_2023.pdf",
        "description": "Digital Personal Data Protection Act 2023"
    }
]

def download():
    folder = os.path.dirname(os.path.abspath(__file__))
    for doc in DOCS:
        dest = os.path.join(folder, doc["filename"])
        if os.path.exists(dest):
            print(f"✓ Already exists: {doc['filename']}")
            continue
        print(f"Downloading {doc['description']}...")
        urllib.request.urlretrieve(doc["url"], dest)
        print(f"✓ Saved: {doc['filename']}")

if __name__ == "__main__":
    download()