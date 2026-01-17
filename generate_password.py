#!/usr/bin/env python3
"""
Password hash generator for Unraid Monitor Web UI.

This script generates a bcrypt password hash that can be used as the
WEB_PASSWORD environment variable for secure Web UI authentication.

Usage:
    python generate_password.py [password]
    
    If no password is provided, you'll be prompted to enter one securely.

Example:
    $ python generate_password.py
    Enter password: ••••••••
    Confirm password: ••••••••
    
    Generated password hash:
    $2b$12$abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yz56
    
    Add to docker-compose.yml:
    environment:
      - WEB_PASSWORD=$2b$12$abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yz56
    
    Or export as environment variable:
    export WEB_PASSWORD='$2b$12$abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yz56'
"""

import sys
import getpass
from passlib.context import CryptContext

# Password hashing context (same as in Web UI)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_hash(password: str) -> str:
    """Generate bcrypt hash for password."""
    return pwd_context.hash(password)


def main():
    print("=" * 70)
    print("Unraid Monitor - Password Hash Generator")
    print("=" * 70)
    print()
    
    # Get password from command line or prompt
    if len(sys.argv) > 1:
        password = sys.argv[1]
        print("⚠️  WARNING: Password provided as command line argument.")
        print("   This may be visible in shell history!")
        print()
    else:
        # Prompt for password securely
        try:
            password = getpass.getpass("Enter password: ")
            confirm = getpass.getpass("Confirm password: ")
            
            if password != confirm:
                print("\n❌ Error: Passwords do not match!", file=sys.stderr)
                sys.exit(1)
            
            if len(password) < 8:
                print("\n⚠️  WARNING: Password is less than 8 characters.")
                print("   Consider using a stronger password.")
                print()
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)
    
    # Generate hash
    print("Generating bcrypt hash (this may take a few seconds)...")
    hash_value = generate_hash(password)
    
    # Display results
    print("\n" + "=" * 70)
    print("✅ Password hash generated successfully!")
    print("=" * 70)
    print()
    print("Generated hash:")
    print(hash_value)
    print()
    print("Usage in docker-compose.yml:")
    print("-" * 70)
    print("environment:")
    print(f"  - WEB_PASSWORD={hash_value}")
    print()
    print("Or as environment variable (Bash/Zsh):")
    print("-" * 70)
    print(f"export WEB_PASSWORD='{hash_value}'")
    print()
    print("Or as environment variable (PowerShell):")
    print("-" * 70)
    print(f"$env:WEB_PASSWORD='{hash_value}'")
    print()
    print("⚠️  IMPORTANT:")
    print("  - Keep this hash secure (treat it like a password)")
    print("  - Don't commit it to version control")
    print("  - Use a .env file or Docker secrets for production")
    print()
    print("Testing:")
    print("  - Leave WEB_PASSWORD empty/unset for no authentication")
    print("  - Use any username with the password you just set")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
