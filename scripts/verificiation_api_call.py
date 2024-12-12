import asyncio
import hashlib
import json
from typing import Dict
import copy

import requests

API_KEY = "asdasd-asd1234"


async def main():
    url = "http://127.0.0.1:5000/v1/verified/chat/completions"
    request_body = {
        "messages": [
            {"content": "You are a helpful assistant.", "role": "system"},
            {"content": "Hello!", "role": "user"},
        ],
        "model": "gpt-4o",
    }
    response = requests.post(
        url, headers={"Authorization": f"Bearer {API_KEY}"}, json=request_body
    )
    response_json = response.json()
    print("Got response JSON")
    print(response_json)

    formatted_response_json = copy.deepcopy(response_json)
    extra_fields = ["hash", "signature", "attestation"]
    for field in extra_fields:
        formatted_response_json.pop(field, None)

    expected_hash = _hash_request_and_response(request_body, formatted_response_json)
    expected_hash_str = expected_hash.hex()
    print(f"Expected response hash: {expected_hash_str}")
    print(f"Actual response hash: {response_json['hash']}")
    print(f"Equal: {expected_hash_str == response_json['hash']}")
    # TODO: verify signature


def _hash_request_and_response(request_body: Dict, response: Dict) -> bytes:
    combined_str = f"{json.dumps(request_body, sort_keys=True)}{json.dumps(response, sort_keys=True)}"
    return hashlib.sha256(combined_str.encode("utf-8")).digest()


if __name__ == "__main__":
    asyncio.run(main())
