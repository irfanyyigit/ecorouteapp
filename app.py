import os, sys
# Bu yollar Python 3.13'ün standart kurulum yerleridir. 
# Eğer hata devam ederse bu klasörlerin varlığını kontrol et.
os.environ['TCL_LIBRARY'] = r'C:\Users\irfan\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\irfan\AppData\Local\Programs\Python\Python313\tcl\tk8.6'
sys.path.append(r'C:\Users\irfan\AppData\Local\Programs\Python\Python313\tcl')
import customtkinter as ctk
import tkintermapview
import math
from tkcalendar import DateEntry
from data_fetcher import WeatherService
from PIL import Image
from PIL import ImageTk
import pandas as pd
from tkinter import filedialog, messagebox
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta #tarih degerleri

AIRPORTS = {
    "Ankara (ESB)": (40.12, 32.99),
    "İstanbul (IST)": (41.27, 28.75),
    "Londra (LHR)": (51.47, -0.45),
    "Paris (CDG)": (49.00, 2.55),
    "Kayseri (ASR)": (38.77, 35.49),
    "Şanlıurfa (GNY)": (37.45, 38.90),
    "New York (JFK)": (40.64, -73.77),
    "Tokyo (HND)": (35.54, 139.78),
    "Berlin (BER)": (52.36, 13.50),
    "Roma (FCO)": (41.80, 12.24),
    "Dubai (DXB)": (25.25, 55.36),
    "Amsterdam (AMS)": (52.31, 4.76),
    "Madrid (MAD)": (40.49, -3.56),
    "Bakü (GYD)": (40.46, 50.04),
    "Antalya (AYT)": (36.90, 30.79),
    "İzmir (ADB)": (38.29, 27.15),
    "Moskova (SVO)": (55.97, 37.41)
}

class MapWindow(ctk.CTkToplevel):

    def __init__(self, start_coords, end_coords, start_name, plane_icon, end_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(f"Rota: {start_name} - {end_name}")
        self.geometry("900x600")
        self.plane_icon_ref = plane_icon
        self.map_widget = tkintermapview.TkinterMapView(self, corner_radius=15)
        self.map_widget.pack(fill="both", expand=True, padx=15, pady=15)

        self.map_widget.max_zoom = 19
        self.map_widget.set_tile_server(
            "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}"
        )

        # Orta nokta
        mid_lat = (start_coords[0] + end_coords[0]) / 2
        mid_lon = (start_coords[1] + end_coords[1]) / 2

        self.map_widget.set_position(mid_lat, mid_lon)
        self.map_widget.set_zoom(6)

        # bearing hesaaplama
        bearing = self.calculate_bearing(
            start_coords[0], start_coords[1],
            end_coords[0], end_coords[1]
        )
        current_mode = ctk.get_appearance_mode()
        icon_path = "assets/white_plane.png" if current_mode == "Dark" else "assets/plane.png"
        plane_pil = Image.open(icon_path).resize((25, 25))
        rotated_plane = plane_pil.rotate(-bearing, expand=True)
        self.plane_icon_ref = ImageTk.PhotoImage(rotated_plane)

        # marker bolumu
        self.map_widget.set_marker(*start_coords, text=start_name)
        self.map_widget.set_marker(*end_coords, text=end_name)

        #animasyon için rota noktaları belirleme ilerlerme durumuna göre
        self.route_points = self.interpolate_points(start_coords, end_coords, steps=120)
        self.plane_index = 0
        self.plane_marker = None # Başlangıçta boş

        # İlk uçak marker’ı
        self.plane_marker = self.map_widget.set_marker(
            self.route_points[0][0],
            self.route_points[0][1],
            icon=self.plane_icon_ref,
            text=""
        )
        #burada anımasyonu baslat komutunu veriyoruz
        self.animate_plane()
        # rota
        self.map_widget.set_path([start_coords, end_coords], color="#3498db", width=3)
        # Küçük zoom efekti
        self.after(500, lambda: self.map_widget.set_zoom(self.map_widget.zoom + 1))
        self.after(600, lambda: self.map_widget.set_zoom(self.map_widget.zoom - 1))

    def animate_plane(self):
        # Eski marker’ı sil
        if self.plane_marker:
            self.plane_marker.delete()

        lat, lon = self.route_points[self.plane_index]

        # Yeni marker
        self.plane_marker = self.map_widget.set_marker(
            lat,
            lon,
            icon=self.plane_icon_ref,
            text=""
        )

        #indexe göre ilerletme
        self.plane_index += 1

        # Sona geldiyse başa dön
        if self.plane_index >= len(self.route_points):
            self.plane_index = 0

        #yavas ve akıcı bir şekilde ilerletiyor (ms)
        self.after(120, self.animate_plane)

    def refresh_plane_icon(self):
            """Mod değiştiğinde uçağı yeniden döndürür ve rengini günceller."""
            if self.plane_marker:
                try:
                    self.plane_marker.delete()
                except:
                    pass
                # 1. Mevcut konumu ve bearing değerini al
                lat, lon = self.plane_marker.position
                bearing = self.calculate_bearing(
                    self.route_points[0][0], self.route_points[0][1],
                    self.route_points[-1][0], self.route_points[-1][1]
                )

                # 2. Yeni moda göre doğru imajı seç ve döndür
                current_mode = ctk.get_appearance_mode()
                icon_path = "assets/white_plane.png" if current_mode == "Dark" else "assets/plane.png"
                
                plane_pil = Image.open(icon_path).resize((30, 30))
                rotated_plane = plane_pil.rotate(-bearing, expand=True)
                self.plane_icon_ref = ImageTk.PhotoImage(rotated_plane)

                # 3. Eski marker'ı sil ve yenisini (yeni renkle) ekle
                self.plane_marker.delete()
                self.plane_marker = self.map_widget.set_marker(
                    lat, lon,
                    icon=self.plane_icon_ref,
                    text=""
                )

    #SADECE HESAPLAMA YAPIYOR
    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        lat1 = math.radians(lat1)
        lat2 = math.radians(lat2)
        diff_lon = math.radians(lon2 - lon1)

        x = math.sin(diff_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - \
            math.sin(lat1) * math.cos(lat2) * math.cos(diff_lon)

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360

    def interpolate_points(self, start, end, steps=100):
        points = []
        for i in range(steps + 1):
            lat = start[0] + (end[0] - start[0]) * i / steps
            lon = start[1] + (end[1] - start[1]) * i / steps
            points.append((lat, lon))
        return points

class EcoRouteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Eco-Route Flight Planner v2.0")
        self.geometry("620x700")
        self.setup_icons()
        self.resizable(False, False)
        self.weather_service = WeatherService("1ba31ca597cbfd1a283cfcb112a95108")

        # setup_icons içinde arka plan resmini tanımla
        self.bg_image = ctk.CTkImage(
        light_image=Image.open("assets/city_bg.jpg"), # Şehir resmin
        dark_image=Image.open("assets/city_bg.jpg"),
        size=(620, 700) # Pencere boyutunla aynı olmalı
        )
        # __init__ içinde en başa (diğer her şeyden önce) ekle
        self.bg_lbl = ctk.CTkLabel(self, image=self.bg_image, text="")
        self.bg_lbl.place(x=0, y=0, relwidth=1, relheight=1)

        self.top_panel = ctk.CTkFrame(
        self, 
        fg_color="white", 
        height=130,
        )
        self.top_panel.place(x=0, y=0, relwidth=1)

        self.start_combo = ctk.CTkComboBox(self.top_panel, values=sorted(list(AIRPORTS.keys())), width=100, height=40,corner_radius=7, fg_color="#ffffff",
                                           border_width=1,border_color="#d1d1d1", button_hover_color="#ffffff",
                                           dropdown_hover_color="#f0f0f0", dropdown_text_color="black", font=("Arial", 12))
        self.start_combo.place(x=10, y=20) 
        self.start_combo.set("Nereden")
        self.end_combo = ctk.CTkComboBox(self.top_panel, values=sorted(list(AIRPORTS.keys())), width=100,height=40, corner_radius=7, fg_color="#ffffff",
                                        border_width=1,border_color="#d1d1d1", button_hover_color="white",
                                        dropdown_hover_color="#f0f0f0", dropdown_text_color="black", font=("Arial", 12))
        self.end_combo.place(x=160, y=20) 
        self.end_combo.set("Nereye")
        self.start_combo._entry.configure(justify='center') 
        self.end_combo._entry.configure(justify='center')

        self.date_container = ctk.CTkFrame(self.top_panel, 
                                        width=120, # ComboBox genişliğinle aynı yapabilirsin
                                        height=45, # ComboBox yüksekliğinle aynı
                                        fg_color="white", 
                                        border_color="#d1d1d1", # ComboBox border rengin
                                        border_width=1, 
                                        corner_radius=7)
        self.date_container.place(x=270, y=20)
        #tarıh secme alanı burada yer alıyo
        self.date_lbl = ctk.CTkLabel(self.top_panel, text="Gidiş Tarihi:", font=("Arial", 12), text_color="#333333")
        self.date_lbl.place(x=270, y=0)

        self.cal = DateEntry(self.date_container, 
                     width=12, 
                     background='#d1d1d1', 
                     foreground='white', 
                     borderwidth=0,
                     font=("Arial", 11),
                     date_pattern='dd/mm/yyyy')
        self.cal.pack(padx=5, pady=8, expand=True)

    # Konum İkonu 1 (Kalkış kutusunun içine/yanına)
        self.icon_lbl1 = ctk.CTkLabel(self.top_panel, image=self.marker_image, text="", fg_color="#ffffff")
        self.icon_lbl1.place(x=0, y=26)
    # Konum İkonu 2 (varış kutusunun içine/yanına)
        self.icon_lbl1 = ctk.CTkLabel(self.top_panel, image=self.marker_image, text="", fg_color="#ffffff")
        self.icon_lbl1.place(x=150, y=26)

     # Buton yerine Label kullanarak tıklama özelliği ekliyoruz
        self.btn_swap = ctk.CTkLabel(
            self.top_panel, 
            image=self.swap_image, 
            text="", 
            width=25,
            height=25,
            fg_color="white", 
            cursor="hand2"
        )
        # Label'a tıklama özelliği tanımlıyoruz
        self.btn_swap.bind("<Button-1>", lambda e: self.swap_locations())
        self.btn_swap.place(x=120, y=25)

        self.btn_analyze = ctk.CTkButton(self.top_panel, text="Konumu ve Verileri Analiz Et  >", command=self.analyze, 
                                          fg_color="#08b82e", text_color="white", corner_radius=7, width=250, height=40, hover_color="#0ba02b", font=("Arial", 14, "bold"))
        self.btn_analyze.place(x=10, y=70)

        self.btn_export = ctk.CTkButton(
            self.top_panel, 
            text="Raporu İndir (.pdf/.xlsx)", 
            command=self.export_report,
            fg_color="#2c3e50", # Koyu gri/mavi tonu profesyonel durur
            hover_color="#34495e",
            width=150, 
            height=40,
            corner_radius=7,
            font=("Arial", 12, "bold")
        )
        self.btn_export.place(x=265, y=70)

        self.btn_alternate = ctk.CTkButton(
            self.top_panel, 
            text="Alternatif Havalimanı Bul", 
            command=self.show_nearest_alternate,
            fg_color="#f1c40f", # sarı ton isaretleyici
            text_color="black",
            hover_color="#f39c12",
            width=160, 
            height=40,
            font=("Arial", 12, "bold")
        )
        self.btn_alternate.place(x=420, y=70) # Konumu ihtiyacına göre ayarlayabilirsin
        self.is_dark_mode = False
        self.btn_map_style = ctk.CTkButton(
        self.top_panel, 
        text="GM kapalı", 
        command=self.toggle_map_style,
        fg_color="#34495e",
        hover_color="#2c3e50",
        width=90, 
        height=40,
        font=("Arial", 11, "bold")
        )
        self.btn_map_style.place(x=405, y=20)

        self.btn_weather = ctk.CTkButton(
        self.top_panel, 
        text="Hava Durumu ", 
        command=self.open_weather_details,
        fg_color="#3498db", 
        hover_color="#2980b9",
        width=110, 
        height=40,
        font=("Arial", 11, "bold")
    )
        self.btn_weather.place(x=500, y=20)
       #-----------------------------------------------------------------------------------------------------------------------------------------------------------------#
        
       # 3. Alt Panel (Operasyonel Rapor Alanı burada baslıyor)
        #beyaz ana kart burada OPERASYONEL RAPOR
        self.report_card = ctk.CTkFrame(self, fg_color="white", height=100)
        self.report_card.place(x=0, y=320, relwidth=1, relheight=0.57)

        ctk.CTkLabel(self.report_card, text="Operasyonel Rapor", font=("Arial", 18, "bold"), text_color="black").pack(pady=15)

        # Kutuların dizileceği frame
        self.grid_frame = ctk.CTkFrame(self.report_card, fg_color="transparent")
        self.grid_frame.pack(expand=True, fill="both", padx=15)

        # grid ayarları burada
        for i in range(4): self.grid_frame.grid_columnconfigure(i, weight=1)

        # Kutucukları oluştur (İçindeki değer etiketlerini değişkenlere atıyoruz)
        self.val_konum = self.create_report_item(self.grid_frame, "Şu anki Konum", 0, 0)
        self.val_varis = self.create_report_item(self.grid_frame, "Varış Noktası", 0, 1)
        self.val_tarih = self.create_report_item(self.grid_frame, "Gidiş Tarihi", 0, 2)
        self.val_ruzgar = self.create_report_item(self.grid_frame, "Rüzgar Yönü", 0, 3)

        self.val_eta = self.create_report_item(self.grid_frame, "Tahmini Süre", 1, 0)
        self.val_durum = self.create_report_item(self.grid_frame, "Durum", 1, 1)
        self.val_etki = self.create_report_item(self.grid_frame, "Etki", 1, 2)
        self.val_fuel = self.create_report_item(self.grid_frame, "Yakıt Verimi", 1, 3)

        # Bu kısımda create_report_item'ı is_progress=True ile çağırıyoruz ve 4 sütun kaplatıyoruz
        self.progress_bar = self.create_report_item(self.grid_frame, "Uçuş Verimlilik Analizi", 2, 0, is_progress=True)
        # Progress bar'ın bulunduğu frame'i 4 sütuna yayalım:
        self.progress_bar.master.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(10, 0))

        # Siyah Harita Butonu (Rapor kartının en altına)
        self.btn_map = ctk.CTkButton(self.report_card, text="Verileri/Sonuçları Haritada Göster", 
                                     fg_color="black", text_color="white", corner_radius=20, hover_color="black",
                                     height=45, command=self.open_map, font=("Arial", 12, "bold"))
        self.btn_map.pack(fill="x", padx=20, pady=20)

    def create_report_item(self, parent, title, row, col, is_progress=False):
        # Kart çerçevesi
        item_frame = ctk.CTkFrame(parent, fg_color="#f0f0f0", corner_radius=15, height=95)
        item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        item_frame.grid_propagate(False)

        lbl_title = ctk.CTkLabel(item_frame, text=title, font=("Arial", 9, "bold"), text_color="#555555")
        lbl_title.pack(anchor="nw", padx=10, pady=5)

        if is_progress:
            # Uzun Progress Bar
            progress = ctk.CTkProgressBar(item_frame, orientation="horizontal", height=12, 
                                          progress_color="black", fg_color="#d1d1d1")
            progress.pack(fill="x", padx=15, pady=15)
            progress.set(0)
            return progress
        else:
            # Normal Değer Etiketi
            lbl_value = ctk.CTkLabel(item_frame, text="-", font=("Arial", 11), text_color="black")
            lbl_value.pack(anchor="sw", padx=10, pady=10)
            return lbl_value


        # alınan değer etiketleri (Analiz edildiğinde burası değişecek)
        lbl_value = ctk.CTkLabel(item_frame, text="-", font=("Arial", 11), text_color="black", wraplength=90)
        lbl_value.pack(anchor="sw", padx=10, pady=10)
        
        return lbl_value # Değeri güncelleyebilmek için etiketi geri döndür

    def analyze(self):
            start_city = self.start_combo.get()
            end_city = self.end_combo.get()
            
            c1 = AIRPORTS.get(start_city)
            c2 = AIRPORTS.get(end_city)
            
            if c1 and c2:
                # ETA Hesapla
                eta_sonucu = self.calculate_eta(c1, c2)
                
                # Kartları Güncelle
                self.val_konum.configure(text=start_city)
                self.val_varis.configure(text=end_city)
                self.val_tarih.configure(text=self.cal.get_date().strftime("%d/%m/%Y"))
                self.val_eta.configure(text=eta_sonucu)
                
                wind = self.weather_service.get_wind_data(c1[0], c1[1])
                if wind:
                    self.val_ruzgar.configure(text=f"{wind['deg']}°")
                    self.val_etki.configure(text=f"{wind['speed']} m/s")
                    self.val_durum.configure(text="Tamamlandı")
                    self.val_fuel.configure(text="%1.8 Tasarruf")

    # Progress Bar Animasyonu
            self.progress_bar.set(0)
            def animate_progress(val):
                if val <= 0.85: # %85'e kadar dolsun
                    self.progress_bar.set(val)
                    self.after(20, lambda: animate_progress(val + 0.02))
            animate_progress(0)

    def calculate_eta(self, coords1, coords2):#burada tahmini ucus süresi hesaplama kısmı var uygulama bir ust seviyeye burada cıkıyor
        #mesafe km cinsinden ölçme
        lat1, lon1 = math.radians(coords1[0]), math.radians(coords1[1])
        lat2, lon2 = math.radians(coords2[0]), math.radians(coords2[1])

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = 6371 * c #dünyanın yarıcapı ile çarpımı 

        hours = distance / 800
        minutes = int(hours * 60)
        return f"{minutes // 60}s {minutes % 60}dk"


    def setup_icons(self):
        self.marker_image = ctk.CTkImage(
            light_image=Image.open("assets/marker.png"),
            dark_image=Image.open("assets/marker.png"),
            size=(20, 20)
        )

        self.swap_image = ctk.CTkImage(
            light_image=Image.open("assets/swap.png"),
            dark_image=Image.open("assets/swap.png"),
            size=(20, 20)
        )
   
        # Uçak ikonu - Hata veren kısım düzeltildi
        # light_image ve dark_image boyutları resize ile (30, 30) olarak eşitlendi
        self.plane_map_icon = ctk.CTkImage(
            light_image=Image.open("assets/plane.png").resize((30, 30)),   # Siyah uçak
            dark_image=Image.open("assets/white_plane.png").resize((30, 30)), # Beyaz uçak
            size=(30, 30) # Harita üzerinde görünecek son boyut
        )

    def swap_locations(self):
        # kalkıs ve varıs noktalarının yerini değiştir
        start = self.start_combo.get()
        end = self.end_combo.get()
        self.start_combo.set(end)
        self.end_combo.set(start)
        print("Rota tersine çevrildi!")


    def open_map(self):
        start_city = self.start_combo.get()
        end_city = self.end_combo.get()

        #burada sehirlerin koordinatları söözlükten çeker
        start_coords = AIRPORTS.get(start_city)
        end_coords = AIRPORTS.get(end_city)

        #şehirler seçilmiş mi kontrol edioyruz
        if start_coords and end_coords:
            if hasattr(self, "map_window") and self.map_window.winfo_exists():
                self.map_window.focus()
            else:
                self.map_window = MapWindow(
                    start_coords=start_coords,
                    end_coords=end_coords,
                    start_name=start_city,
                    end_name=end_city,
                    plane_icon=self.plane_map_icon
                )
        else:
            print("Lütfen geçerli bir kalkış ve varış şehirleri seçin!")

    def export_report(self):
        #burada veriler dosyaya işlenmek üzere hazırlanır
        data = {
            "Parametre": ["Kalkış", "Varış", "Tarih", "Rüzgar Yönü", "Rüzgar Hızı", "Uçuş Süresi", "Yakıt Tasarrufu"],
            "Değer": [
                self.start_combo.get(),
                self.end_combo.get(),
                self.val_tarih.cget("text"),
                self.val_ruzgar.cget("text"),
                self.val_etki.cget("text"),
                self.val_eta.cget("text"),
                self.val_fuel.cget("text")
            ]
        }

        #kullanıcıya dosya türü sorma
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx"), ("PDF Dosyası", "*.pdf")]#kaydetme secenekleri excel ve pdf var
        )
        if not file_path:
            return
        try:
            if file_path.endswith(".xlsx"):
                # .excel olarak kaydetme
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)

            elif file_path.endswith(".pdf"):
                # pdf Olarak Kaydet
                c = canvas.Canvas(file_path, pagesize=letter)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(100, 750, "Eco-Route Operasyonel Raporu")
                c.setFont("Helvetica", 12)
                
                y = 700
                for i in range(len(data["Parametre"])):
                    line = f"{data['Parametre'][i]}: {data['Değer'][i]}"
                    c.drawString(100, y, line)
                    y -= 25

                c.save()
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu: {e}")

    def haversine(self, lat1, lon1, lat2, lon2):
            #iki nokta arasındaki mesafeyi km cinsinden hesaplar
            R = 6371
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
            return 2 * R * math.asin(math.sqrt(a))

    def show_nearest_alternate(self):
            # 1. Seçili şehirleri al
            full_start = self.start_combo.get()
            full_end = self.end_combo.get()
            
            c1 = AIRPORTS.get(full_start)
            c2 = AIRPORTS.get(full_end)

            if not c1 or not c2:
                print("Lütfen önce bir rota seçin!")
                return

            # 2. Orta noktayı hesapla
            mid_lat = (c1[0] + c2[0]) / 2
            mid_lon = (c1[1] + c2[1]) / 2

            en_yakin_havalimani = None
            min_mesafe = float('inf')

            # 3. En yakın meydanı bul
            for name, coords in AIRPORTS.items():
                if name == full_start or name == full_end:
                    continue
                
                dist = self.haversine(mid_lat, mid_lon, coords[0], coords[1])
                if dist < min_mesafe:
                    min_mesafe = dist
                    en_yakin_havalimani = (name, coords)

            # 4. HATA DÜZELTİLEN KISIM: Kontrol ve Çizim
            # Harita penceresi var mı ve en yakın meydan bulundu mu kontrolü
            if en_yakin_havalimani and hasattr(self, "map_window") and self.map_window.winfo_exists():
                name, coords = en_yakin_havalimani
                
                # Haritaya sarı marker ekle
                self.map_window.map_widget.set_marker(
                    coords[0], coords[1], 
                    text=f"YEDEK: {name}\n({int(min_mesafe)} km)",
                    marker_color_circle="#8B0000",
                    marker_color_outside="#C0392B"
                )
                # Haritayı yedek meydana odakla
                self.map_window.map_widget.set_position(coords[0], coords[1])
                self.map_window.map_widget.set_zoom(6) # Daha iyi görmek için biraz yaklaştır
            else:
                print("Hata: Harita penceresi açık değil veya uygun meydan bulunamadı!")

    def toggle_map_style(self):
            if not hasattr(self, "map_window") or not self.map_window.winfo_exists():
                messagebox.showinfo("Bilgi", "Lütfen önce haritayı açın!")
                return
            
            self.map_window.map_widget.delete_all_marker()
            start_city = self.start_combo.get()
            end_city = self.end_combo.get()
            self.map_window.map_widget.set_marker(*AIRPORTS[start_city], text=start_city)
            self.map_window.map_widget.set_marker(*AIRPORTS[end_city], text=end_city)

            if not self.is_dark_mode:
                # 1. TÜM UYGULAMAYI KOYU MODA AL (İkonlar burada değişir)
                ctk.set_appearance_mode("dark") 
                
                # 2. HARİTAYI KARART
                dark_url = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
                self.map_window.map_widget.set_tile_server(dark_url)
                
                # 3. BUTON GÖRÜNÜMÜNÜ GÜNCELLE
                self.btn_map_style.configure(text="GM açık", fg_color="#1abc9c")
                self.is_dark_mode = True
            else:
                # 1. TÜM UYGULAMAYI AÇIK MODA AL
                ctk.set_appearance_mode("light")
                
                # 2. HARİTAYI STANDART YAP
                standard_url = "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}"
                self.map_window.map_widget.set_tile_server(standard_url)
                
                # 3. BUTON GÖRÜNÜMÜNÜ GÜNCELLE
                self.btn_map_style.configure(text="GM kapalı", fg_color="#34495e")
                self.is_dark_mode = False

            # ÖNEMLİ: Haritayı yenilemek için küçük bir hareket yapalım ki ikon güncellensin
            self.map_window.map_widget.set_zoom(self.map_window.map_widget.zoom)

            self.map_window.refresh_plane_icon()

    def open_weather_details(self):
        city_name = self.start_combo.get()
        coords = AIRPORTS.get(city_name)

        if not coords:
            messagebox.showwarning("Uyarı", "Lütfen önce bir kalkış şehri seçin!")
            return

        data = self.weather_service.get_full_weather(coords[0], coords[1])
        if not data:
            messagebox.showerror("Hata", "Hava durumu verisi alınamadı!")
            return

        w_win = ctk.CTkToplevel(self)
        w_win.title(f"{city_name} - Detaylı Hava Durumu")
        w_win.geometry("380x600")
        w_win.attributes("-topmost", True)
        w_win.configure(fg_color="#f5f6fa") # Hafif gri arka plan

        # üst baslık ve derece gösterilen yer
        ctk.CTkLabel(w_win, text=f"{city_name}", font=("Arial", 22, "bold"), text_color="black").pack(pady=(20, 5))
        ctk.CTkLabel(w_win, text=f"{data.get('temp', 0)}°C", font=("Arial", 45, "bold"), text_color="#3498db").pack()
        ctk.CTkLabel(w_win, text=data.get('description', "").capitalize(), font=("Arial", 14, "italic"), text_color="#7f8c8d").pack(pady=(0, 20))

        #grid goruntu
        grid_frame = ctk.CTkFrame(w_win, fg_color="transparent", width=120, height=120)
        grid_frame.pack(fill="both", expand=True)

        #2 sütırlı 8 sütundan olusan yapı
        for i in range(2):
            grid_frame.grid_columnconfigure(i, weight=1, uniform="a")

        for i in range(4):
            grid_frame.grid_rowconfigure(i, weight=1)

        #veriler arka tarafta hazırlanıyor
        from datetime import datetime
        sunrise = datetime.fromtimestamp(data['sunrise']).strftime('%H:%M') if data.get('sunrise') else "--:--"
        sunset = datetime.fromtimestamp(data['sunset']).strftime('%H:%M') if data.get('sunset') else "--:--"
        visibility = data.get('visibility', 0) / 1000 if data.get('visibility') else 0

        # Kutu Listesi (Başlık, Değer)
        weather_items = [
            ("Hissedilen", f"{data.get('feels_like')}°C"),
            ("UV İndeksi", f"{data.get('uv_index')}"),
            ("Nem", f"%{data.get('humidity')}"),
            ("Rüzgar Hızı", f"{data.get('wind_speed')} m/s"),
            ("Görüş Mesafesi", f"{visibility} km"),
            ("Basınç", f"{data.get('pressure')} hPa"),
            ("Gün Doğumu", sunrise),
            ("Gün Batımı", sunset)
        ]

        # kutuları döngüyle birlikte olusturur 2x2 halınde
        for index, (title, value) in enumerate(weather_items):
            row = index // 2
            col = index % 2
                        
            item_frame = ctk.CTkFrame(grid_frame, fg_color="white", corner_radius=12, height=100)
            item_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            item_frame.grid_propagate(False) #boyut burada sabit

            # Başlık (Küçük ve Gri)
            ctk.CTkLabel(item_frame, text=title, font=("Arial", 10, "bold"), text_color="#95a5a6").pack(anchor="nw", padx=10, pady=(10, 0))
            
            # Değer (Büyük ve Siyah)
            ctk.CTkLabel(item_frame, text=value, font=("Arial", 13, "bold"), text_color="#2c3e50").pack(expand=True)
if __name__ == "__main__":
    app = EcoRouteApp()
    app.mainloop()