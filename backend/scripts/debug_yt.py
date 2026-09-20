"""Quick debug script to test YouTube transcript fetching strategies."""
import httpx
import re
import json

VIDEO_ID = "vFrkf8WyJVc"

print("=" * 60)
print(f"Testing video: {VIDEO_ID}")
print("=" * 60)

# Strategy 1: ANDROID client
print("\n--- Strategy 1: InnerTube ANDROID client ---")
try:
    r = httpx.post(
        "https://www.youtube.com/youtubei/v1/player",
        json={
            "context": {
                "client": {
                    "hl": "en",
                    "gl": "US",
                    "clientName": "ANDROID",
                    "clientVersion": "19.09.37",
                    "androidSdkVersion": 30,
                }
            },
            "videoId": VIDEO_ID,
        },
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.09.37",
        },
        timeout=15,
    )
    d = r.json()
    status = d.get("playabilityStatus", {}).get("status")
    reason = d.get("playabilityStatus", {}).get("reason", "N/A")
    has_caps = bool(d.get("captions", {}))
    print(f"  Status: {status}")
    print(f"  Reason: {reason}")
    print(f"  Has captions: {has_caps}")
    if has_caps:
        tracks = d["captions"].get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
        for t in tracks:
            print(f"    Track: {t.get('languageCode')} | kind={t.get('kind','manual')} | url={t.get('baseUrl','')[:80]}...")
except Exception as e:
    print(f"  Error: {e}")

# Strategy 2: WEB client with proper cookies
print("\n--- Strategy 2: InnerTube WEB with consent ---")
try:
    r = httpx.post(
        "https://www.youtube.com/youtubei/v1/player",
        json={
            "context": {
                "client": {
                    "hl": "en",
                    "gl": "US",
                    "clientName": "WEB",
                    "clientVersion": "2.20250420.01.00",
                }
            },
            "videoId": VIDEO_ID,
            "contentCheckOk": True,
            "racyCheckOk": True,
        },
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Origin": "https://www.youtube.com",
            "Referer": f"https://www.youtube.com/watch?v={VIDEO_ID}",
        },
        timeout=15,
    )
    d = r.json()
    status = d.get("playabilityStatus", {}).get("status")
    reason = d.get("playabilityStatus", {}).get("reason", "N/A")
    has_caps = bool(d.get("captions", {}))
    print(f"  Status: {status}")
    print(f"  Reason: {reason}")
    print(f"  Has captions: {has_caps}")
    if has_caps:
        tracks = d["captions"].get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
        for t in tracks:
            print(f"    Track: {t.get('languageCode')} | kind={t.get('kind','manual')} | url={t.get('baseUrl','')[:80]}...")
except Exception as e:
    print(f"  Error: {e}")

# Strategy 3: Scrape the watch page for embedded player data
print("\n--- Strategy 3: Watch page scrape ---")
try:
    r = httpx.get(
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "CONSENT=PENDING+987; SOCS=CAESEwgDEgk2MjQwODE5MjAaAmVuIAEaBgiA_OC8Bg",
        },
        follow_redirects=True,
        timeout=15,
    )
    print(f"  HTTP Status: {r.status_code}")
    
    # Look for captionTracks in the page
    ct_match = re.search(r'"captionTracks":(\[.*?\])', r.text)
    if ct_match:
        tracks = json.loads(ct_match.group(1))
        print(f"  Found {len(tracks)} caption tracks!")
        for t in tracks:
            lang = t.get("languageCode", "?")
            kind = t.get("kind", "manual")
            base_url = t.get("baseUrl", "")
            print(f"    Track: {lang} | kind={kind}")
            
            # Try downloading the first track
            if base_url:
                sep = "&" if "?" in base_url else "?"
                dl_url = f"{base_url}{sep}fmt=srv3"
                dr = httpx.get(dl_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }, timeout=15)
                print(f"    Download status: {dr.status_code}")
                if dr.status_code == 200 and dr.text.strip():
                    print(f"    Content length: {len(dr.text)} chars")
                    print(f"    First 200 chars: {dr.text[:200]}")
                else:
                    print(f"    Empty or failed response")
    else:
        print("  No captionTracks found in page")
        
        # Check playability from page
        ps_match = re.search(r'"playabilityStatus":\{"status":"(\w+)"', r.text)
        if ps_match:
            print(f"  Page playability: {ps_match.group(1)}")
        
        # Check for any sign the video exists
        title_match = re.search(r'"title":"(.*?)"', r.text)
        if title_match:
            print(f"  Video title found: {title_match.group(1)[:80]}")
            
except Exception as e:
    print(f"  Error: {e}")

# Strategy 4: Direct timedtext API
print("\n--- Strategy 4: Direct timedtext endpoint ---")
try:
    for kind_param in ["", "asr"]:
        params = {"v": VIDEO_ID, "lang": "en", "fmt": "srv3"}
        if kind_param:
            params["kind"] = kind_param
        r = httpx.get(
            "https://www.youtube.com/api/timedtext",
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=15,
        )
        label = f"kind={kind_param or 'manual'}"
        print(f"  {label}: HTTP {r.status_code}, content_length={len(r.text)}")
        if r.text.strip():
            print(f"    First 200 chars: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 60)
print("Done.")
