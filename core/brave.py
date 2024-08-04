import random
import os
import requests
import time
from pprint import pprint


def brave_search(search_string):
    params = {"q": search_string, "extra_snippets": "1"}
    headers = {
        "X-Subscription-Token": os.environ.get("BRAVE_API_KEY"),
        "Accept": "application/json",
    }
    max_retries = 5
    retries = 0
    delay = 1
    while True:
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params=params,
                headers=headers,
                timeout=10,
            )
            break
        except requests.RequestException as e:
            if isinstance(e, requests.HTTPError) and e.response.status_code == 429:
                delay = delay * 2 + random.choice([1, 2, 3, 4])

                time.sleep(delay)
                retries += 1
                if retries >= max_retries:
                    return []
            else:
                raise
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []

    try:
        data = response.json()
        pprint(data)
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(response.text)
        return []

    results = []

    for result in data["web"]["results"]:
        url = result.get("url")
        title = result.get("title")
        description = result.get("description")
        extra_snippets = result.get("extra_snippets", [])

        result_dict = {
            "url": url,
            "title": title,
            "description": description,
            "extra_snippets": extra_snippets,
        }

        results.append(result_dict)

    return results


def brave_search_str(query):
    search = brave_search(query)
    res = ""
    for r in search:
        res += f"\n\n# {r['title']}\n"
        res += r["description"]
        res += "\n" + "\n".join(r["extra_snippets"])
        res += f"\nsource: {r['url']}"
    return res


# print(brave_search_str("Who is runing for president in 2024"))
