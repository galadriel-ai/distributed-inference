from distributedinference.service.middleware.client_version_validation_middleware import (
    Client,
)


async def test_client():
    test_cases = [
        ("0.0.6", True),
        ("0.0.9", True),
        ("0.0.11", False),
    ]

    for version, expected_result in test_cases:
        assert (
            Client.GPU_NODE.is_version_supported(version) is expected_result
        ), f"Version {version} support should be {expected_result}"
