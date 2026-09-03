from app.auth.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    """Test that hashing and verifying passwords works correctly."""
    plain_password = "my_secure_password"
    hashed = hash_password(plain_password)
    
    assert hashed != plain_password
    assert verify_password(plain_password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_jwt_token_creation_and_decoding():
    """Test that JWT tokens can be created and decoded with matching payloads."""
    payload = {"sub": "editor", "role": "editor"}
    token = create_access_token(payload)
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "editor"
    assert decoded["role"] == "editor"
    assert "exp" in decoded  # Should contain expiration time

def test_jwt_invalid_token():
    """Test that invalid tokens return None."""
    decoded = decode_access_token("this.is.not.a.valid.jwt")
    assert decoded is None
