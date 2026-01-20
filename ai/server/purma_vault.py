#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗                                 ║
║     ██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝                                 ║
║     ██║   ██║███████║██║   ██║██║     ██║                                    ║
║     ╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║                                    ║
║      ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║                                    ║
║       ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝                                    ║
║                                                                              ║
║                    PurmaLinux AI Password Manager                            ║
║              Secure secrets with natural language queries                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import base64
import hashlib
import secrets
import string
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re

# Cryptography imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not installed. Run: pip install cryptography")


class SecretType(Enum):
    """Types of secrets that can be stored"""
    PASSWORD = "password"
    API_KEY = "api_key"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    NOTE = "secure_note"
    CREDIT_CARD = "credit_card"
    IDENTITY = "identity"
    OTHER = "other"


@dataclass
class Secret:
    """A stored secret"""
    id: str
    name: str
    secret_type: str
    username: Optional[str]
    encrypted_value: str
    url: Optional[str]
    category: str
    tags: List[str]
    notes: Optional[str]
    created_at: str
    updated_at: str
    last_accessed: Optional[str]
    access_count: int
    favorite: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EncryptionEngine:
    """Handles all encryption/decryption operations"""

    def __init__(self, master_password: str, salt: Optional[bytes] = None):
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")

        self.salt = salt or os.urandom(16)
        self.key = self._derive_key(master_password)
        self.fernet = Fernet(self.key)

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from master password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=480000,  # High iteration count for security
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string"""
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string"""
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self.fernet.decrypt(encrypted)
        return decrypted.decode()

    def get_salt_b64(self) -> str:
        """Get salt as base64 string for storage"""
        return base64.urlsafe_b64encode(self.salt).decode()

    @staticmethod
    def salt_from_b64(salt_b64: str) -> bytes:
        """Restore salt from base64 string"""
        return base64.urlsafe_b64decode(salt_b64.encode())


class PasswordGenerator:
    """Generate secure passwords"""

    @staticmethod
    def generate(
        length: int = 20,
        uppercase: bool = True,
        lowercase: bool = True,
        digits: bool = True,
        symbols: bool = True,
        exclude_ambiguous: bool = True,
        custom_symbols: Optional[str] = None
    ) -> str:
        """Generate a secure random password"""
        chars = ""

        if lowercase:
            chars += string.ascii_lowercase
        if uppercase:
            chars += string.ascii_uppercase
        if digits:
            chars += string.digits
        if symbols:
            chars += custom_symbols or "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if exclude_ambiguous:
            ambiguous = "0O1lI"
            chars = "".join(c for c in chars if c not in ambiguous)

        if not chars:
            chars = string.ascii_letters + string.digits

        # Ensure at least one character from each selected category
        password = []
        if lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if digits:
            valid_digits = "".join(d for d in string.digits if d not in "0O1lI") if exclude_ambiguous else string.digits
            password.append(secrets.choice(valid_digits))
        if symbols:
            syms = custom_symbols or "!@#$%^&*()_+-=[]{}|;:,.<>?"
            password.append(secrets.choice(syms))

        # Fill rest with random chars
        remaining = length - len(password)
        password.extend(secrets.choice(chars) for _ in range(remaining))

        # Shuffle
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)

        return "".join(password_list)

    @staticmethod
    def generate_passphrase(
        word_count: int = 4,
        separator: str = "-",
        capitalize: bool = True
    ) -> str:
        """Generate a passphrase using common words"""
        # Common words for passphrases (simplified list)
        words = [
            "apple", "banana", "cherry", "dragon", "eagle", "falcon", "guitar",
            "hammer", "island", "jungle", "kernel", "lemon", "mango", "nebula",
            "ocean", "planet", "quartz", "river", "solar", "thunder", "umbra",
            "violet", "whisper", "xenon", "yellow", "zenith", "alpha", "bravo",
            "castle", "delta", "echo", "forest", "gamma", "horizon", "igloo",
            "jasper", "karma", "lunar", "matrix", "nova", "omega", "phoenix",
            "quantum", "radar", "sigma", "tiger", "ultra", "vortex", "winter",
            "azure", "blaze", "comet", "dusk", "ember", "frost", "glacier",
            "harbor", "iris", "jade", "kinetic", "lotus", "mystic", "neon"
        ]

        selected = [secrets.choice(words) for _ in range(word_count)]

        if capitalize:
            selected = [w.capitalize() for w in selected]

        return separator.join(selected)

    @staticmethod
    def check_strength(password: str) -> Dict[str, Any]:
        """Check password strength"""
        score = 0
        feedback = []

        # Length checks
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        if len(password) < 8:
            feedback.append("Password should be at least 8 characters")

        # Character variety
        has_lower = bool(re.search(r"[a-z]", password))
        has_upper = bool(re.search(r"[A-Z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_symbol = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password))

        if has_lower:
            score += 1
        else:
            feedback.append("Add lowercase letters")

        if has_upper:
            score += 1
        else:
            feedback.append("Add uppercase letters")

        if has_digit:
            score += 1
        else:
            feedback.append("Add numbers")

        if has_symbol:
            score += 1
        else:
            feedback.append("Add special characters")

        # Common patterns to avoid
        common_patterns = [
            r"123", r"abc", r"qwerty", r"password", r"admin",
            r"(.)\1{2,}",  # Repeated characters
        ]

        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                score -= 1
                feedback.append("Avoid common patterns")
                break

        # Determine strength level
        if score <= 2:
            level = "weak"
        elif score <= 4:
            level = "fair"
        elif score <= 6:
            level = "good"
        else:
            level = "strong"

        return {
            "score": max(0, min(score, 7)),
            "max_score": 7,
            "level": level,
            "feedback": feedback,
            "length": len(password),
            "has_lowercase": has_lower,
            "has_uppercase": has_upper,
            "has_digits": has_digit,
            "has_symbols": has_symbol
        }


class VaultStorage:
    """SQLite storage for the vault"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    secret_type TEXT NOT NULL,
                    username TEXT,
                    encrypted_value TEXT NOT NULL,
                    url TEXT,
                    category TEXT DEFAULT 'General',
                    tags TEXT DEFAULT '[]',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0,
                    favorite INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_secrets_name ON secrets(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_secrets_category ON secrets(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_secrets_type ON secrets(secret_type)
            """)

            conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        """Get metadata value"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM vault_meta WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def set_meta(self, key: str, value: str):
        """Set metadata value"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()

    def save_secret(self, secret: Secret):
        """Save or update a secret"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO secrets
                (id, name, secret_type, username, encrypted_value, url, category,
                 tags, notes, created_at, updated_at, last_accessed, access_count, favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                secret.id, secret.name, secret.secret_type, secret.username,
                secret.encrypted_value, secret.url, secret.category,
                json.dumps(secret.tags), secret.notes, secret.created_at,
                secret.updated_at, secret.last_accessed, secret.access_count,
                1 if secret.favorite else 0
            ))
            conn.commit()

    def get_secret(self, secret_id: str) -> Optional[Secret]:
        """Get a secret by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM secrets WHERE id = ?", (secret_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_secret(row)
        return None

    def get_all_secrets(self) -> List[Secret]:
        """Get all secrets"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM secrets ORDER BY name")
            return [self._row_to_secret(row) for row in cursor.fetchall()]

    def search_secrets(
        self,
        query: str,
        category: Optional[str] = None,
        secret_type: Optional[str] = None
    ) -> List[Secret]:
        """Search secrets by name, username, url, or tags"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT * FROM secrets
                WHERE (name LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ?)
            """
            params = [f"%{query}%"] * 4

            if category:
                sql += " AND category = ?"
                params.append(category)

            if secret_type:
                sql += " AND secret_type = ?"
                params.append(secret_type)

            sql += " ORDER BY favorite DESC, access_count DESC, name"

            cursor = conn.execute(sql, params)
            return [self._row_to_secret(row) for row in cursor.fetchall()]

    def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM secrets WHERE id = ?", (secret_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_access(self, secret_id: str):
        """Update access timestamp and count"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE secrets
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (now, secret_id))
            conn.commit()

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT category FROM secrets ORDER BY category"
            )
            return [row[0] for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get vault statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM secrets").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT secret_type, COUNT(*) FROM secrets GROUP BY secret_type"
            ).fetchall())
            by_category = dict(conn.execute(
                "SELECT category, COUNT(*) FROM secrets GROUP BY category"
            ).fetchall())
            favorites = conn.execute(
                "SELECT COUNT(*) FROM secrets WHERE favorite = 1"
            ).fetchone()[0]

            return {
                "total": total,
                "by_type": by_type,
                "by_category": by_category,
                "favorites": favorites
            }

    def _row_to_secret(self, row: sqlite3.Row) -> Secret:
        """Convert database row to Secret object"""
        return Secret(
            id=row["id"],
            name=row["name"],
            secret_type=row["secret_type"],
            username=row["username"],
            encrypted_value=row["encrypted_value"],
            url=row["url"],
            category=row["category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
            favorite=bool(row["favorite"])
        )


class AIQueryProcessor:
    """Process natural language queries for the vault"""

    # Query patterns for natural language understanding
    PATTERNS = {
        "get_password": [
            r"(?:what(?:'s| is)|show|get|find|give me)(?: the)? (?:password|pass|pwd|cred(?:ential)?s?) (?:for|of|to) (.+)",
            r"(.+?) (?:password|pass|pwd|cred(?:ential)?s?)",
            r"(?:password|pass|pwd) (?:for|of|to) (.+)",
        ],
        "get_username": [
            r"(?:what(?:'s| is)|show|get|find)(?: the)? (?:username|user|login|email) (?:for|of|to) (.+)",
            r"(.+?) (?:username|user|login)",
        ],
        "list_category": [
            r"(?:list|show|get)(?: all)? (.+?) (?:passwords|accounts|secrets)",
            r"(?:all|my) (.+?) (?:passwords|accounts|secrets)",
        ],
        "search": [
            r"(?:search|find|look for) (.+)",
            r"(?:do i have|is there)(?: a)? (.+)",
        ],
        "generate": [
            r"(?:generate|create|make)(?: a)?(?: new)? (?:password|pass)",
            r"(?:new|random) (?:password|pass)",
        ],
    }

    def __init__(self):
        self.compiled_patterns = {}
        for intent, patterns in self.PATTERNS.items():
            self.compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def parse_query(self, query: str) -> Tuple[str, Optional[str]]:
        """
        Parse a natural language query and return intent and extracted entity.
        Returns: (intent, entity)
        """
        query = query.strip()

        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(query)
                if match:
                    entity = match.group(1) if match.groups() else None
                    if entity:
                        entity = entity.strip().rstrip("?.,!")
                    return intent, entity

        # Default to search if no pattern matches
        return "search", query

    def extract_service_name(self, text: str) -> str:
        """Extract and normalize service name from text"""
        # Remove common words
        stop_words = {
            "the", "my", "a", "an", "for", "to", "of", "password", "account",
            "login", "credentials", "username", "what", "is", "show", "get"
        }

        words = text.lower().split()
        words = [w for w in words if w not in stop_words]

        return " ".join(words).strip()


class VaultEngine:
    """Main Purma Vault engine"""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".local" / "share" / "purma" / "vault"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "vault.db"
        self.storage = VaultStorage(self.db_path)

        self.encryption: Optional[EncryptionEngine] = None
        self.is_unlocked = False
        self.unlock_time: Optional[datetime] = None
        self.auto_lock_minutes = 15

        self.query_processor = AIQueryProcessor()
        self.password_generator = PasswordGenerator()

    def is_initialized(self) -> bool:
        """Check if vault has been initialized with a master password"""
        return self.storage.get_meta("salt") is not None

    def initialize(self, master_password: str) -> bool:
        """Initialize vault with master password"""
        if self.is_initialized():
            return False

        # Create encryption engine
        self.encryption = EncryptionEngine(master_password)

        # Store salt and verification hash
        self.storage.set_meta("salt", self.encryption.get_salt_b64())

        # Store encrypted verification string
        verification = self.encryption.encrypt("PURMA_VAULT_VERIFIED")
        self.storage.set_meta("verification", verification)

        self.is_unlocked = True
        self.unlock_time = datetime.now()

        return True

    def unlock(self, master_password: str) -> bool:
        """Unlock the vault with master password"""
        if not self.is_initialized():
            return False

        try:
            # Get stored salt
            salt_b64 = self.storage.get_meta("salt")
            salt = EncryptionEngine.salt_from_b64(salt_b64)

            # Create encryption engine with stored salt
            self.encryption = EncryptionEngine(master_password, salt)

            # Verify password by decrypting verification string
            verification = self.storage.get_meta("verification")
            decrypted = self.encryption.decrypt(verification)

            if decrypted == "PURMA_VAULT_VERIFIED":
                self.is_unlocked = True
                self.unlock_time = datetime.now()
                return True
        except Exception:
            pass

        self.encryption = None
        self.is_unlocked = False
        return False

    def lock(self):
        """Lock the vault"""
        self.encryption = None
        self.is_unlocked = False
        self.unlock_time = None

    def check_auto_lock(self) -> bool:
        """Check if vault should auto-lock and lock if needed"""
        if not self.is_unlocked or not self.unlock_time:
            return True

        if datetime.now() - self.unlock_time > timedelta(minutes=self.auto_lock_minutes):
            self.lock()
            return True

        return False

    def _require_unlock(self):
        """Ensure vault is unlocked"""
        self.check_auto_lock()
        if not self.is_unlocked:
            raise PermissionError("Vault is locked")

    def add_secret(
        self,
        name: str,
        value: str,
        secret_type: str = "password",
        username: Optional[str] = None,
        url: Optional[str] = None,
        category: str = "General",
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        favorite: bool = False
    ) -> Secret:
        """Add a new secret to the vault"""
        self._require_unlock()

        now = datetime.now().isoformat()
        secret_id = secrets.token_urlsafe(16)

        # Encrypt the value
        encrypted_value = self.encryption.encrypt(value)

        secret = Secret(
            id=secret_id,
            name=name,
            secret_type=secret_type,
            username=username,
            encrypted_value=encrypted_value,
            url=url,
            category=category,
            tags=tags or [],
            notes=notes,
            created_at=now,
            updated_at=now,
            last_accessed=None,
            access_count=0,
            favorite=favorite
        )

        self.storage.save_secret(secret)
        return secret

    def get_secret(self, secret_id: str, decrypt: bool = True) -> Optional[Dict[str, Any]]:
        """Get a secret by ID"""
        self._require_unlock()

        secret = self.storage.get_secret(secret_id)
        if not secret:
            return None

        self.storage.update_access(secret_id)

        result = secret.to_dict()
        if decrypt:
            result["decrypted_value"] = self.encryption.decrypt(secret.encrypted_value)

        return result

    def update_secret(
        self,
        secret_id: str,
        name: Optional[str] = None,
        value: Optional[str] = None,
        username: Optional[str] = None,
        url: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        favorite: Optional[bool] = None
    ) -> Optional[Secret]:
        """Update an existing secret"""
        self._require_unlock()

        secret = self.storage.get_secret(secret_id)
        if not secret:
            return None

        # Update fields
        if name is not None:
            secret.name = name
        if value is not None:
            secret.encrypted_value = self.encryption.encrypt(value)
        if username is not None:
            secret.username = username
        if url is not None:
            secret.url = url
        if category is not None:
            secret.category = category
        if tags is not None:
            secret.tags = tags
        if notes is not None:
            secret.notes = notes
        if favorite is not None:
            secret.favorite = favorite

        secret.updated_at = datetime.now().isoformat()

        self.storage.save_secret(secret)
        return secret

    def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret"""
        self._require_unlock()
        return self.storage.delete_secret(secret_id)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        secret_type: Optional[str] = None,
        decrypt: bool = False
    ) -> List[Dict[str, Any]]:
        """Search secrets"""
        self._require_unlock()

        secrets_list = self.storage.search_secrets(query, category, secret_type)

        results = []
        for secret in secrets_list:
            result = secret.to_dict()
            if decrypt:
                result["decrypted_value"] = self.encryption.decrypt(secret.encrypted_value)
            else:
                # Don't include encrypted value in results
                result.pop("encrypted_value", None)
            results.append(result)

        return results

    def list_all(self, decrypt: bool = False) -> List[Dict[str, Any]]:
        """List all secrets"""
        self._require_unlock()

        secrets_list = self.storage.get_all_secrets()

        results = []
        for secret in secrets_list:
            result = secret.to_dict()
            if decrypt:
                result["decrypted_value"] = self.encryption.decrypt(secret.encrypted_value)
            else:
                result.pop("encrypted_value", None)
            results.append(result)

        return results

    def get_categories(self) -> List[str]:
        """Get all categories"""
        self._require_unlock()
        return self.storage.get_categories()

    def get_stats(self) -> Dict[str, Any]:
        """Get vault statistics"""
        return self.storage.get_stats()

    def generate_password(
        self,
        length: int = 20,
        uppercase: bool = True,
        lowercase: bool = True,
        digits: bool = True,
        symbols: bool = True
    ) -> Dict[str, Any]:
        """Generate a new password"""
        password = self.password_generator.generate(
            length=length,
            uppercase=uppercase,
            lowercase=lowercase,
            digits=digits,
            symbols=symbols
        )

        strength = self.password_generator.check_strength(password)

        return {
            "password": password,
            "strength": strength
        }

    def generate_passphrase(
        self,
        word_count: int = 4,
        separator: str = "-",
        capitalize: bool = True
    ) -> Dict[str, Any]:
        """Generate a passphrase"""
        passphrase = self.password_generator.generate_passphrase(
            word_count=word_count,
            separator=separator,
            capitalize=capitalize
        )

        strength = self.password_generator.check_strength(passphrase)

        return {
            "passphrase": passphrase,
            "strength": strength
        }

    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """Check password strength"""
        return self.password_generator.check_strength(password)

    async def ai_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query about the vault.
        Returns structured response with intent and results.
        """
        self._require_unlock()

        intent, entity = self.query_processor.parse_query(query)

        if intent == "generate":
            result = self.generate_password()
            return {
                "intent": "generate",
                "success": True,
                "message": f"Generated password: {result['password']}",
                "data": result
            }

        if intent in ("get_password", "get_username", "search"):
            if entity:
                service = self.query_processor.extract_service_name(entity)
                results = self.search(service, decrypt=True)

                if results:
                    if intent == "get_password":
                        # Return first matching password
                        secret = results[0]
                        return {
                            "intent": intent,
                            "success": True,
                            "message": f"Password for {secret['name']}: {secret.get('decrypted_value', '[encrypted]')}",
                            "data": {
                                "name": secret["name"],
                                "username": secret.get("username"),
                                "password": secret.get("decrypted_value"),
                                "url": secret.get("url")
                            }
                        }
                    elif intent == "get_username":
                        secret = results[0]
                        return {
                            "intent": intent,
                            "success": True,
                            "message": f"Username for {secret['name']}: {secret.get('username', 'N/A')}",
                            "data": secret
                        }
                    else:
                        return {
                            "intent": intent,
                            "success": True,
                            "message": f"Found {len(results)} matching secrets",
                            "data": results
                        }
                else:
                    return {
                        "intent": intent,
                        "success": False,
                        "message": f"No secrets found matching '{entity}'",
                        "data": None
                    }

        if intent == "list_category":
            if entity:
                results = self.search("", category=entity)
                return {
                    "intent": intent,
                    "success": True,
                    "message": f"Found {len(results)} secrets in category '{entity}'",
                    "data": results
                }

        # Default fallback - search
        results = self.search(query)
        return {
            "intent": "search",
            "success": len(results) > 0,
            "message": f"Found {len(results)} matching secrets",
            "data": results
        }

    def export_vault(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export vault data (for backup)"""
        self._require_unlock()

        secrets_list = self.list_all(decrypt=include_secrets)

        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "stats": self.get_stats(),
            "categories": self.get_categories(),
            "secrets": secrets_list if include_secrets else [
                {k: v for k, v in s.items() if k != "decrypted_value"}
                for s in secrets_list
            ]
        }

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """Change the master password"""
        # Verify old password
        if not self.unlock(old_password):
            return False

        # Get all secrets with decrypted values
        secrets_list = self.storage.get_all_secrets()
        decrypted_secrets = []
        for secret in secrets_list:
            decrypted_value = self.encryption.decrypt(secret.encrypted_value)
            decrypted_secrets.append((secret, decrypted_value))

        # Create new encryption with new password
        new_encryption = EncryptionEngine(new_password)

        # Re-encrypt all secrets
        for secret, decrypted_value in decrypted_secrets:
            secret.encrypted_value = new_encryption.encrypt(decrypted_value)
            secret.updated_at = datetime.now().isoformat()
            self.storage.save_secret(secret)

        # Update salt and verification
        self.storage.set_meta("salt", new_encryption.get_salt_b64())
        verification = new_encryption.encrypt("PURMA_VAULT_VERIFIED")
        self.storage.set_meta("verification", verification)

        # Update encryption engine
        self.encryption = new_encryption

        return True


# Global vault instance
_vault_engine: Optional[VaultEngine] = None


def get_vault_engine() -> VaultEngine:
    """Get or create the global vault engine instance"""
    global _vault_engine
    if _vault_engine is None:
        _vault_engine = VaultEngine()
    return _vault_engine


# CLI interface
if __name__ == "__main__":
    import sys

    vault = get_vault_engine()

    if len(sys.argv) < 2:
        print("Purma Vault - AI Password Manager")
        print("Usage: purma_vault.py <command> [args]")
        print("\nCommands:")
        print("  init              - Initialize vault with master password")
        print("  unlock            - Unlock the vault")
        print("  lock              - Lock the vault")
        print("  add <name>        - Add a new secret")
        print("  get <name>        - Get a secret")
        print("  search <query>    - Search secrets")
        print("  list              - List all secrets")
        print("  generate          - Generate a password")
        print("  stats             - Show vault statistics")
        sys.exit(0)

    command = sys.argv[1]

    if command == "init":
        if vault.is_initialized():
            print("Vault is already initialized")
        else:
            import getpass
            password = getpass.getpass("Create master password: ")
            confirm = getpass.getpass("Confirm master password: ")
            if password == confirm:
                vault.initialize(password)
                print("Vault initialized successfully!")
            else:
                print("Passwords don't match")

    elif command == "generate":
        result = vault.generate_password()
        print(f"Password: {result['password']}")
        print(f"Strength: {result['strength']['level']}")

    elif command == "stats":
        if not vault.is_initialized():
            print("Vault not initialized")
        else:
            stats = vault.get_stats()
            print(f"Total secrets: {stats['total']}")
            print(f"Favorites: {stats['favorites']}")
            print(f"By type: {stats['by_type']}")
            print(f"By category: {stats['by_category']}")
