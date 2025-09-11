# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # leest .env als ‘ie er is

def get_api_key():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY mist!")
    return key