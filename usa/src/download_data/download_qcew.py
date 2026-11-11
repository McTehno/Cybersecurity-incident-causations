from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "raw" / "bls" / "qcew"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for year in range(2014, 2026):
    filename = f"{year}_annual_by_area.zip"
    url = (
        f"https://data.bls.gov/cew/data/files/"
        f"{year}/csv/{filename}"
    )
    destination = OUTPUT_DIR / filename

    if destination.exists():
        print(f"SKIP: {filename}")
        continue

    print(f"Downloading {year}...")

    try:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()

            with destination.open("wb") as file:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        file.write(chunk)

        print(f"OK: {filename}")

    except requests.RequestException as error:
        destination.unlink(missing_ok=True)
        print(f"ERROR {year}: {error}")
