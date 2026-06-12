import asyncio
import sys

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

URL = "http://www.results.exams.gov.lk/viewresults.htm"
EXCEL_FILE = "indexes.xlsx"
INDEX_COLUMN = "index_number"
OUTPUT_FILE = "results.csv"
MAX_CONCURRENT_REQUESTS = 50

PAYLOAD = {
    "examSessionId": "689",
    "year": "2025",
    "typeTitle": "Open Competitive Examination for Recruitment to The Post of Grade III Postal Service Officer of Non-Technical/Technical Officer Category - Supervisory Management Assistant of The Department of Posts, Sri Lanka - 2025",
    "isAddIndexNeeded": "N",
    "additionalFieldName": "",
    "comment": "",
}


def load_index_numbers(path: str) -> list[str]:
    df = pd.read_excel(path, dtype=str)

    if INDEX_COLUMN in df.columns:
        column = INDEX_COLUMN
    else:
        column = df.columns[0]

    indexes = df[column].dropna().astype(str).str.strip()
    return [idx for idx in indexes if idx]


def parse_result_html(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
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

    return name, result


async def fetch_result(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    index_number: str,
) -> dict:
    payload = {**PAYLOAD, "indexNumber": index_number}

    async with semaphore:
        try:
            async with session.post(URL, data=payload, timeout=aiohttp.ClientTimeout(total=20)) as response:
                response.raise_for_status()
                html = await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            return {
                "index_number": index_number,
                "name": None,
                "result": None,
                "error": str(exc),
            }

    name, result = parse_result_html(html)
    return {
        "index_number": index_number,
        "name": name,
        "result": result,
        "error": None,
    }


async def fetch_all(index_numbers: list[str]) -> list[dict]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    lock = asyncio.Lock()

    async with aiohttp.ClientSession() as session:

        async def fetch_with_progress(index_number: str) -> dict:
            row = await fetch_result(session, semaphore, index_number)

            async with lock:
                if row["name"] is not None or row["result"] is not None:
                    print(f"Index: {index_number}")
                    if row["name"] is not None:
                        print(f"  Name   : {row['name']}")
                    if row["result"] is not None:
                        print(f"  Result : {row['result']}")
                    print()

            return row

        return await asyncio.gather(
            *[fetch_with_progress(index_number) for index_number in index_numbers]
        )


def main() -> None:
    excel_path = sys.argv[1] if len(sys.argv) > 1 else EXCEL_FILE
    index_numbers = load_index_numbers(excel_path)

    if not index_numbers:
        print(f"No index numbers found in {excel_path}")
        sys.exit(1)

    print(f"Processing {len(index_numbers)} index number(s) from {excel_path}\n")

    results = asyncio.run(fetch_all(index_numbers))

    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
    print(f"Saved results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
