from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_settings():
    try:
        sb = get_supabase()
        res = sb.table('app_settings').select('*').eq('id', 1).single().execute()
        return res.data or {}
    except Exception:
        return {}
