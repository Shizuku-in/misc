import os
import requests

API_URL = "https://api.vndb.org/kana/vn"
TOKEN = "" # https://vndb.org/u/tokens
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

def fetch_data(vnid):
    query = {
        "filters": ["id", "=", vnid],
        "fields": "titles{lang,title,latin,official},olang,released,developers{name},description,image.url,screenshots{url,sexual,violence}"
    }
    res = requests.post(API_URL, headers=HEADERS, json=query)
    res.raise_for_status()
    data = res.json().get("results")
    if not data:
        raise ValueError(f"No data found for {vnid}")
    return data[0]

def content(data):
    jp_title = next((t["title"] for t in data["titles"] if t["lang"] == "ja" and t.get("official")), "Unknown")
    roman_title = next((t.get("latin") for t in data["titles"] if t["lang"] == "ja"), "Unknown")
    date = data.get("released", "Unknown").replace("-", "/")
    devs = ", ".join(d["name"] for d in data.get("developers", [])) or "Unknown"
    desc = data.get("description", "No description available.")
    cover = data.get("image", {}).get("url", "No cover available.")
    screenshots = "\n".join(
        f"[img]{s['url']}[/img]" for s in data.get("screenshots", [])
        if s.get("sexual", 0) <= 1 and s.get("violence", 0) <= 1
    ) or "No screenshots available."

    return f"""[img]{cover}[/img]

[b]Title:[/b] {jp_title}
[b]Romanized title:[/b] {roman_title}
[b]Release date:[/b] {date}
[b]Developer:[/b] {devs}
[b]Description:[/b]
{desc}
[b]Screenshots:[/b] {screenshots}
""", jp_title, date

def save_file(bbcode, title, date, out_dir):
    year, month, day = (date.split("/") + ["00", "00"])[:3]
    safe_title = "".join(c if c.isalnum() or c in " _-[]" else "_" for c in (title or "Unknown"))
    fname = f"[{year}{month}{day}] {safe_title}.txt"

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(bbcode)
    print(f"Generated: {path}")

def main():
    vnids = input("Enter VNDB IDs (comma-separated): ").split(",")
    out_dir = "D:/" # output dir

    for vnid in map(str.strip, vnids):
        try:
            data = fetch_data(vnid)
            bbcode, title, date = content(data)
            save_file(bbcode, title, date, out_dir)
        except Exception as e:
            print(f"Error processing {vnid}: {e}")

if __name__ == "__main__":
    main()
