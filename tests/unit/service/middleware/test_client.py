from distributedinference.service.middleware.client_version_validation_middleware import (
    SupportedVersionRange,
)


async def test_client():
    test_cases = [
        (SupportedVersionRange("0.0.6", "0.0.9"), "0.0.5", False),
        (SupportedVersionRange("0.0.6", "0.0.9"), "0.0.6", True),
        (SupportedVersionRange("0.0.6", "0.0.9"), "0.0.9", True),
        (SupportedVersionRange("0.0.6", "0.0.9"), "0.0.10", False),
        (SupportedVersionRange("0.0.6", "0.0.10"), "0.0.10", True),
        (SupportedVersionRange("0.0.6", "0.0.10"), "0.0.11", False),
        (SupportedVersionRange("0.0.6", "0.1.0"), "0.0.11", True),
        (SupportedVersionRange("0.1.2", "0.2.0"), "0.1.1", False),
        (SupportedVersionRange("0.1.2", "0.2.0"), "0.1.2", True),
    ]

    for range, version, expected_result in test_cases:
        assert range.is_version_supported(version) == expected_result
