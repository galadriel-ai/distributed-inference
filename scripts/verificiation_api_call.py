import base58
import asyncio
import copy
import hashlib
import json
from typing import Dict

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

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
    extra_fields = ["hash", "signature", "attestation", "public_key"]
    for field in extra_fields:
        formatted_response_json.pop(field, None)

    expected_hash = _hash_request_and_response(request_body, formatted_response_json)
    expected_hash_str = expected_hash.hex()
    print(f"Expected response hash: {expected_hash_str}")
    print(f"Actual response hash: {response_json['hash']}")
    print(f"Equal: {expected_hash_str == response_json['hash']}")

    print(f"Verifying signature: {response_json['signature']}")
    print(f"Public key: {response_json['public_key']}")
    is_signature_valid = _verify_signature(
        response_json['public_key'],
        response_json['signature'],
        response_json['hash'],
    )
    print(f"Is signature valid: {is_signature_valid}")


def _hash_request_and_response(request_body: Dict, response: Dict) -> bytes:
    combined_str = f"{json.dumps(request_body, sort_keys=True)}{json.dumps(response, sort_keys=True)}"
    return hashlib.sha256(combined_str.encode("utf-8")).digest()


def _verify_signature(public_key: str, signature: str, hash_value: str) -> bool:
    try:
        public_key_bytes = base58.b58decode(public_key)
        signature_bytes = bytes.fromhex(signature)
        hash_value_bytes = bytes.fromhex(hash_value)

        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, hash_value_bytes)
        return True
    except (InvalidSignature, ValueError) as e:
        return False


if __name__ == "__main__":
    asyncio.run(main())
