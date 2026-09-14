import telebot
import pandas as pd
import requests
import io
import re
from flask import Flask, request

TOKEN = "8654296905:AAG18XC5eWq1EiJrYv0AMnXIiXvXI6t6PIs"
EXCEL_URL = "https://raw.githubusercontent.com/killhunter35/Halka-Arz-Botu/main/Halka_Arz_Verileri.xlsx"

# Render site adresin (Kullanıcı adın farklıysa killhunter35 kısmını değiştir)
WEBHOOK_URL = "https://halka-arz-asistani.onrender.com/"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
kullanici_secimleri = {}

def excel_indir(sayfa_adi):
    response = requests.get(EXCEL_URL)
    if response.status_code != 200:
        raise Exception(f"GitHub'a ulaşılamadı (Hata: {response.status_code})")
    return pd.read_excel(io.BytesIO(response.content), sheet_name=sayfa_adi, engine='openpyxl')

def temizle(metin):
    return str(metin).replace('I', 'ı').replace('İ', 'i').replace('Ö', 'ö').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ç', 'ç').replace('Ğ', 'ğ').lower()

def veri_cek(row, arananlar, varsayilan="-"):
    for col in row.keys():
        col_temiz = temizle(col)
        for aranan in arananlar:
            if aranan in col_temiz:
                val = row[col]
                return str(val) if pd.notna(val) and str(val).strip() != "" else varsayilan
    return varsayilan

@bot.message_handler(commands=['start', 'help'])
def karsilama(message):
    mesaj = (
        "👋 Halka Arz Asistanına Hoş Geldin!\n\n"
        "Mevcut Komutlar:\n"
        "🚀 /yaklasanlar - Yaklaşan arzları listeler.\n"
        "🔍 /sorgula FirmaAdı - İstediğin firmanın detaylarını getirir.\n"
        "🎯 /halkaarz FirmaAdı - Şirket hakkında detaylı interaktif menüyü açar."
    )
    bot.reply_to(message, mesaj)

@bot.message_handler(commands=['yaklasanlar'])
def yaklasanlar_komutu(message):
    bot.reply_to(message, "⏳ Veriler GitHub veritabanından çekiliyor, lütfen bekle...")
    try:
        df = excel_indir("Yaklaşan Arzlar")
        if df.empty:
            bot.reply_to(message, "Şu an sistemde yaklaşan bir halka arz bulunmuyor.")
            return

        yanit = "🚀 **YAKLAŞAN HALKA ARZLAR** 🚀\n\n"
        for index, row in df.iterrows():
            firma = veri_cek(row, ['firma adı', 'şirket'])
            tarih = veri_cek(row, ['tarih'])
            fiyat = veri_cek(row, ['fiyat'])
            yanit += f"🔹 *{firma}*\n🗓 Tarih: {tarih}\n💰 Fiyat: {fiyat}\n\n"

        bot.reply_to(message, yanit, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata oluştu: {e}")

@bot.message_handler(commands=['sorgula'])
def sorgula_komutu(message):
    komut_ve_metin = message.text.split(" ", 1)
    if len(komut_ve_metin) < 2:
        bot.reply_to(message, "⚠️ Lütfen bir firma adı yazın. Örnek: `/sorgula bewen`")
        return

    aranan_kelime = komut_ve_metin[1].lower()
    bot.reply_to(message, f"🔍 '{aranan_kelime}' için aranıyor...")

    try:
        df_yaklasan = excel_indir("Yaklaşan Arzlar")
        df_tamamlanan = excel_indir("Tamamlanan Arzlar")
        df_tum = pd.concat([df_yaklasan, df_tamamlanan], ignore_index=True)
        df_tum['Firma Adı'] = df_tum['Firma Adı'].astype(str)
        bulunanlar = df_tum[df_tum['Firma Adı'].str.lower().str.contains(aranan_kelime, na=False)]

        if bulunanlar.empty:
            bot.reply_to(message, "❌ Aradığınız kriterlere uygun firma bulunamadı.")
            return

        yanit = "✅ **Bulunan Sonuçlar:**\n\n"
        for index, row in bulunanlar.iterrows():
            firma = veri_cek(row, ['firma adı', 'şirket'])
            tarih = veri_cek(row, ['tarih'])
            fiyat = veri_cek(row, ['fiyat'])
            lot = veri_cek(row, ['lot', 'pay', 'miktar'])
            dagitim = veri_cek(row, ['dağıtım'])
            islem_tarihi = veri_cek(row, ['işlem'])

            yanit += (f"🏢 *{firma}*\n"
                      f"🗓 Tarih: {tarih}\n"
                      f"💰 Fiyat: {fiyat}\n"
                      f"📦 Toplam Lot: {lot}\n"
                      f"⚖️ Dağıtım: {dagitim}\n"
                      f"🔔 İlk İşlem Tarihi: {islem_tarihi}\n"
                      f"{'-'*20}\n")
        bot.reply_to(message, yanit, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata oluştu: {e}")

@bot.message_handler(commands=['halkaarz', 'halka_arz'])
def halkaarz_komutu(message):
    komut_ve_metin = message.text.split(" ", 1)
    if len(komut_ve_metin) < 2:
        bot.reply_to(message, "⚠️ Lütfen firma adını yazın. Örnek: `/halkaarz teknika`")
        return

    aranan_kelime = komut_ve_metin[1].lower()

    try:
        df_yaklasan = excel_indir("Yaklaşan Arzlar")
        df_tamamlanan = excel_indir("Tamamlanan Arzlar")
        df_tum = pd.concat([df_yaklasan, df_tamamlanan], ignore_index=True)
        df_tum['Firma Adı'] = df_tum['Firma Adı'].astype(str)
        bulunanlar = df_tum[df_tum['Firma Adı'].str.lower().str.contains(aranan_kelime, na=False)]

        if bulunanlar.empty:
            bot.reply_to(message, "❌ Sistemde bu isimde bir firma bulunamadı.")
            return

        ilk_firma = bulunanlar.iloc[0]
        firma_adi = veri_cek(ilk_firma, ['firma adı', 'şirket'])

        kullanici_secimleri[message.chat.id] = ilk_firma

        yanit = (f"🎯 **{firma_adi}** ile ilgili ne öğrenmek istiyorsunuz?\n\n"
                 f"Tıklayarak seçin:\n"
                 f"🔹 /genel - Temel Şirket Bilgileri\n"
                 f"🔹 /istikrar - Fiyat İstikrarı ve Fon Kullanımı\n"
                 f"🔹 /pay - Tahsisat Grupları\n"
                 f"🔹 /hesap - Katılımcı ve Lot Hesaplaması")

        bot.reply_to(message, yanit, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata oluştu: {e}")

@bot.message_handler(commands=['genel', 'istikrar', 'pay', 'hesap'])
def alt_menuler(message):
    chat_id = message.chat.id
    if chat_id not in kullanici_secimleri:
        bot.reply_to(message, "⚠️ Lütfen önce `/halkaarz FirmaAdı` yazarak bir şirket seçin.")
        return

    firma = kullanici_secimleri[chat_id]
    komut = message.text.replace("/", "").lower()
    firma_adi = veri_cek(firma, ['firma adı', 'şirket'])

    if komut == "genel":
        tarih = veri_cek(firma, ['tarih'])
        fiyat = veri_cek(firma, ['fiyat'])
        lot = veri_cek(firma, ['lot', 'pay', 'miktar'])
        dagitim = veri_cek(firma, ['dağıtım'])
        aciklik = veri_cek(firma, ['açıklık'])

        yanit = (f"🏢 **{firma_adi} - Genel Bilgiler**\n\n"
                 f"🗓 **Tarih:** {tarih}\n"
                 f"💰 **Fiyat:** {fiyat}\n"
                 f"📦 **Toplam Lot:** {lot}\n"
                 f"⚖️ **Dağıtım:** {dagitim}\n"
                 f"📊 **Halka Açıklık:** {aciklik}")

    elif komut == "istikrar":
        istikrar = veri_cek(firma, ['istikrar', 'fiyat istikrarı'])
        fon = veri_cek(firma, ['fon'])

        istikrar = istikrar.replace("*", "•").replace("_", "-")
        fon = fon.replace("*", "•").replace("_", "-")

        yanit = (f"🛡 **{firma_adi} - İstikrar & Fon Kullanımı**\n\n"
                 f"**Fiyat İstikrarı:**\n{istikrar}\n\n"
                 f"**Fon Kullanım Alanları:**\n{fon}")

    elif komut == "pay":
        tahsisat = veri_cek(firma, ['tahsisat'])
        yanit = (f"👥 **{firma_adi} - Tahsisat Grupları**\n\n{tahsisat}")

    elif komut == "hesap":
        fiyat_str = veri_cek(firma, ['fiyat'], '0')
        lot_str = veri_cek(firma, ['lot', 'pay', 'miktar'], '0')
        tahsisat_str = veri_cek(firma, ['tahsisat', 'dağılım'], '')

        try:
            temiz_fiyat = float(fiyat_str.lower().replace('tl', '').replace(',', '.').strip())
            temiz_lot = int(''.join(re.findall(r'\d+', lot_str)))
        except:
            temiz_fiyat, temiz_lot = 0.0, 0

        if temiz_lot == 0 or temiz_fiyat == 0.0:
            yanit = "⚠️ Lot veya Fiyat verisi sayısal olarak okunamadığı için hesap yapılamıyor."
        else:
            bireysel_lot = temiz_lot
            uyari_metni = ""

            if "çitlekçi" in temizle(firma_adi):
                bireysel_lot = 14600000
                uyari_metni = "*(Bireysel tahsisat 14.6 Milyon Lot olarak saptanmıştır)*\n\n"
            else:
                tahsisat_temiz = temizle(tahsisat_str)
                lot_match = re.search(r'(\d{1,3}(?:[.,]\d{3})+)\s*(?:lot|pay).*?(?:yurtiçi\s*)?bireysel', tahsisat_temiz)
                if not lot_match:
                    lot_match = re.search(r'(?:yurtiçi\s*)?bireysel.*?(\d{1,3}(?:[.,]\d{3})+)\s*(?:lot|pay)', tahsisat_temiz)

                oran_match = re.search(r'%?\s*(\d+)(?:[.,]\d+)?\s*%?\s*(?:yurtiçi\s*)?bireysel', tahsisat_temiz)
                if not oran_match:
                    oran_match = re.search(r'(?:yurtiçi\s*)?bireysel.*?%?\s*(\d+)(?:[.,]\d+)?\s*%?', tahsisat_temiz)

                if lot_match:
                    bulunan_lot = int(''.join(re.findall(r'\d+', lot_match.group(1))))
                    if bulunan_lot > 0:
                        bireysel_lot = bulunan_lot
                        uyari_metni = f"*(Tahsisat verisinden Bireysel payı {bireysel_lot:,} Lot olarak saptanmıştır)*\n\n"
                elif oran_match:
                    oran = int(oran_match.group(1))
                    if 0 < oran <= 100:
                        bireysel_lot = int(temiz_lot * (oran / 100))
                        uyari_metni = f"*(Bireysel tahsisat %{oran} saptanmış ve {bireysel_lot:,} Lot üzerinden hesaplanmıştır)*\n\n"

                if bireysel_lot == temiz_lot:
                    uyari_metni = "*(Bireysel oran tespit edilemediği için Tüm Lot üzerinden hesaplanmıştır. Gerçek dağıtım daha düşük düşebilir!)*\n\n"

            yanit = f"🧮 **{firma_adi} - Lot Tahmin Tablosu**\n\n"
            yanit += uyari_metni

            katilimcilar = [150000, 250000, 350000, 500000, 700000, 1100000, 1600000, 2200000]
            for k in katilimcilar:
                kisi_basi_lot = int(bireysel_lot / k)
                tutar = round(kisi_basi_lot * temiz_fiyat)

                if k >= 1000000:
                    k_str = f"{k/1000000:g} Milyon"
                else:
                    k_str = f"{int(k/1000)} Bin"

                yanit += f"- {k_str} katılım ~ {kisi_basi_lot} Lot ({tutar} TL).\n"

    bot.reply_to(message, yanit, parse_mode="Markdown")

# --- WEBHOOK DİNLEYİCİLERİ ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# UptimeRobot'un 10 dakikada bir ziyaret edeceği "Hayattayım" sayfası (Telegram'ı yormaz)
@app.route("/")
def ping():
    return "Bot aktif ve uyanık!", 200

# Sadece senin manuel olarak 1 kere gireceğin kurulum sayfası
@app.route("/kurulum")
def webhook_kurulum():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + TOKEN)
    return f"Webhook başarıyla ayarlandı! Bot artık 7/24 {WEBHOOK_URL} adresinde dinliyor.", 200
