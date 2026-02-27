# app/utils/shortcode.py
import random
import string

# Our alphabet — 62 characters (a-z, A-Z, 0-9)
# We avoid similar-looking characters like 0/O, 1/l to reduce confusion
ALPHABET = string.ascii_letters + string.digits

def generate_short_code(length: int = 6) -> str:
    """Generate a random short code like 'aB3xZ9'"""
    return "".join(random.choices(ALPHABET, k=length))