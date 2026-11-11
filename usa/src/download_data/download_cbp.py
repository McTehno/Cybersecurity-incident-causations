
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zipfile import ZipFile, BadZipFile
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "raw" / "census" / "cbp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = (
    "https://www2.census.gov/"
    "programs-surveys/cbp/datasets"
)

START_YEAR = 2014
END_YEAR = 2023

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/zip,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def valid_zip(path):
    try:
        with ZipFile(path) as archive:
            return bool(archive.namelist()) and archive.testzip() is None
    except (BadZipFile, OSError):
        return False


def download_cbp(year):
    filename = f"cbp{year % 100:02d}st.zip"
    url = f"{BASE_URL}/{year}/{filename}"

    destination = OUTPUT_DIR / filename
    temporary = OUTPUT_DIR / f"{filename}.part"

    if destination.exists() and valid_zip(destination):
        print(f"SKIP {year}: already downloaded")
        return True

    destination.unlink(missing_ok=True)
    temporary.unlink(missing_ok=True)

    print(f"Downloading {year}: {url}")

    request = Request(url, headers=HEADERS)

    try:
        with urlopen(request, timeout=120) as response:
            with temporary.open("wb") as file:
                shutil.copyfileobj(response, file)

        if not valid_zip(temporary):
            raise ValueError("Invalid ZIP file")

        temporary.replace(destination)

        size_mb = destination.stat().st_size / (1024 * 1024)
        print(f"OK {year}: {size_mb:.2f} MB")

        return True

    except (HTTPError, URLError, OSError, ValueError) as error:
        print(f"ERROR {year}: {error}")
        return False

    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    results = {}

    for year in range(START_YEAR, END_YEAR + 1):
        results[year] = download_cbp(year)
        time.sleep(1)

    successful = sum(results.values())
    failed = [year for year, ok in results.items() if not ok]

    print(f"\nDownloaded/verified: {successful}/{len(results)}")
    print(f"Failed years: {failed}")
