"""Manual smoke test for the Supadata transcript API.

Not a pytest test (no assertions) — run directly with `python backend/scripts/test_supadata.py`
to sanity-check that SUPADATA_API_KEY is valid and the API is reachable. Hits the real
Supadata API and will incur usage against your quota.
"""
import json
import os
import sys

import requests

VIDEO_ID = "jEnxvZXzo0E"


def main() -> None:
    api_key = os.environ.get("SUPADATA_API_KEY")
    if not api_key:
        print("SUPADATA_API_KEY is not set in the environment.", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={VIDEO_ID}"
    headers = {"x-api-key": api_key}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print("Status:", response.status_code)
        try:
            print(json.dumps(response.json(), indent=2)[:500])
        except ValueError:
            print(response.text)
    except requests.RequestException as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
