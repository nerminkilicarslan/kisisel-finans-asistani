import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

_model = None
_configured_key: str = ""


def _get_model():
    global _model, _configured_key
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "buraya_api_anahtarinizi_yazin":
        return None
    if api_key != _configured_key:
        genai.configure(api_key=api_key)
        # gemini-2.0-flash kullan - stabil ve erişilebilir model
        _model = genai.GenerativeModel("gemini-2.0-flash")
        _configured_key = api_key
    return _model


def ask_assistant(question: str, context: dict) -> str:
    model = _get_model()
    if model is None:
        return (
            "⚠️ Gemini API anahtarı bulunamadı veya geçersiz. "
            "Proje kök dizinindeki `.env` dosyasına `GEMINI_API_KEY=<anahtarınız>` satırını ekleyin."
        )

    prompt = f"""Sen deneyimli bir kişisel finans danışmanısın. Türkiye'de yaşayan kullanıcılara
Türk Lirası (TL) cinsinden somut, uygulanabilir öneriler veriyorsun.

=== KULLANICININ BU AYKİ FİNANSAL TABLOSU ===
• Toplam Gelir   : {context.get('income', 0):,.0f} ₺
• Toplam Gider   : {context.get('expense', 0):,.0f} ₺
• Net Tasarruf   : {context.get('savings', 0):,.0f} ₺
• Tasarruf Oranı : %{context.get('savings_rate', 0):.1f}
• En Çok Harcama : {context.get('top_category', '-')} kategorisi

=== SON 3 AY GİDER KATEGORİLERİ ===
{context.get('category_summary', 'Veri yok')}

=== KULLANICININ SORUSU ===
{question}

Yanıtın:
- Türkçe ve samimi bir dille olsun
- Sayısal verilerden (kullanıcının kendi rakamlarından) yola çık
- Somut ve uygulanabilir 2-3 öneri ver
- Gereksiz uzatma, net ol
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        err = str(e)
        if "RESOURCE_EXHAUSTED" in err or "quota" in err.lower() or "429" in err:
            return (
                "⚠️ **Gemini API kotası doldu!**\n\n"
                "Ücretsiz tier'ın günlük istek limiti aşılmış. Seçenekler:\n"
                "• Yarın tekrar deneyin (sıfırlanacak)\n"
                "• [Google AI Studio](https://aistudio.google.com) → Ücretli plan seçin\n\n"
                "Not: Özellikle test sırasında hızlı soru butonlarına fazla tıklama quota'yı hızlı tüketiyor."
            )
        return f"❌ API hatası: {e}"


def analyze_spending_pattern(transactions_summary: str) -> str:
    model = _get_model()
    if model is None:
        return "⚠️ API anahtarı gerekli."

    prompt = f"""Aşağıdaki harcama verisini analiz et ve 3 madde halinde kısa özet yaz:

{transactions_summary}

Türkçe, maddeler halinde (1. 2. 3.) yaz. Her madde en fazla 2 cümle."""
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"❌ {e}"
