# test_groq.py

from dotenv import load_dotenv
load_dotenv()

import os
from groq import Groq

def main():
    # 1) Debug: controleer wat er geladen wordt
    key = os.getenv("GROQ_API_KEY", "")
    print("🔑 Loaded key repr:", repr(key))
    print("🔢 Length:", len(key))
    if not key:
        raise RuntimeError("GROQ_API_KEY niet gevonden in env")

    # 2) Init en test-authenticatie
    client = Groq(api_key=key)
    models = client.models.list()
    print(f"✅ Aantal beschikbare modellen: {len(models.data)}")

if __name__ == "__main__":
    main()
