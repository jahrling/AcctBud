#!/usr/bin/env bash
# Generate a VAPID keypair for Web Push.
# Run once, paste the output into your .env file.
set -euo pipefail

python3 -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print(f'VAPID_PRIVATE_KEY={v.private_pem().decode().strip()}')
print()
raw = v.public_key.public_bytes(
    encoding=__import__('cryptography').hazmat.primitives.serialization.Encoding.X962,
    format=__import__('cryptography').hazmat.primitives.serialization.PublicFormat.UncompressedPoint,
)
import base64
print(f'VAPID_PUBLIC_KEY={base64.urlsafe_b64encode(raw).rstrip(b\"=\").decode()}')
"
