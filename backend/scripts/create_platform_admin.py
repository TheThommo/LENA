#!/usr/bin/env python3
"""
Create Platform Admin — one-shot CLI script.

Creates (or promotes) a LENA platform_admin user who can access /admin.html
dashboards. Run once, ideally before demo.

Usage (local venv — needs SUPABASE_URL & SUPABASE_SERVICE_KEY in env):
    python backend/scripts/create_platform_admin.py \
        --email admin@lena.ai --password S0m3Str0ngPa55!

Usage (Railway production):
    railway run python backend/scripts/create_platform_admin.py \
        --email admin@lena.ai --password S0m3Str0ngPa55!

DO NOT commit real credentials. Use env vars or CLI args only.
"""

import argparse
import asyncio
import sys
import os

# Allow imports from the backend package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt


async def main(email: str, password: str, name: str) -> None:
    # Lazy imports so env is loaded first
    from app.db.supabase import get_supabase_admin_client
    from app.db.repositories.tenant_repo import TenantRepository
    from app.db.repositories.user_repo import UserRepository, UserTenantRepository
    from app.models import TenantCreate
    from app.models.user import UserCreate, UserTenantCreate
    from app.models.enums import UserRole, PersonaType

    client = get_supabase_admin_client()

    # 1. Ensure a default tenant exists
    tenant = await TenantRepository.get_by_slug("default")
    if not tenant:
        print("Creating default tenant...")
        tenant = await TenantRepository.create(
            TenantCreate(
                name="LENA Platform",
                slug="default",
                domain="lena-research.com",
            )
        )
        if not tenant:
            print("ERROR: Failed to create default tenant. Check Supabase connection.")
            sys.exit(1)
    print(f"Tenant: {tenant.slug} ({tenant.id})")

    # 2. Check if user already exists
    existing = await UserRepository.get_by_email(email)
    if existing:
        print(f"User {email} already exists (id={existing.id}, role={existing.role}).")
        if existing.role != UserRole.PLATFORM_ADMIN:
            print("Promoting to platform_admin...")
            client.table("users").update({"role": "platform_admin"}).eq("id", str(existing.id)).execute()
            # Ensure user_tenants row exists with platform_admin role
            try:
                client.table("user_tenants").upsert({
                    "user_id": str(existing.id),
                    "tenant_id": str(tenant.id),
                    "role": "platform_admin",
                }).execute()
            except Exception as e:
                print(f"Warning: user_tenants upsert failed (may already exist): {e}")
            print(f"Done. {email} is now platform_admin.")
        else:
            print("Already platform_admin. Nothing to do.")
        return

    # 3. Create new user
    print(f"Creating platform_admin user: {email}")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    user_create = UserCreate(
        email=email,
        name=name,
        tenant_id=tenant.id,
        role=UserRole.PLATFORM_ADMIN,
        persona_type=PersonaType.GENERAL,
    )

    user = await UserRepository.create(
        user_create,
        password_hash=password_hash,
        raw_password=password,
    )
    if not user:
        print("ERROR: Failed to create user. Check Supabase logs for FK/auth errors.")
        sys.exit(1)

    # 4. Link user to tenant as platform_admin
    user_tenant = await UserTenantRepository.create(
        UserTenantCreate(
            user_id=user.id,
            tenant_id=tenant.id,
            role=UserRole.PLATFORM_ADMIN,
        )
    )
    if not user_tenant:
        print("WARNING: user_tenants link failed — dashboard auth may not work. Insert manually via SQL.")
    else:
        print(f"user_tenants linked: {user.id} -> {tenant.id}")

    print(f"\nPlatform admin created successfully.")
    print(f"  Email:     {email}")
    print(f"  User ID:   {user.id}")
    print(f"  Tenant ID: {tenant.id}")
    print(f"\nLog in at /admin.html with these credentials.")
    print(f"REMINDER: Set APP_ENV=production and a strong JWT_SECRET_KEY before demo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote a LENA platform admin")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--name", default="Platform Admin", help="Display name (default: Platform Admin)")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    asyncio.run(main(args.email, args.password, args.name))
