import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SECRET_KEY   = os.environ.get('SECRET_KEY', 'mfg-app-secret-2024')

IMAGE_BUCKET      = 'product-images'
LOW_STOCK_DEFAULT = 10
