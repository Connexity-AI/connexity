"""Fingerprints and masking."""

from app.services.fingerprint import (
    MASK,
    combined_fingerprint,
    fingerprint,
    mask_secrets,
    without,
)


def test_the_same_content_gives_the_same_fingerprint_whatever_the_key_order() -> None:
    assert fingerprint({"a": 1, "b": [1, 2]}) == fingerprint({"b": [1, 2], "a": 1})
    assert fingerprint({"a": 1}) != fingerprint({"a": 2})
    assert len(fingerprint("x")) == 64


def test_fields_left_out_do_not_change_the_fingerprint() -> None:
    one = {"prompt": "Hello", "version": 3, "last_modification_timestamp": 1}
    two = {"prompt": "Hello", "version": 4, "last_modification_timestamp": 2}
    ignore = ("version", "last_modification_timestamp")
    assert fingerprint(without(one, ignore)) == fingerprint(without(two, ignore))


def test_header_values_are_masked_in_both_shapes() -> None:
    masked = mask_secrets(
        {
            "url": "https://example.com/hook",
            "headers": {"Authorization": "Bearer invented", "X-Team": "sales"},
            "parameters": {
                "headerParameters": {
                    "parameters": [{"name": "X-Api-Key", "value": "invented-1"}]
                },
                "queryParameters": {"parameters": [{"name": "limit", "value": "10"}]},
            },
        }
    )
    assert masked["url"] == "https://example.com/hook"
    assert masked["headers"] == {"Authorization": MASK, "X-Team": MASK}
    assert masked["parameters"]["headerParameters"]["parameters"] == [
        {"name": "X-Api-Key", "value": MASK}
    ]
    # Not a header and not named like a credential: kept.
    assert masked["parameters"]["queryParameters"]["parameters"] == [
        {"name": "limit", "value": "10"}
    ]


def test_fields_named_like_credentials_are_masked_whatever_the_value() -> None:
    masked = mask_secrets(
        {
            "api_key": "x",
            "apiKey": "",
            "access_token": "plain words",
            "clientSecret": "12345",
            "password": "p",
            "model": "gpt-4.1",
            "max_tokens_note": "kept? no: named like a token",
            "nested": [{"webhook_secret": "s", "name": "kept"}],
            "token_count": 42,
        }
    )
    assert masked["api_key"] == masked["apiKey"] == masked["access_token"] == MASK
    assert masked["clientSecret"] == masked["password"] == MASK
    assert masked["model"] == "gpt-4.1"
    assert masked["nested"] == [{"webhook_secret": MASK, "name": "kept"}]
    # Only strings are masked; a number under such a name is not a credential.
    assert masked["token_count"] == 42


def test_masking_makes_a_rotated_token_the_same_content() -> None:
    before = mask_secrets({"headers": {"Authorization": "Bearer old"}, "url": "u"})
    after = mask_secrets({"headers": {"Authorization": "Bearer new"}, "url": "u"})
    assert fingerprint(before) == fingerprint(after)


def test_masking_does_not_change_its_input() -> None:
    original = {"headers": {"Authorization": "Bearer invented"}}
    mask_secrets(original)
    assert original == {"headers": {"Authorization": "Bearer invented"}}


def test_combined_fingerprint() -> None:
    assert combined_fingerprint({}) is None
    one = combined_fingerprint({"agent": "a", "prompt": "p"})
    assert one == combined_fingerprint({"prompt": "p", "agent": "a"})
    assert one != combined_fingerprint({"agent": "a", "prompt": "q"})


def test_a_name_and_value_pair_named_like_a_credential_is_masked() -> None:
    masked = mask_secrets(
        {
            "queryParameters": {
                "parameters": [
                    {"name": "api_key", "value": "invented-secret"},
                    {"name": "limit", "value": "10"},
                ]
            },
            "access_key": "a",
            "Cookie": "c",
            "x_signature": "s",
        }
    )
    assert masked["queryParameters"]["parameters"] == [
        {"name": "api_key", "value": MASK},
        {"name": "limit", "value": "10"},
    ]
    assert masked["access_key"] == masked["Cookie"] == masked["x_signature"] == MASK
