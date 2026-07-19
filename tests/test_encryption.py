from agentwatch.security.encryption import APIKeyEncryption

def test_api_key_encryption():
    enc = APIKeyEncryption(master_key="test_master_key_12345")
    api_key = "my-secret-api-key"
    
    encrypted, nonce = enc.encrypt_key(api_key)
    assert encrypted != api_key
    assert nonce != ""
    
    decrypted = enc.decrypt_key(encrypted, nonce)
    assert decrypted == api_key
    
    hashed = enc.hash_key(api_key)
    assert len(hashed) == 64
