"""
Türk banka ekstresi tarzında etiketli eğitim verisi üretir.
Gerçek banka hareketi açıklama formatları baz alınmıştır:
  - POS harcaması: "POS HARCAMA MİGROS MARKET A.Ş."
  - Fatura ödemesi: "FATURA ÖDEME BEDAŞ ELEKTRİK"
  - EFT/Havale: "EFT MAAŞ ÖDEMESİ"
  - Online: "3D SECURE YEMEKSEPETI"
"""
import random
import pandas as pd
import numpy as np

random.seed(0)
np.random.seed(0)

# ── Merchant / açıklama şablonları (kategori başına) ──────────────────────────

CORPUS: dict[str, list[str]] = {
    "Market": [
        "MİGROS MARKET", "MİGROS SANAL MARKET", "MİGROS JET",
        "A101 MAĞAZACILIK", "A-101 SATIŞ", "A101",
        "BİM MAĞAZALAR", "BİM A.Ş.", "BİM MARKET",
        "ŞOK MARKET", "ŞOK MAĞAZACILIK", "ŞOK A.Ş.",
        "CARREFOURSA", "CARREFOUR EXPRESS", "CARREFOUR SA",
        "METRO GROSMARKET", "METRO CASH CARRY",
        "KILER MARKET", "KILER A.Ş.",
        "DİA SÜPERMARKET", "HAKMAR MARKET", "TARÇIN MARKET",
        "MACRO CENTER", "SPAR MARKET", "ÖZDILEK MARKET",
        "TANSAS MARKET", "REAL MARKET", "ONUR MARKET",
        "GETİR MARKET", "TRENDYOL MARKET", "HEPSIBURADA MARKET",
        "YAŞAR MARKET", "KÖFTECI YUSUF", "GIDA MARKET",
        "SÜPERMARKET ÖDEME", "MARKET ALIŞ", "GIDA ALIŞ",
        "ELEMAN MARKET", "ÇİFT TAÇ MARKET", "ARAZ MARKET",
    ],
    "Fatura": [
        "BEDAŞ ELEKTRİK FATURA", "AYEDAŞ ELEKTRİK",
        "BAŞKENT EDAŞ ELEKTRİK", "TOROSLAR EDAŞ",
        "GEDİZ ELEKTRİK DAĞITIM", "AKEDAŞ",
        "ELEKTRİK FATURA ÖDEMESİ", "ELEKTRİK ABONELIĞI",
        "İGDAŞ DOĞALGAZ", "BAĞCILAR GAZ",
        "EGE GAZ DOĞALGAZ", "GAZDAŞ",
        "DOĞALGAZ FATURA", "GAZ FATURA ÖDEMESİ",
        "İSKİ SU FATURA", "ASKİ SU FATURA",
        "BUSKİ SU ÖDEME", "MESKİ SU",
        "SU FATURA ÖDEMESİ", "SU ABONELIĞI",
        "TÜRK TELEKOM FATURA", "TTNET İNTERNET",
        "TÜRK TELEKOM MOBİL", "TÜRK TELEKOM FİBER",
        "TURKCELL FATURA", "TURKCELL SUPERONLINE",
        "VODAFONE TÜRKİYE FATURA", "VODAFONE KABLO",
        "SUPERONLINE İNTERNET", "KABLONET FATURA",
        "DSL İNTERNET FATURA", "ADSL FATURA",
        "FATURA ÖDEME", "ABONELIK ÜCRETİ",
        "UYDU FATURA", "KABLOTV ÖDEME",
    ],
    "Yemek": [
        "YEMEKSEPETI", "YEMEK SEPETİ ONLINE",
        "GETİR YEMEK", "GETİR EKSPRES",
        "TRENDYOL YEMEK", "TRENDYOL GO",
        "MC DONALDS TÜRKİYE", "MCDONALDS",
        "BURGER KING TÜRKİYE", "BURGERKING",
        "PIZZA HUT TÜRKİYE", "PIZZAHUT ONLINE",
        "DOMINO'S PIZZA", "DOMINOS ONLINE",
        "SUBWAY TÜRKİYE", "KFC TÜRKİYE",
        "POPEYES TÜRKİYE", "FIVE GUYS",
        "STARBUCKS COFFEE", "STARBUCKS TÜRKİYE",
        "KAHVE DÜNYASI", "CARIBOU COFFEE",
        "GLORIA JEAN'S COFFEES", "COSTA COFFEE",
        "SİMİT SARAYI", "BÖREKÇI USTA",
        "DÖNER EXPRESS", "TAVUK DÜNYASI",
        "RESTORAN ÖDEME", "CAFE ÖDEMESİ",
        "LOKANTA HARCAMA", "YEMEK HARCAMA",
        "PİZZA SIPARIŞI", "PAKET SERVİS",
        "IŞKEMBECI", "LAHMACUNCU",
        "NUSRET BURGER", "NUSR-ET",
        "STEAKHOUSE", "BALIK LOKANTASI",
    ],
    "Ulaşım": [
        "İSTANBULKART YÜKLEME", "İSTANBUL KART",
        "IETT BİLET", "İETT ULAŞIM",
        "İSTANBUL METRO KARTLI", "METRO İSTANBUL",
        "MARMARAY BİLET", "METROBÜS",
        "ANKARA EGO KART", "ANKARAKART",
        "EGO ANKARA ULAŞIM", "BAŞKENTRAY",
        "İZMİRİM KART", "ESHOT İZMİR",
        "İZMİR METRO", "TRAMVAY BİLET",
        "UBER TÜRKİYE", "UBER YAZILIM",
        "BİTAKSİ", "BOLT TÜRKİYE",
        "OPET AKARYAKIT", "SHELL OİL TÜRKİYE",
        "BP AKARYAKIT", "TOTAL OİL TÜRKİYE",
        "MOBİL AKARYAKIT", "PETKİM",
        "LPG DOLUM", "LPG AKARYAKIT",
        "OTOGAR BİLET", "ŞEHİRLERARASI OTOBÜS",
        "TÜRK HAVAYOLLARI", "THY BİLET",
        "PEGASUS HAVAYOLLARI", "SUNEXPRESS",
        "TREN BİLETİ TCDD", "TCDD E-BİLET",
        "ISPARK OTOPARK", "OTOPARK ÜCRETİ",
        "ARAÇ KİRALAMA", "RENT A CAR",
    ],
    "Eğlence": [
        "NETFLİX TÜRKİYE", "NETFLIX ABONELIK",
        "SPOTIFY TÜRKİYE", "SPOTIFY PREMIUM",
        "YOUTUBE PREMIUM", "GOOGLE ONE",
        "APPLE TV PLUS", "APPLE MUSIC",
        "AMAZON PRIME TÜRKİYE", "AMAZON VIDEO",
        "BLUTV", "PUHU TV",
        "GAIN TV", "TABII PLATFORMU",
        "D-SMART TV", "DIGITURK",
        "BEİN SPORTS CONNECT", "S SPORT PLUS",
        "CİNEMAXİMUM BİLET", "CINEMAXIMUM",
        "CGV MARS SİNEMA", "SİNEMA BİLETİ",
        "BİLETİX", "BİLETBUL",
        "PASSO BİLET", "TICKET ONLINE",
        "STEAM TÜRKİYE", "STEAM OYUN",
        "PLAYSTATION STORE", "XBOX GAMEPASS",
        "EPİC GAMES", "RIOT GAMES",
        "KONSER BİLETİ", "STADYUM BİLET",
        "TEMA PARK GİRİŞ", "LUNAPARK",
        "BOWLING SALONU", "GO KART",
        "ESCAPE ROOM", "LAZER TAG",
    ],
    "Sağlık": [
        "ECZANE ÖDEMESİ", "ECZANESI REÇETE",
        "ACİBADEM HASTANESİ", "ACİBADEM SAĞLIK",
        "MEMORIAL HASTANESİ", "MEMORIAL SAĞLIK",
        "MEDİCANA HASTANESİ", "MEDICANA",
        "FLORENCE NİGHTİNGALE HASTANE",
        "GÜVEN HASTANESİ", "BAYINDIR HASTANESİ",
        "NP İSTANBUL HASTANE", "LOKMAN HEKİM",
        "ÖZEL KLİNİK ÖDEMESİ", "ÖZEL HASTANE",
        "DEVLET HASTANESİ", "ŞEHİR HASTANESİ",
        "DİŞ HEKİMİ ÜCRETİ", "DİŞ KLİNİĞİ",
        "GÖZ DOKTORU MUAYENESİ", "GÖZ KLİNİĞİ",
        "CİLT KLİNİĞİ", "DERMATOLOJİ",
        "LABORATUVAR TAHLIL", "TAHLIL MERKEZİ",
        "MR ÇEKIM ÜCRETİ", "RÖNTGEN",
        "FİZYOTERAPİ SEANS", "MASAJ TERAPİ",
        "DİYETİSYEN", "PSİKOLOG SEANS",
        "İLAÇ ÖDEME", "REÇETE İLAÇ",
        "MEDİKAL MALZEME", "TIBBİ CIHAZ",
        "SGK ÖZEL SAĞLIK", "TAMAMLAYICI SİGORTA",
    ],
    "Giyim": [
        "LCW LC WAİKİKİ", "LC WAİKİKİ MAĞAZA",
        "ZARA TÜRKİYE", "ZARA ONLINE",
        "H&M TÜRKİYE", "H M MAĞAZACILIK",
        "MANGO TÜRKİYE", "MANGO ONLINE",
        "KOTON MAĞAZACILIK", "KOTON ONLINE",
        "DEFACTO TÜRKİYE", "DEFACTO ONLINE",
        "PENTİ ÇORAP", "PENTİ MAĞAZA",
        "SÜVARI AYAKKABI", "FLO AYAKKABI",
        "ALDO SHOES TÜRKİYE", "BAMBI AYAKKABI",
        "BATA AYAKKABI", "HOTIÇ",
        "YKM BÜYÜK MAĞAZA", "BOYNER",
        "MARKS SPENCER TÜRKİYE", "GAP TÜRKİYE",
        "RESERVED TÜRKİYE", "CROPP",
        "PULL BEAR TÜRKİYE", "BERSHKA",
        "STRADIVARIUS", "MASSIMO DUTTI",
        "VAKKO TEKSTIL", "PIERRE CARDIN",
        "BEYMEN", "NETWORK MODA",
        "MONDİ", "İPEKYOLU",
        "GİYİM ÖDEME", "TEKSTIL ALIŞ",
        "ONLINE GİYİM", "SPOR GİYİM",
    ],
    "Eğitim": [
        "UDEMY ONLINE KURS", "UDEMY",
        "COURSERA ABONELIK", "COURSERA",
        "LINKEDIN LEARNING", "SKILLSHARE",
        "DUOLINGO PLUS", "BABBEL DİL",
        "İNGİLİZCE KURSU ÖDEMESİ",
        "YABANCI DİL KURSU",
        "TÖMER DİL MERKEZİ", "DİLKUR",
        "DERSHANE KAYIT", "DERSHANE ÖDEMESİ",
        "ÖZEL DERS ÖDEMESİ",
        "ÜNİVERSİTE HARCI", "ÜNİVERSİTE KAYIT",
        "MEB SINAV ÜCRETİ", "ÖSYM BAŞVURU",
        "YDS SINAV", "IELTS SINAV",
        "KİTAP ÖDEME", "KİTAPYURDU",
        "D&R KİTAP MÜZIK", "PANDORA KİTAP",
        "İDEFİX KİTAP", "TRENDYOL KİTAP",
        "KIRTASİYE ÖDEME", "KIRTASİYE MALZEME",
        "OKUL MALZEMESİ", "EĞITIM MATERYALİ",
        "SERTİFİKA PROGRAMI", "UZAKTAN EĞİTİM",
        "e-OKUL ÖDEME", "MEB ÖDEME",
    ],
    "Kira": [
        "KİRA ÖDEMESİ", "KİRA EFT",
        "KONUT KİRASI", "EV KİRASI",
        "KİRACI ÖDEMESİ", "KİRA HAVALE",
        "İŞYERİ KİRASI", "DÜKKAN KİRASI",
        "OFİS KİRASI", "DEPO KİRASI",
        "AİDAT ÖDEMESİ", "SİTE AİDATI",
        "YÖNETİM AİDATI", "APARTMAN AİDATI",
        "BLOK AİDAT", "KİRA+AİDAT",
        "YURT ÜCRETI", "YURT KİRASI",
        "PANSION ÖDEMESİ",
    ],
    "Diğer": [
        "ATM ÇEKİMİ", "PARA ÇEKİMİ ATM",
        "KREDİ KARTI ÖDEMESİ", "KREDİ KARTI BORÇ",
        "TRENDYOL ALIŞVERİŞ", "TRENDYOL ONLINE",
        "HEPSİBURADA ONLINE", "N11 ALIŞVERİŞ",
        "AMAZON TÜRKİYE", "ALİEXPRESS",
        "TEKNOSAFARİ ELEKTRONİK", "VATAN BİLGİSAYAR",
        "MEDİA MARKT TÜRKİYE", "SAMSUNG TÜRKİYE",
        "APPLE TÜRKİYE", "HUAWEI TÜRKİYE",
        "SIGORTA ÖDEMESİ", "KASKO ÖDEMESI",
        "TRAFIK SİGORTA", "DASK SİGORTA",
        "NOTER ÜCRETİ", "AVUKAT ÜCRETİ",
        "VERGİ ÖDEMESİ", "MTV ÖDEME",
        "EHLİYET SINAV", "ARAÇ MUAYENE",
        "BANKA MASRAFI", "KOMİSYON",
        "KUYUMCU", "ALTIN ALIŞ",
        "ÇIÇEKÇI", "HEDİYE ALIŞ",
        "KONUT SİGORTASI", "HAYAT SİGORTASI",
    ],
}

# Gerçek banka ekstresi önekleri
PREFIXES = [
    "POS HARCAMA", "KART HARCAMASI", "YURT İÇİ İŞLEM",
    "3D SECURE ÖDEMESİ", "ONLINE ALIŞVERİŞ",
    "FATURA ÖDEME", "OTOMATİK ÖDEME",
    "EFT", "HAVALE", "FAST ÖDEME",
    "",  # Önek olmadan (sade açıklama)
    "",
    "",  # Önek olmadan daha yaygın olsun
]

# Türk şirket ekleri
SUFFIXES = ["A.Ş.", "LTD.ŞTİ.", "A.Ş. TÜRKİYE", ""]

# Tutar dağılımları (kategori → (min, max, typical, std))
AMOUNT_DIST: dict[str, tuple] = {
    "Market":   (30,   3500, 350,  200),
    "Fatura":   (80,   2500, 550,  300),
    "Yemek":    (20,    800, 120,   80),
    "Ulaşım":   (10,   1500, 200,  150),
    "Eğlence":  (15,    800, 120,   80),
    "Sağlık":   (25,   5000, 400,  500),
    "Giyim":    (80,   8000, 600,  700),
    "Eğitim":   (30,   6000, 400,  500),
    "Kira":     (3000,35000,9500, 3000),
    "Diğer":    (10,   5000, 300,  400),
}


def _random_amount(category: str) -> float:
    mn, mx, mu, sigma = AMOUNT_DIST[category]
    amount = np.random.normal(mu, sigma)
    return round(float(np.clip(amount, mn, mx)), 2)


def _augment(desc: str) -> str:
    """Gürültü ekleyerek gerçek banka ekstresi formatına benzet."""
    variations = [
        desc,
        desc.lower(),
        desc.title(),
        desc + " " + random.choice(SUFFIXES) if random.random() > 0.6 else desc,
        random.choice(PREFIXES) + " " + desc if random.random() > 0.5 else desc,
    ]
    result = random.choice(variations).strip()
    # Zaman zaman baştaki/sondaki boşluk veya çift boşluk (banka kayıtlarında olur)
    if random.random() > 0.85:
        result = "  " + result
    return result.strip()


def build_dataset(n_per_category: int = 900) -> pd.DataFrame:
    """
    Her kategori için n_per_category örnek üretir.
    Varsayılan: 900 × 10 kategori = 9 000 satır
    """
    rows = []
    for category, templates in CORPUS.items():
        mn, mx, mu, sigma = AMOUNT_DIST[category]
        for _ in range(n_per_category):
            base = random.choice(templates)
            desc = _augment(base)
            amount = _random_amount(category)
            rows.append({"description": desc, "amount": amount, "category": category})

    df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = build_dataset()
    df.to_csv("data/training_data.csv", index=False)
    print(f"Veri seti: {len(df)} satır, {df['category'].nunique()} kategori")
    print(df["category"].value_counts())
