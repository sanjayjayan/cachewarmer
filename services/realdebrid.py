import requests

BASE_URL = "https://api.real-debrid.com/rest/1.0"


def test_connection(api_key: str) -> bool:
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(
            f"{BASE_URL}/user",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            return True
        else:
            print("RD Error:", response.text)
            return False

    except Exception as e:
        print("RD Connection Error:", e)
        return False

def is_cached(api_key: str, info_hash: str) -> bool | None:
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    url = f"{BASE_URL}/torrents/instantAvailability/{info_hash}"

    try:
        response = requests.get(url, headers=headers, timeout=20)
        data = response.json()

        return info_hash in data and len(data[info_hash]) > 0

    except Exception as e:
        print("RD cache check error:", e)
        return None   # UNKNOWN


def add_magnet(api_key: str, magnet: str) -> bool:
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "magnet": magnet
    }

    try:
        response = requests.post(
            f"{BASE_URL}/torrents/addMagnet",
            headers=headers,
            data=data,
            timeout=10
        )

        if response.status_code == 201:
            return True
        else:
            print("RD add magnet error:", response.text)
            return False

    except Exception as e:
        print("RD add magnet exception:", e)
        return False
