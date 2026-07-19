from agentwatch.security.key_storage import EncryptedAPIKey, KeyRotationAudit, KeyAccessAudit

def test_key_storage_models():
    # Instantiate models to cover the classes
    key = EncryptedAPIKey(agent_id="test", key_hash="hash", encrypted_key="enc", nonce="nonce")
    assert key.agent_id == "test"
    
    audit = KeyRotationAudit(rotation_id="r1", agent_id="test", new_key_hash="hash2", rotated_by="admin")
    assert audit.rotation_id == "r1"
    
    access = KeyAccessAudit(access_id="a1", agent_id="test", accessed_by="admin", access_type="decrypt")
    assert access.access_id == "a1"
