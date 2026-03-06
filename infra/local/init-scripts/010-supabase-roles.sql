-- Roles expected by Supabase/Auth/PostgREST stack.
-- This script is safe to run on initialization.

-- Ensure schemas exist even if this script runs before the main schema script.
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOINHERIT;
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOINHERIT;
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOINHERIT BYPASSRLS;
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticator') THEN
    CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD 'authenticator-dev-password';
  END IF;
END $$;

GRANT anon TO authenticator;
GRANT authenticated TO authenticator;
GRANT service_role TO authenticator;

GRANT USAGE ON SCHEMA public, meta, bronze, silver, gold TO anon, authenticated, service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public, meta, bronze, silver, gold TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public, meta, bronze, silver, gold
GRANT SELECT ON TABLES TO anon, authenticated, service_role;
