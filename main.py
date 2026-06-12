import requests
from bs4 import BeautifulSoup

INDEX_NUMBER = "96021234"

url = "http://www.results.exams.gov.lk/viewresults.htm"

payload = {
    "examSessionId": "689",
    "year": "2025",
    "typeTitle": "Open Competitive Examination for Recruitment to The Post of Grade III Postal Service Officer of Non-Technical/Technical Officer Category - Supervisory Management Assistant of The Department of Posts, Sri Lanka - 2025",
    "isAddIndexNeeded": "N",
    "additionalFieldName": "",
    "comment": "",
    "indexNumber": INDEX_NUMBER,
}

r = requests.post(url, data=payload, timeout=20)

soup = BeautifulSoup(r.text, "html.parser")

# Example extraction - adjust selectors after inspecting the result page
name = None
result = None

for row in soup.find_all("tr"):
    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]

    if len(cells) >= 2:
        label = cells[0].lower()

        if "name" in label:
            name = cells[1]

        if "result" in label:
            result = cells[1]

print(f"Name   : {name}")
print(f"Result : {result}")