from datetime import UTC, datetime

import jwt

from src import config
from src.api_nms import AuthInfo


class TestAuthInfo:
    def test_jwt(self):
        jwt_info = AuthInfo()
        token = jwt_info.jwt(expiry_seconds=60)
        # Decode the token to verify its contents
        decoded = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        # Check that the username and fullname are present
        assert decoded["username"] == jwt_info.username
        assert decoded["fullname"] == jwt_info.fullname
        # Check that expire_day and expire_password are equal
        assert jwt_info.expire_day == jwt_info.expire_password
        # Check that the expiry is within the next 2 minutes
        expire_dt = datetime.strptime(jwt_info.expire_day, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        now = datetime.now(UTC)
        # Allow for some clock skew
        assert 0 <= (expire_dt - now).total_seconds() <= 120  # noqa: PLR2004
