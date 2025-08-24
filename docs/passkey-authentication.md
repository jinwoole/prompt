# Passkey Authentication Implementation

This FastAPI application now supports **Passkey (WebAuthn/FIDO2) authentication** alongside traditional JWT-based authentication. This provides users with a passwordless, secure authentication method using biometrics, security keys, or platform authenticators.

## 🔐 Features

- **Dual Authentication**: Traditional username/password AND passkey authentication
- **WebAuthn/FIDO2 Compliant**: Implements W3C WebAuthn standard
- **Passwordless Flow**: Complete login without passwords using passkeys
- **Multiple Authenticators**: Support for platform (biometric) and cross-platform authenticators
- **Credential Management**: Users can register, list, and delete passkeys
- **Security First**: Proper challenge validation, signature verification, and replay protection

## 🏗️ Architecture

### Database Schema

New table `passkey_credentials`:
```sql
CREATE TABLE passkey_credentials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    credential_id VARCHAR(255) UNIQUE NOT NULL,
    public_key BYTEA NOT NULL,
    sign_count INTEGER DEFAULT 0,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### API Endpoints

#### Passkey Registration
- `POST /api/v1/passkey/register/begin` - Start passkey registration
- `POST /api/v1/passkey/register/complete` - Complete passkey registration

#### Passkey Authentication
- `POST /api/v1/passkey/authenticate/begin` - Start passkey authentication
- `POST /api/v1/passkey/authenticate/complete` - Complete passkey authentication

#### Credential Management
- `GET /api/v1/passkey/credentials` - List user's passkeys
- `DELETE /api/v1/passkey/credentials/{credential_id}` - Delete a passkey

### WebAuthn Service

The `WebAuthnService` class handles:
- Challenge generation and storage
- Registration options creation
- Authentication options creation
- Credential verification (attestation and assertion)
- Cryptographic signature validation

## 🚀 Quick Start

### 1. Start Services

```bash
# Start PostgreSQL and Redis
docker compose up -d postgres redis

# Install dependencies
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the application
uvicorn main:app --reload
```

### 2. Test with Frontend Demo

```bash
# Start the full demo environment
./scripts/test-passkey-demo.sh

# Or manually start frontend
docker compose --profile demo up -d frontend
```

Visit http://localhost:8080 for the interactive demo.

### 3. Manual API Testing

```bash
# 1. Register a user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"password123"}'

# 2. Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'

# 3. Begin passkey registration (requires token)
curl -X POST "http://localhost:8000/api/v1/passkey/register/begin" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser"}'

# 4. Begin passkey authentication
curl -X POST "http://localhost:8000/api/v1/passkey/authenticate/begin" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser"}'
```

## 🔧 Configuration

Add to your `.env` file:

```env
# Passkey/WebAuthn settings
PASSKEY_RP_ID="localhost"                    # Your domain (localhost for dev)
PASSKEY_RP_NAME="Your App Name"             # Display name for your app
PASSKEY_CHALLENGE_TIMEOUT="300"             # Challenge timeout in seconds
```

For production:
```env
PASSKEY_RP_ID="yourdomain.com"
PASSKEY_RP_NAME="Your Production App"
```

## 🌐 Frontend Integration

### WebAuthn Registration Flow

```javascript
// 1. Begin registration
const response = await fetch('/api/v1/passkey/register/begin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'user' })
});
const options = await response.json();

// 2. Convert challenge and user.id from base64url
const createOptions = {
    publicKey: {
        ...options,
        challenge: base64URLDecode(options.challenge),
        user: {
            ...options.user,
            id: base64URLDecode(options.user.id)
        }
    }
};

// 3. Create credential
const credential = await navigator.credentials.create(createOptions);

// 4. Complete registration
await fetch('/api/v1/passkey/register/complete', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
        id: credential.id,
        rawId: base64URLEncode(credential.rawId),
        response: {
            attestationObject: base64URLEncode(credential.response.attestationObject),
            clientDataJSON: base64URLEncode(credential.response.clientDataJSON)
        },
        type: credential.type
    })
});
```

### WebAuthn Authentication Flow

```javascript
// 1. Begin authentication
const response = await fetch('/api/v1/passkey/authenticate/begin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'user' }) // optional for usernameless
});
const options = await response.json();

// 2. Convert challenge
const getOptions = {
    publicKey: {
        ...options,
        challenge: base64URLDecode(options.challenge)
    }
};

// 3. Get credential
const assertion = await navigator.credentials.get(getOptions);

// 4. Complete authentication
const authResponse = await fetch('/api/v1/passkey/authenticate/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        id: assertion.id,
        rawId: base64URLEncode(assertion.rawId),
        response: {
            authenticatorData: base64URLEncode(assertion.response.authenticatorData),
            clientDataJSON: base64URLEncode(assertion.response.clientDataJSON),
            signature: base64URLEncode(assertion.response.signature)
        },
        type: assertion.type
    })
});

const result = await authResponse.json();
// result.access_token contains JWT for authenticated requests
```

## 🧪 Testing

### Unit Tests

```bash
# Run passkey-specific tests
python -m pytest tests/test_passkey.py -v

# Run all tests
python -m pytest tests/ -v
```

### Integration Testing

The included demo script tests the complete flow:

```bash
./scripts/test-passkey-demo.sh
```

This script:
1. Starts all required services
2. Tests user registration and login
3. Tests passkey registration flow
4. Tests passkey authentication flow
5. Launches the frontend demo

### Browser Testing

1. Open http://localhost:8080
2. Use the interactive demo to test:
   - User registration
   - Traditional login
   - Passkey registration
   - Passkey authentication
   - Credential management

**Requirements for passkey testing:**
- Modern browser (Chrome 67+, Edge 18+, Safari 14+, Firefox 60+)
- HTTPS (or localhost for testing)
- Biometric device (Touch ID, Face ID, Windows Hello) or security key

## 🔒 Security Considerations

### Implementation Details

1. **Challenge Security**: 
   - 32-byte cryptographically secure random challenges
   - Challenges stored temporarily (5-minute expiration)
   - Single-use challenges

2. **Signature Verification**:
   - ECDSA P-256 signature validation
   - Authenticator data verification
   - Client data JSON validation

3. **Replay Protection**:
   - Sign counter monotonic validation
   - Challenge uniqueness enforcement

4. **Origin Validation**:
   - Strict origin checking
   - RP ID validation against expected domain

### Production Checklist

- [ ] Use HTTPS in production
- [ ] Set correct `PASSKEY_RP_ID` (your domain)
- [ ] Implement proper challenge storage (Redis recommended)
- [ ] Configure CORS properly for your frontend domain
- [ ] Monitor sign counter for cloned authenticator detection
- [ ] Implement rate limiting on authentication endpoints
- [ ] Set up proper logging for security events

## 🐛 Troubleshooting

### Common Issues

1. **"WebAuthn not supported"**
   - Ensure modern browser
   - Use HTTPS (or localhost for dev)
   - Check if biometric device is available

2. **"Challenge mismatch"**
   - Challenges expire after 5 minutes
   - Ensure proper base64url encoding/decoding
   - Check challenge storage mechanism

3. **"Origin validation failed"**
   - Verify `PASSKEY_RP_ID` matches your domain
   - Ensure frontend origin matches expected origin

4. **"Signature verification failed"**
   - Check authenticator data parsing
   - Verify CBOR public key format
   - Ensure proper signature format

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL="DEBUG"
DEBUG="true"
```

## 📚 Resources

- [W3C WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [FIDO Alliance](https://fidoalliance.org/)
- [WebAuthn.guide](https://webauthn.guide/)
- [MDN WebAuthn API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)

## 🤝 Contributing

When contributing to passkey functionality:

1. Ensure all tests pass: `pytest tests/test_passkey.py`
2. Test with the frontend demo
3. Verify security considerations are met
4. Update documentation for any API changes
5. Test on multiple browsers/devices when possible

## 📄 License

This implementation is part of the FastAPI Enterprise Template and follows the same MIT license.