from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    Uses service role key for admin operations.
    """
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )
    return supabase

def get_supabase_anon_client() -> Client:
    """
    Create and return a Supabase client with anon key.
    Use for user-facing operations with RLS.
    """
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    return supabase
