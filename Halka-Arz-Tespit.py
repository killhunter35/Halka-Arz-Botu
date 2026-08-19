from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import json
import time
import pandas as pd
import os
import datetime
import re
import smtplib
import ssl
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openpyxl.styles import Alignment, Font, PatternFill

print("Gizli (Stealth) Tarayıcı başlatılıyor...")
tr_timezone = datetime.timezone(datetime.timedelta(hours=3))
bugun_tarih = datetime.datetime.now(tr_timezone)
current_year = bugun_tarih.year

# --- İLK İŞLEM GÜNÜ KESTİRME (SHORTCUTS) TETİKLEYİCİSİ ---
def ilk_islem_linki_olustur(firma_adi, tarih_str):
    aylar = {"ocak": "01", "şubat": "02", "mart": "03", "nisan": "04", "mayıs": "05", "haziran": "06", 
             "temmuz": "07", "ağustos": "08", "eylül": "09", "ekim": "10", "kasım": "11", "aralık": "12"}
    
    tarih_str = tarih_str.lower()
    ay_no = "01"
    for ay, no in aylar.items():
        if ay in tarih_str:
            ay_no = no
            break
            
    yil_match = re.search(r'202\d', tarih_str)
    yil = yil_match.group(0) if yil_match else str(current_year)
    
    gun_match = re.search(r'\b\d{1,2}\b', tarih_str)
    if not gun_match: 
        return None
        
    gun = int(gun_match.group(0))
    islem_tarihi_formati = f"{yil}{ay_no}{gun:02d}"
    
    try:
        islem_tarihi_obj = datetime.datetime.strptime(islem_tarihi_formati, "%Y%m%d")
        hatirlatici_tarihi_obj = islem_tarihi_obj - datetime.timedelta(days=1)
        tarih_metni = hatirlatici_tarihi_obj.strftime("%d.%m.%Y 22:00")
        
        # Linki senin GitHub sitene yönlendiriyoruz!
        firma_enc = urllib.parse.quote(firma_adi)
        tarih_enc = urllib.parse.quote(tarih_metni)
        link = f"https://killhunter35.github.io/Halka-Arz-Botu/yonlendir.html?firma={firma_enc}&tarih={tarih_enc}"
        return link
    except:
        return None

# --- TALEP TOPLAMA GÜNÜ HESAPLAYICI ---
def talep_durumu(tarih_metni):
    aylar = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
             7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
    gun = bugun_tarih.day
    ay_adi = aylar[bugun_tarih.month]

    if ay_adi not in tarih_metni:
        return None

    gun_blogu = tarih_metni.split(ay_adi)[0]
    sayilar = [int(s) for s in re.findall(r'\d{1,2}', gun_blogu)]

    if not sayilar:
        return None

    ilk_gun = sayilar[0]
    son_gun = sayilar[-1]

    if gun == ilk_gun:
        return "BASLIYOR"
    elif gun == son_gun:
        return "SON_GUN"
    return None

# --- 1. ESKİ HAFIZAYI (EXCEL) OKUMA ---
dosya_adi = "Halka_Arz_Verileri.xlsx"
eski_firmalar = set()
tamamlanan_firmalar = set() 
eski_islem_tarihleri = {} 
df_yaklasan, df_tamamlanan, df_kismi = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if os.path.exists(dosya_adi):
    print(f"'{dosya_adi}' bulundu. Geçmiş veriler hafızaya alınıyor...")
    excel_dosyasi = pd.ExcelFile(dosya_adi)
    if "Yaklaşan Arzlar" in excel_dosyasi.sheet_names:
        df_yaklasan = pd.read_excel(dosya_adi, sheet_name="Yaklaşan Arzlar").dropna(subset=["Firma Adı"])
    if "Tamamlanan Arzlar" in excel_dosyasi.sheet_names:
        df_tamamlanan = pd.read_excel(dosya_adi, sheet_name="Tamamlanan Arzlar").dropna(subset=["Firma Adı"])
        tamamlanan_firmalar.update(df_tamamlanan["Firma Adı"].tolist())
        for _, row in df_tamamlanan.iterrows():
            eski_islem_tarihleri[row["Firma Adı"]] = str(row.get("İlk İşlem Tarihi", "-"))
    if "Kısmi Bölünme" in excel_dosyasi.sheet_names:
        df_kismi = pd.read_excel(dosya_adi, sheet_name="Kısmi Bölünme").dropna(subset=["Firma Adı"])

    for df in [df_yaklasan, df_tamamlanan, df_kismi]:
        if not df.empty and "Firma Adı" in df.columns:
            eski_firmalar.update(df["Firma Adı"].tolist())

# --- 2. SİTEYE GİRİŞ (HAYALET MOD) ---
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("window-size=1280,800")
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
})

url = "https://halkarz.com/"
driver.get(url)
time.sleep(3)

while True:
    try:
        load_more_btn = driver.find_element(By.CLASS_NAME, "misha_loadmore")
        if load_more_btn.is_displayed():
            driver.execute_script("arguments[0].click();", load_more_btn)
            time.sleep(1.5)
        else:
            break
    except:
        break

soup = BeautifulSoup(driver.page_source, "html.parser")
ana_kolon = soup.find("div", id="getin")
test_linkleri = []

if ana_kolon:
    for ul in ana_kolon.find_all("ul"):
        if ul.get("class") == ["halka-arz-list"]:
            for makale in ul.find_all("article", class_="index-list"):
                link_etiketi = makale.find("a")
                if link_etiketi and link_etiketi.has_attr("href"):
                    test_linkleri.append(link_etiketi["href"])

test_linkleri = list(dict.fromkeys(test_linkleri))
yaklasan_listesi, tamamlanan_listesi, kismi_listesi = [], [], []
yeni_yaklasan, yeni_tamamlanan, yeni_kismi = [], [], []
bugun_baslayanlar, bugun_bitenler = [], []
yeni_islem_tarihleri_eklenenler = []

# --- 3. DİNAMİK AKILLI TARAMA VE VERİ ÇEKME ---
for index_no, link in enumerate(test_linkleri):
    driver.get(link)
    time.sleep(2)

    detay_soup = BeautifulSoup(driver.page_source, "html.parser")
    sayfa_basligi = driver.title.replace(" Halka Arz", "").strip()
    sayfa_metni = detay_soup.text

    eski_islem = eski_islem_tarihleri.get(sayfa_basligi, "-")
    
    if sayfa_basligi in tamamlanan_firmalar:
        if "202" in eski_islem:
            print(f"\n✅ DİNAMİK AKILLI TARAMA: '{sayfa_basligi}' zaten tamamlanmış ve işlem tarihi belli. Tarama güvenle sonlandırıldı.")
            break
        else:
            print(f"🔄 '{sayfa_basligi}' tamamlanmış ancak işlem tarihi bekleniyor. Kontrol ediliyor...")

    def tablo_verisi_al(baslik_metni):
        etiket = detay_soup.find(string=lambda x: x and baslik_metni in x)
        if etiket and etiket.find_parent("tr"):
            td_ler = etiket.find_parent("tr").find_all("td")
            if len(td_ler) > 1: return td_ler[1].text.replace("*", "").strip()
        return "-"

    tarih_metni = tablo_verisi_al("Halka Arz Tarihi")
    eski_tamamlanmis_mi = any(str(yil) in tarih_metni for yil in range(1980, current_year))
    durum = ""

    if "Kısmi Bölünme" in sayfa_metni:
        durum = "KISMİ BÖLÜNME"
        kismi_listesi.append({"Firma Adı": sayfa_basligi, "Halka Arz Tarihi": tarih_metni,
                              "BİST İlk İşlem Tarihi": tablo_verisi_al("İlk İşlem Tarihi")})
                              
    elif "Halka Arz Sonuçları" in sayfa_metni or "Bist İlk İşlem Tarihi" in sayfa_metni or eski_tamamlanmis_mi:
        durum = "TAMAMLANAN ARZ"
        yeni_islem = tablo_verisi_al("İlk İşlem Tarihi")
        
        if "202" not in eski_islem and "202" in yeni_islem:
            yeni_islem_tarihleri_eklenenler.append({
                "Firma": sayfa_basligi,
                "Tarih": yeni_islem
            })
            
        tamamlanan_veriler = {
            "Firma Adı": sayfa_basligi, "Halka Arz Tarihi": tarih_metni, "Fiyat": tablo_verisi_al("Halka Arz Fiyatı"),
            "Lot Miktarı": tablo_verisi_al("Pay :"), "Dağıtım Yöntemi": tablo_verisi_al("Dağıtım Yöntemi"),
            "İlk İşlem Tarihi": yeni_islem, "Bireysel Katılımcı": "-", "Bireysel Oran": "-",
            "Toplam Katılımcı": "-"
        }
        bireysel_hucre = detay_soup.find("td", string=lambda x: x and "Yurt İçi Bireysel" in x)
        if bireysel_hucre and bireysel_hucre.find_parent("tr") and len(
                bireysel_hucre.find_parent("tr").find_all("td")) >= 4:
            sutunlar = bireysel_hucre.find_parent("tr").find_all("td")
            tamamlanan_veriler["Bireysel Katılımcı"], tamamlanan_veriler["Bireysel Oran"] = sutunlar[1].text.strip(), \
            sutunlar[3].text.strip()
        toplam_hucre = detay_soup.find(["td", "b", "strong"], string=lambda x: x and "Toplam" in x)
        if toplam_hucre and toplam_hucre.find_parent("tr") and len(toplam_hucre.find_parent("tr").find_all("td")) >= 2:
            tamamlanan_veriler["Toplam Katılımcı"] = toplam_hucre.find_parent("tr").find_all("td")[1].text.strip()
        tamamlanan_listesi.append(tamamlanan_veriler)
        
    else:
        durum = "YAKLAŞAN/TASLAK ARZ"
        t_durum = talep_durumu(tarih_metni)
        if t_durum == "BASLIYOR":
            bugun_baslayanlar.append(sayfa_basligi)
        elif t_durum == "SON_GUN":
            bugun_bitenler.append(sayfa_basligi)

        yaklasan_veriler = {
            "Firma Adı": sayfa_basligi, "Halka Arz Tarihi": tarih_metni, "Fiyat": "-", "Lot Miktarı": "-",
            "Dağıtım Yöntemi": "-", "Halka Açıklık": "-", "Arz Büyüklüğü": "-", "Fiyat İstikrarı": "-",
            "Fon Kullanımı": "-", "Tahsisat Grupları": "-", "Dağıtılacak Pay (Olası)": "-", "Finansal Tablo": "-"
        }
        fiyat_etiketi = detay_soup.find(string=lambda x: x and "Halka Arz Fiyatı" in x)
        if fiyat_etiketi and fiyat_etiketi.find_parent(["tr", "li", "div"]) and ":" in fiyat_etiketi.find_parent(
                ["tr", "li", "div"]).text:
            yaklasan_veriler["Fiyat"] = fiyat_etiketi.find_parent(["tr", "li", "div"]).text.split(":")[-1].strip()
        pay_etiketi = detay_soup.find(string=lambda x: x and "Pay :" in x)
        if pay_etiketi and pay_etiketi.find_parent(["tr", "li", "div"]) and ":" in pay_etiketi.find_parent(
                ["tr", "li", "div"]).text:
            yaklasan_veriler["Lot Miktarı"] = pay_etiketi.find_parent(["tr", "li", "div"]).text.split(":")[-1].strip()
        dy_etiket = detay_soup.find(string=lambda x: x and "Dağıtım Yöntemi" in x)
        if dy_etiket and dy_etiket.find_parent("tr") and ":" in dy_etiket.find_parent("tr").text:
            yaklasan_veriler["Dağıtım Yöntemi"] = dy_etiket.find_parent("tr").text.split(":")[-1].replace("*", "").strip()

        def ozet_bilgi_cek(baslik_metni):
            baslik = detay_soup.find("h5", string=lambda x: x and baslik_metni in x)
            if baslik and baslik.find_next_sibling("p"):
                p_etiket = baslik.find_next_sibling("p")
                for small in p_etiket.find_all("small"): small.decompose()
                return p_etiket.get_text(separator="\n", strip=True)
            return "-"

        yaklasan_veriler["Fon Kullanımı"], yaklasan_veriler["Tahsisat Grupları"] = ozet_bilgi_cek(
            "Fonun Kullanım Yeri"), ozet_bilgi_cek("Tahsisat Grupları")
        yaklasan_veriler["Halka Açıklık"], yaklasan_veriler["Arz Büyüklüğü"] = ozet_bilgi_cek(
            "Halka Açıklık"), ozet_bilgi_cek("Halka Arz Büyüklüğü")
        yaklasan_veriler["Fiyat İstikrarı"], yaklasan_veriler["Dağıtılacak Pay (Olası)"] = ozet_bilgi_cek(
            "Fiyat İstikrarı"), ozet_bilgi_cek("Dağıtılacak Pay Miktarı")

        finansal_tablo_verisi = []
        finans_baslik = detay_soup.find("h5", string=lambda x: x and "Finansal Tablo" in x)
        if finans_baslik and finans_baslik.find_parent("table"):
            for satir in finans_baslik.find_parent("table").find_all("tr"):
                hucreler = [hucre.text.strip() for hucre in satir.find_all(["th", "td"])]
                if hucreler: finansal_tablo_verisi.append(" - ".join(hucreler))
            yaklasan_veriler["Finansal Tablo"] = "\n".join(finansal_tablo_verisi)
        yaklasan_listesi.append(yaklasan_veriler)

    if sayfa_basligi not in eski_firmalar:
        if durum == "YAKLAŞAN/TASLAK ARZ":
            yeni_yaklasan.append(sayfa_basligi)
        elif durum == "TAMAMLANAN ARZ":
            yeni_tamamlanan.append(sayfa_basligi)
        elif durum == "KISMİ BÖLÜNME":
            yeni_kismi.append(sayfa_basligi)

driver.quit()

# --- 4. MAİL VE TELEGRAM GÖNDERME FONKSİYONLARI ---
def telegram_gonder(icerik):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_uzunluk = 4000
    parcalar = [icerik[i:i+max_uzunluk] for i in range(0, len(icerik), max_uzunluk)]
    
    for parca in parcalar:
        payload = {"chat_id": chat_id, "text": parca, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram bağlantı hatası: {e}")
            
def mail_gonder(baslik, icerik):
    gonderen = os.environ.get("MAIL_ADRESI")
    sifre = os.environ.get("MAIL_SIFRESI")
    alici = os.environ.get("MAIL_ADRESI")
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = gonderen, alici, baslik
    msg.attach(MIMEText(icerik, 'plain', 'utf-8'))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gonderen, sifre)
            server.sendmail(gonderen, alici, msg.as_string())
    except Exception as e:
        print(f"Mail hatası: {e}")

# --- 5. DİNAMİK RAPORLAMA VE MAİL MANTIĞI ---
anlik_zaman = datetime.datetime.now(tr_timezone).strftime("%d.%m.%Y - %H:%M")
guncel_tum_firmalar = yaklasan_listesi + tamamlanan_listesi + kismi_listesi

def mail_kategori_metni(baslik_metni, firma_isimleri):
    if not firma_isimleri: return ""
    metin = f"\n📌 {baslik_metni}\n" + "-" * 40 + "\n"
    for f_adi in firma_isimleri:
        f_veri = next((item for item in guncel_tum_firmalar if item["Firma Adı"] == f_adi), None)
        if f_veri:
            metin += f"FİRMA: {f_adi}\n" + "-" * 30 + "\n"
            for k, v in f_veri.items():
                if k != "Firma Adı": metin += f"{k}: {v}\n"
            metin += "\n" + "=" * 50 + "\n"
    return metin

if eski_firmalar and (yeni_yaklasan or yeni_tamamlanan or yeni_kismi or bugun_baslayanlar or bugun_bitenler or yeni_islem_tarihleri_eklenenler):

    if bugun_bitenler:
        mail_baslik = f"⏳ SON GÜN: {bugun_bitenler[0]} Talep Toplaması Bitiyor!"
    elif bugun_baslayanlar:
        mail_baslik = f"🔔 BAŞLADI: {bugun_baslayanlar[0]} Talep Topluyor!"
    elif yeni_islem_tarihleri_eklenenler:
        mail_baslik = f"📅 İLK İŞLEM TARİHİ: {yeni_islem_tarihleri_eklenenler[0]['Firma']} Belli Oldu!"
    elif yeni_yaklasan:
        mail_baslik = f"🚨 YENİ Halka Arz (Yaklaşan): {yeni_yaklasan[0]}"
    elif yeni_tamamlanan:
        mail_baslik = f"✅ Tamamlanan Arz Eklendi: {yeni_tamamlanan[0]}"
    else:
        mail_baslik = "🔄 Sistemde Yeni Güncellemeler Var"

    mail_icerik = f"Tarih: {anlik_zaman}\nSistemde önemli halka arz hareketleri tespit edildi!\n\n"

    if yeni_islem_tarihleri_eklenenler:
        mail_icerik += "\n📅 İLK İŞLEM TARİHİ BELLİ OLANLAR\n" + "-"*40 + "\n"
        for item in yeni_islem_tarihleri_eklenenler:
            mail_icerik += f"FİRMA: {item['Firma']} -> İlk İşlem: {item['Tarih']}\n"
            
    mail_icerik += mail_kategori_metni("⏳ BUGÜN TALEP TOPLAMASI BİTENLER (SON GÜN)", bugun_bitenler)
    mail_icerik += mail_kategori_metni("🔔 BUGÜN TALEP TOPLAMASI BAŞLAYANLAR", bugun_baslayanlar)
    mail_icerik += mail_kategori_metni("YENİ YAKLAŞAN/TASLAK ARZLAR", yeni_yaklasan)
    mail_icerik += mail_kategori_metni("TAMAMLANAN ARZLAR LİSTESİNE EKLENENLER", yeni_tamamlanan)
    mail_icerik += mail_kategori_metni("KISMİ BÖLÜNME LİSTESİNE EKLENENLER", yeni_kismi)

    mail_gonder(mail_baslik, mail_icerik)
    telegram_gonder(f"🚨 {mail_baslik}\n\n{mail_icerik}")
    
    # TAKVİM LİNKLERİNİ GÖNDERME İŞLEMİ
    for item in yeni_islem_tarihleri_eklenenler:
        takvim_linki = ilk_islem_linki_olustur(item['Firma'], item['Tarih'])
        if takvim_linki:
            mesaj = (f"🔔 {item['Firma']} firmasının ilk işlem tarihi belli oldu.\n\n"
                     f"Yarın akşam 22:00'de hatırlatmam için aşağıdaki linke tıklayıp anımsatıcıyı kurabilirsin:\n\n"
                     f"👉 {takvim_linki}")
            telegram_gonder(mesaj)

elif eski_firmalar:
    mail_gonder("Günlük Halka Arz Taraması Raporu", 
                f"Tarih: {anlik_zaman}\nTarama Yapıldı. Bugün talep toplayan veya sisteme yeni eklenen bir firma bulunamadı.")
    telegram_gonder(f"✅ Günlük Tarama Yapıldı ({anlik_zaman})\nBugün talep toplayan veya sisteme yeni eklenen bir firma bulunamadı.")

# --- 6. EXCEL'İ GÜNCELLEME VE TEMİZLEME ---
yeni_tam_ve_kismi_isimler = [f["Firma Adı"] for f in (tamamlanan_listesi + kismi_listesi)]
if not df_yaklasan.empty: df_yaklasan = df_yaklasan[~df_yaklasan["Firma Adı"].isin(yeni_tam_ve_kismi_isimler)]

def merge_and_save(yeni_liste, eski_df, sheet_name, writer):
    yeni_df = pd.DataFrame(yeni_liste) if yeni_liste else pd.DataFrame()
    if not yeni_df.empty: yeni_df = yeni_df.dropna(subset=["Firma Adı"])
    if not eski_df.empty: eski_df = eski_df.dropna(subset=["Firma Adı"])

    if not yeni_df.empty and not eski_df.empty:
        final_df = pd.concat([yeni_df, eski_df]).drop_duplicates(subset=["Firma Adı"], keep="first")
    elif not yeni_df.empty:
        final_df = yeni_df
    elif not eski_df.empty:
        final_df = eski_df
    else:
        final_df = pd.DataFrame()
    if not final_df.empty: final_df.to_excel(writer, sheet_name=sheet_name, index=False)

with pd.ExcelWriter(dosya_adi, engine="openpyxl") as writer:
    merge_and_save(yaklasan_listesi, df_yaklasan, "Yaklaşan Arzlar", writer)
    merge_and_save(tamamlanan_listesi, df_tamamlanan, "Tamamlanan Arzlar", writer)
    merge_and_save(kismi_listesi, df_kismi, "Kısmi Bölünme", writer)

    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        for cell in worksheet[1]:
            cell.font, cell.fill, cell.alignment = Font(bold=True, color="FFFFFF"), PatternFill(start_color="1F4E78",
                                                                                                end_color="1F4E78",
                                                                                                fill_type="solid"), Alignment(
                horizontal="center", vertical="center")
        for col in worksheet.columns:
            worksheet.column_dimensions[col[0].column_letter].width = 35
            for cell in col: cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
