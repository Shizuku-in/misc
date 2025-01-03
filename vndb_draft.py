import requests
import os
from datetime import datetime

API_URL = "https://api.vndb.org/kana/vn"

def get_vn_info(vndbid):
    payload = {
        "filters": ["id", "=", vndbid],
        "fields": "id, titles{title,lang,main}, released, description, tags{name}",
        "results": 1
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]
    return None

def create_markdown(vn_data):
    title_data = next(
        (title for title in vn_data["titles"] if title["lang"] == "ja" and title["main"]), 
        vn_data["titles"][0]
    )
    title = title_data["title"]
    released = vn_data.get("released", "TBA")
    description = vn_data.get("description", "")
    tags = ", ".join(tag["name"] for tag in vn_data.get("tags", []))
    
    if released != "TBA":
        released_date = datetime.strptime(released, "%Y-%m-%d")
        file_date = released_date.strftime("%y%m%d")
        display_date = released_date.strftime("%Y/%m/%d")
    else:
        file_date = "TBA"
        display_date = "TBA"

    file_name = f"[{file_date}] {title}.md"
    vndb_link = f"https://vndb.org/{vn_data['id']}"

    markdown_content = f"""\
Title: [{title}]({vndb_link})
Release date: {display_date}
Description: {description}
Tags: {tags}
"""
    with open(file_name, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)
    print(f"Generated: {file_name}")

def main():
    vndbids = input("Enter VNDB IDs separated by commas (e.g. v3770, v4, v9): ").split(", ")
    vndbids = [vid.strip() for vid in vndbids if vid.strip()]

    if not vndbids:
        print("No VNDB IDs provided. Exiting.")
        return

    for vndbid in vndbids:
        vn_data = get_vn_info(vndbid)
        if vn_data:
            create_markdown(vn_data)
        else:
            print(f"VNDB ID {vndbid} not found.")

if __name__ == "__main__":
    main()
