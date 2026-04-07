# -*- coding: utf-8 -*-
"""
Tests unitaires pour le gestionnaire d'authentification
"""

import pytest
import sys
from pathlib import Path
import hashlib
import json
import tempfile
import os
import shutil

# Ajouter le chemin streamlit
sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))

from auth_manager import (
    hash_password,
    verify_password,
    load_users,
    save_users,
    authenticate,
    has_permission,
    DEFAULT_USERS
)

# Fixture pour restaurer users_db.json après chaque test
@pytest.fixture(autouse=True)
def reset_users_db():
    """Reset users database before each test"""
    # Sauvegarder les utilisateurs par défaut
    original_users = DEFAULT_USERS.copy()
    yield
    # Restaurer après le test
    save_users(original_users)


class TestPasswordHashing:
    """Tests pour le hachage de mots de passe"""
    
    def test_hash_password_creates_hash(self):
        """Verify that password hashing creates a hash"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) == 64  # SHA-256 = 64 chars hex
    
    def test_verify_password_success(self):
        """Verify that correct password validates"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
    
    def test_verify_password_failure(self):
        """Verify that incorrect password fails"""
        password = "test123"
        wrong_password = "wrong123"
        hashed = hash_password(password)
        assert not verify_password(wrong_password, hashed)
    
    def test_hash_consistency(self):
        """Verify that same password produces same hash"""
        password = "test123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 == hash2


class TestUserDataManagement:
    """Tests pour la gestion des données utilisateurs"""
    
    def test_load_users_returns_dict(self):
        """Verify load_users returns a dictionary"""
        users = load_users()
        assert isinstance(users, dict)
    
    def test_load_users_has_default_users(self):
        """Verify default users are loaded"""
        users = load_users()
        assert "admin" in users
        assert "user" in users
        assert "scientist" in users
    
    def test_default_users_have_required_fields(self):
        """Verify users have password_hash, role, and permissions"""
        users = DEFAULT_USERS
        for username, user_data in users.items():
            assert "password_hash" in user_data
            assert "role" in user_data
            assert "permissions" in user_data
            assert isinstance(user_data["permissions"], list)
    
    def test_save_and_load_users(self):
        """Verify users can be saved and loaded"""
        test_users = DEFAULT_USERS.copy()
        test_users["test_user"] = {
            "password_hash": hash_password("test123"),
            "role": "user",
            "permissions": ["inference"]
        }
        
        # Save
        save_users(test_users)
        
        # Load
        loaded_users = load_users()
        assert "test_user" in loaded_users
        assert loaded_users["test_user"]["role"] == "user"


class TestAuthentication:
    """Tests pour l'authentification"""
    
    def test_authenticate_admin_success(self, monkeypatch):
        """Verify admin authentication succeeds with correct password"""
        # Mock session state
        class MockSessionState:
            def __setattr__(self, name, value):
                self.__dict__[name] = value
            
            def __getattr__(self, name):
                return self.__dict__.get(name)
        
        st_session = MockSessionState()
        monkeypatch.setattr("auth_manager.st.session_state", st_session)
        
        result = authenticate("admin", "admin123")
        assert result == True
    
    def test_authenticate_fails_with_wrong_password(self, monkeypatch):
        """Verify authentication fails with wrong password"""
        class MockSessionState:
            def __setattr__(self, name, value):
                self.__dict__[name] = value
            
            def __getattr__(self, name):
                return self.__dict__.get(name)
        
        st_session = MockSessionState()
        monkeypatch.setattr("auth_manager.st.session_state", st_session)
        
        result = authenticate("admin", "wrongpassword")
        assert result == False
    
    def test_authenticate_fails_with_unknown_user(self, monkeypatch):
        """Verify authentication fails with unknown user"""
        class MockSessionState:
            def __setattr__(self, name, value):
                self.__dict__[name] = value
            
            def __getattr__(self, name):
                return self.__dict__.get(name)
        
        st_session = MockSessionState()
        monkeypatch.setattr("auth_manager.st.session_state", st_session)
        
        result = authenticate("unknown_user", "password123")
        assert result == False


class TestPermissions:
    """Tests pour les permissions"""
    
    def test_admin_has_all_permissions(self):
        """Verify admin user has all permissions"""
        admin = DEFAULT_USERS["admin"]
        expected_permissions = ["view_all", "train", "inference", "upload_data", "ci_cd", "monitoring"]
        for perm in expected_permissions:
            assert perm in admin["permissions"]
    
    def test_user_has_limited_permissions(self):
        """Verify user has limited permissions"""
        user = DEFAULT_USERS["user"]
        expected_permissions = ["inference", "view_tests", "view_monitoring"]
        assert user["permissions"] == expected_permissions
    
    def test_scientist_has_training_permissions(self):
        """Verify scientist can train"""
        scientist = DEFAULT_USERS["scientist"]
        assert "train" in scientist["permissions"]
        assert "inference" in scientist["permissions"]
    
    def test_user_cannot_train(self):
        """Verify user cannot train"""
        user = DEFAULT_USERS["user"]
        assert "train" not in user["permissions"]
    
    def test_user_cannot_upload_data(self):
        """Verify user cannot upload data"""
        user = DEFAULT_USERS["user"]
        assert "upload_data" not in user["permissions"]


class TestRoles:
    """Tests pour les rôles"""
    
    def test_all_users_have_role(self):
        """Verify all users have a role"""
        for username, user_data in DEFAULT_USERS.items():
            assert "role" in user_data
            assert user_data["role"] in ["admin", "user", "scientist"]
    
    def test_role_is_string(self):
        """Verify role is a string"""
        for username, user_data in DEFAULT_USERS.items():
            assert isinstance(user_data["role"], str)


class TestSecurityBestPractices:
    """Tests pour les meilleures pratiques de sécurité"""
    
    def test_passwords_are_hashed_not_plain(self):
        """Verify passwords are never stored in plain text"""
        for username, user_data in DEFAULT_USERS.items():
            password_hash = user_data["password_hash"]
            # Check it looks like a hash (64 chars hex)
            assert len(password_hash) == 64
            assert all(c in "0123456789abcdef" for c in password_hash)
    
    def test_default_passwords_are_changed_recommended(self):
        """Verify default passwords should be changed in production"""
        # This is a reminder test - default passwords should be changed
        # in production environments
        pass
    
    def test_permissions_follow_least_privilege(self):
        """Verify permissions follow least privilege principle"""
        # User has minimal permissions
        user = DEFAULT_USERS["user"]
        assert len(user["permissions"]) <= 3
        
        # Scientist has moderate permissions
        scientist = DEFAULT_USERS["scientist"]
        assert len(scientist["permissions"]) <= 6
        
        # Admin has maximum permissions
        admin = DEFAULT_USERS["admin"]
        assert len(admin["permissions"]) == 6


# ========== TESTS D'INTÉGRATION ==========

class TestAuthenticationFlow:
    """Tests d'intégration du flux d'authentification"""
    
    def test_login_logout_cycle(self, monkeypatch):
        """Verify complete login/logout cycle works"""
        class MockSessionState:
            def __setattr__(self, name, value):
                self.__dict__[name] = value
            
            def __getattr__(self, name):
                return self.__dict__.get(name)
        
        st_session = MockSessionState()
        monkeypatch.setattr("auth_manager.st.session_state", st_session)
        
        # Initial state
        assert not getattr(st_session, "authenticated", False)
        
        # Login
        authenticate("admin", "admin123")
        assert getattr(st_session, "authenticated", False) == True
        assert getattr(st_session, "username", None) == "admin"
        assert getattr(st_session, "role", None) == "admin"
    
    def test_permission_check_after_login(self, monkeypatch):
        """Verify permissions are correctly set after login"""
        class MockSessionState:
            def __init__(self):
                self._data = {}
            
            def __setattr__(self, name, value):
                if name.startswith('_'):
                    super().__setattr__(name, value)
                else:
                    self._data[name] = value
            
            def __getattr__(self, name):
                if name.startswith('_'):
                    return super().__getattribute__(name)
                return self._data.get(name)
            
            def get(self, key, default=None):
                return self._data.get(key, default)
        
        st_session = MockSessionState()
        monkeypatch.setattr("auth_manager.st.session_state", st_session)
        
        # Admin login
        authenticate("admin", "admin123")
        
        # Check permissions
        assert has_permission("train")
        assert has_permission("inference")
        assert has_permission("upload_data")


if __name__ == "__main__":
    # Exécuter les tests
    pytest.main([__file__, "-v", "--tb=short"])
