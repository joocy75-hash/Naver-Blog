#!/usr/bin/env python3
"""
Session Validation Script
Check session validity and expiry status
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security.session_manager import SecureSessionManager


def validate_session(session_name: str):
    """Validate session and show expiry info"""

    print(f"Validating session: {session_name}")
    print("-" * 60)

    manager = SecureSessionManager()

    # Check file exists
    session_file = Path(f"data/sessions/{session_name}.session.encrypted")
    if not session_file.exists():
        print(f"❌ Session file not found: {session_file}")
        return False

    print(f"✅ Session file exists: {session_file}")
    print(f"   Size: {session_file.stat().st_size:,} bytes")
    print(f"   Modified: {datetime.fromtimestamp(session_file.stat().st_mtime)}")

    # Load and validate
    try:
        session_data = manager.load_session(session_name)
        print(f"✅ Session decrypted successfully")

        # Check timestamps
        created_at = datetime.fromisoformat(session_data.get("created_at", ""))
        last_renewed = datetime.fromisoformat(session_data.get("last_renewed_at", str(created_at)))

        print(f"\n📅 Session Timeline:")
        print(f"   Created: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Last Renewed: {last_renewed.strftime('%Y-%m-%d %H:%M:%S')}")

        # Calculate expiry
        max_age_days = int(os.getenv("SESSION_MAX_AGE_DAYS", "7"))
        expiry_date = last_renewed + timedelta(days=max_age_days)
        days_until_expiry = (expiry_date - datetime.now()).days

        print(f"   Expiry Date: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # Status indicator
        if days_until_expiry < 0:
            print(f"   Status: ❌ EXPIRED ({abs(days_until_expiry)} days ago)")
            print(f"\n⚠️  Action Required: Re-login using manual_login_clipboard.py")
            return False
        elif days_until_expiry <= 1:
            print(f"   Status: 🔴 CRITICAL ({days_until_expiry} days left)")
            print(f"\n⚠️  Warning: Session expires soon! Re-login recommended.")
        elif days_until_expiry <= 3:
            print(f"   Status: 🟡 WARNING ({days_until_expiry} days left)")
        else:
            print(f"   Status: ✅ VALID ({days_until_expiry} days left)")

        # Cookie count
        cookies = session_data.get("cookies", [])
        print(f"\n🍪 Cookies: {len(cookies)} stored")

        # Storage
        origins = session_data.get("origins", [])
        print(f"📦 Storage Origins: {len(origins)}")

        return True

    except Exception as e:
        print(f"❌ Session validation failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate-session.py <session_name>")
        print("Example: python validate-session.py wncksdid0750_clipboard")
        sys.exit(1)

    session_name = sys.argv[1]
    success = validate_session(session_name)

    sys.exit(0 if success else 1)
