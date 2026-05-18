from unittest.mock import MagicMock, patch

import pytest

from app.tests.utils.user import authentication_token_from_email


def test_authentication_token_from_email_raises_when_user_has_no_id() -> None:
    user_without_id = MagicMock()
    user_without_id.id = None

    with patch(
        "app.tests.utils.user.crud.get_user_by_email", return_value=user_without_id
    ):
        with pytest.raises(Exception, match="User id not set"):
            authentication_token_from_email(
                client=MagicMock(),
                email="person@example.com",
                db=MagicMock(),
            )
