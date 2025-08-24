"""WebAuthn service for passkey authentication."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

import cbor2
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.exceptions import InvalidSignature

from app.config import config


class WebAuthnService:
    """Service for handling WebAuthn/FIDO2 passkey operations."""
    
    def __init__(self, rp_id: str = "localhost", rp_name: str = "FastAPI Enterprise App"):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.challenge_cache = {}  # In production, use Redis for this
        
    def generate_challenge(self) -> str:
        """Generate a cryptographically secure challenge."""
        challenge_bytes = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    
    def store_challenge(self, user_id: int, challenge: str, expires_in: int = 300) -> None:
        """Store challenge for later verification."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self.challenge_cache[user_id] = {
            'challenge': challenge,
            'expires_at': expires_at
        }
    
    def get_challenge(self, user_id: int) -> Optional[str]:
        """Retrieve stored challenge for user."""
        challenge_data = self.challenge_cache.get(user_id)
        if not challenge_data:
            return None
        
        if datetime.now(timezone.utc) > challenge_data['expires_at']:
            del self.challenge_cache[user_id]
            return None
        
        return challenge_data['challenge']
    
    def clear_challenge(self, user_id: int) -> None:
        """Clear stored challenge for user."""
        self.challenge_cache.pop(user_id, None)
    
    def create_registration_options(self, user_id: int, username: str, display_name: str, 
                                    exclude_credentials: List[str] = None) -> Dict[str, Any]:
        """Create WebAuthn registration options."""
        challenge = self.generate_challenge()
        self.store_challenge(user_id, challenge)
        
        user_handle = base64.urlsafe_b64encode(str(user_id).encode()).decode('utf-8').rstrip('=')
        
        options = {
            'challenge': challenge,
            'rp': {
                'name': self.rp_name,
                'id': self.rp_id
            },
            'user': {
                'id': user_handle,
                'name': username,
                'displayName': display_name
            },
            'pubKeyCredParams': [
                {'alg': -7, 'type': 'public-key'},   # ES256
                {'alg': -257, 'type': 'public-key'}, # RS256
            ],
            'timeout': 60000,
            'attestation': 'none',
            'authenticatorSelection': {
                'authenticatorAttachment': 'platform',
                'userVerification': 'required',
                'residentKey': 'preferred'
            },
            'excludeCredentials': []
        }
        
        if exclude_credentials:
            options['excludeCredentials'] = [
                {
                    'id': cred_id,
                    'type': 'public-key',
                    'transports': ['internal']
                }
                for cred_id in exclude_credentials
            ]
        
        return options
    
    def create_authentication_options(self, user_id: Optional[int] = None, 
                                     allow_credentials: List[str] = None) -> Dict[str, Any]:
        """Create WebAuthn authentication options."""
        challenge = self.generate_challenge()
        
        if user_id:
            self.store_challenge(user_id, challenge)
        
        options = {
            'challenge': challenge,
            'timeout': 60000,
            'rpId': self.rp_id,
            'allowCredentials': [],
            'userVerification': 'required'
        }
        
        if allow_credentials:
            options['allowCredentials'] = [
                {
                    'id': cred_id,
                    'type': 'public-key',
                    'transports': ['internal']
                }
                for cred_id in allow_credentials
            ]
        
        return options, challenge
    
    def verify_registration_response(self, user_id: int, response: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify WebAuthn registration response."""
        try:
            # Get stored challenge
            challenge = self.get_challenge(user_id)
            if not challenge:
                return False, {'error': 'No challenge found or challenge expired'}
            
            # Parse the authenticator response
            attestation_object = self._decode_base64url(response['response']['attestationObject'])
            client_data_json = self._decode_base64url(response['response']['clientDataJSON'])
            
            # Parse client data
            client_data = json.loads(client_data_json.decode('utf-8'))
            
            # Verify challenge
            if client_data.get('challenge') != challenge:
                return False, {'error': 'Challenge mismatch'}
            
            # Verify origin (in production, be more strict about this)
            expected_origins = [f'https://{self.rp_id}', f'http://{self.rp_id}:8000', 'http://localhost:8000']
            if client_data.get('origin') not in expected_origins:
                return False, {'error': f'Invalid origin: {client_data.get("origin")}'}
            
            # Parse attestation object
            attestation = cbor2.loads(attestation_object)
            auth_data = attestation['authData']
            
            # Parse authenticator data
            rp_id_hash = auth_data[:32]
            expected_rp_id_hash = hashlib.sha256(self.rp_id.encode()).digest()
            
            if rp_id_hash != expected_rp_id_hash:
                return False, {'error': 'RP ID hash mismatch'}
            
            # Check flags
            flags = auth_data[32]
            user_present = bool(flags & 0x01)
            user_verified = bool(flags & 0x04)
            attested_credential_data = bool(flags & 0x40)
            
            if not (user_present and user_verified and attested_credential_data):
                return False, {'error': 'Invalid authenticator flags'}
            
            # Extract credential data
            sign_count = struct.unpack('>I', auth_data[33:37])[0]
            
            # Parse attested credential data
            aaguid = auth_data[37:53]
            credential_id_length = struct.unpack('>H', auth_data[53:55])[0]
            credential_id = auth_data[55:55+credential_id_length]
            
            # Extract public key
            public_key_cbor = auth_data[55+credential_id_length:]
            public_key_data = cbor2.loads(public_key_cbor)
            
            # Clear challenge
            self.clear_challenge(user_id)
            
            credential_data = {
                'credential_id': base64.urlsafe_b64encode(credential_id).decode('utf-8').rstrip('='),
                'public_key': public_key_cbor,
                'sign_count': sign_count,
                'aaguid': aaguid.hex()
            }
            
            return True, credential_data
            
        except Exception as e:
            return False, {'error': f'Registration verification failed: {str(e)}'}
    
    def verify_authentication_response(self, credential_id: str, public_key: bytes, 
                                     stored_sign_count: int, response: Dict[str, Any],
                                     challenge: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify WebAuthn authentication response."""
        try:
            # Parse the authenticator response
            authenticator_data = self._decode_base64url(response['response']['authenticatorData'])
            client_data_json = self._decode_base64url(response['response']['clientDataJSON'])
            signature = self._decode_base64url(response['response']['signature'])
            
            # Parse client data
            client_data = json.loads(client_data_json.decode('utf-8'))
            
            # Verify challenge
            if client_data.get('challenge') != challenge:
                return False, {'error': 'Challenge mismatch'}
            
            # Verify origin
            expected_origins = [f'https://{self.rp_id}', f'http://{self.rp_id}:8000', 'http://localhost:8000']
            if client_data.get('origin') not in expected_origins:
                return False, {'error': f'Invalid origin: {client_data.get("origin")}'}
            
            # Verify RP ID hash
            rp_id_hash = authenticator_data[:32]
            expected_rp_id_hash = hashlib.sha256(self.rp_id.encode()).digest()
            
            if rp_id_hash != expected_rp_id_hash:
                return False, {'error': 'RP ID hash mismatch'}
            
            # Check flags
            flags = authenticator_data[32]
            user_present = bool(flags & 0x01)
            user_verified = bool(flags & 0x04)
            
            if not (user_present and user_verified):
                return False, {'error': 'User not present or not verified'}
            
            # Extract and verify sign count
            current_sign_count = struct.unpack('>I', authenticator_data[33:37])[0]
            
            if current_sign_count <= stored_sign_count and stored_sign_count != 0:
                return False, {'error': 'Sign count verification failed (possible cloned authenticator)'}
            
            # Verify signature
            client_data_hash = hashlib.sha256(client_data_json).digest()
            signed_data = authenticator_data + client_data_hash
            
            # Parse public key
            public_key_data = cbor2.loads(public_key)
            
            if public_key_data.get(1) == 2:  # EC2 key type
                # ES256 signature
                curve_id = public_key_data.get(-1)
                x = public_key_data.get(-2)
                y = public_key_data.get(-3)
                
                if curve_id == 1:  # P-256 curve
                    # Construct EC public key
                    public_key_point = ec.EllipticCurvePublicNumbers(
                        int.from_bytes(x, byteorder='big'),
                        int.from_bytes(y, byteorder='big'),
                        ec.SECP256R1()
                    ).public_key()
                    
                    # Verify signature
                    try:
                        # Parse DER signature
                        r_s = decode_dss_signature(signature)
                        public_key_point.verify(signature, signed_data, ec.ECDSA(hashes.SHA256()))
                        signature_valid = True
                    except InvalidSignature:
                        signature_valid = False
                else:
                    return False, {'error': 'Unsupported curve'}
            else:
                return False, {'error': 'Unsupported key type'}
            
            if not signature_valid:
                return False, {'error': 'Signature verification failed'}
            
            return True, {'sign_count': current_sign_count}
            
        except Exception as e:
            return False, {'error': f'Authentication verification failed: {str(e)}'}
    
    def _decode_base64url(self, data: str) -> bytes:
        """Decode base64url string."""
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        
        return base64.urlsafe_b64decode(data)


# Global instance
webauthn_service = WebAuthnService(
    rp_id=config.security.passkey_rp_id if hasattr(config.security, 'passkey_rp_id') else "localhost",
    rp_name=config.title
)