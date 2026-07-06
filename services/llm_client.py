import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def ask_llm(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        return "OPENROUTER_API_KEY bulunamadı."

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "meta-llama/llama-3.2-3b-instruct:free",
        "messages": [
            {
                "role": "system",
                "content": "You are StyleScout, a helpful fashion assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        # Timeout süresini 10 saniyeye çektik ki terminal dakikalarca kilitli kalmasın
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10
        )

        print("Status Code:", response.status_code)
        print("Response:", response.text)

        if response.status_code != 200:
            return f"API Error: {response.status_code}"

        return response.json()["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        print("HATA: API isteği zaman aşımına uğradı (10 saniye).")
        return "API Zaman Aşımı Hatası."
    except requests.exceptions.RequestException as e:
        print(f"HATA: İstek sırasında bir sorun oluştu: {e}")
        return "API Bağlantı Hatası."
