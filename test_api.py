# test_groq.py

import os
from groq import Groq

def main():
    # Haal je key uit de env
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY niet gevonden in env")

    # Init en test
    client = Groq(api_key=key)
    models = client.models.list()
    print(f"✅ Aantal beschikbare modellen: {len(models.data)}")

if __name__ == "__main__":
    main()

