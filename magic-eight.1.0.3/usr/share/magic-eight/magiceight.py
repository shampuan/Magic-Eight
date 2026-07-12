import gi
import os
import random
import pygame.mixer
import ctypes
import locale
import configparser
import json

# Burası dil ayarlarıyla ilgili
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

# GTK4 kütüphanesinin içe aktarımı
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Pango, Gio

app = Gtk.Application(application_id="org.example.magiceight")

# GTK uygulaması sınıfı
class MagicEightApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

        self.project_name = "magic_eight"
        self.resource_dir = "guithings"
        self.lang_dir_name = "languages"
        self.image_icon_name = "magic_eight.png"
        self.image_ball_name = "layer.png"
        self.audio_file_name = "magic8.wav"
        self.image_ball_size = 375

        # Dil verileri burada tutulacak: {'en': {'name':..., 'texts':{...}, 'answers':[...]}, ...}
        self.languages = {}
        self.lang_codes = []

        # Kullanıcı ayarlarının tutulacağı dosya
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "magiceight")
        self.config_file = os.path.join(self.config_dir, "settings.json")

        # Varsayılan dil (diller yüklenene kadar geçici)
        self.current_lang = 'en'
        self.is_muted = False
    
    # Kapsamlı dosya bulma metodu
    def find_file(self, filename):
        # 1. /usr/share/magiceight/guithings klasöründen çekmesi için
        install_path = os.path.join(
            os.path.abspath(os.sep), "usr", "share", self.project_name, self.resource_dir, filename
        )
        if os.path.exists(install_path):
            return install_path
        
        # 2. Bulamazsa kendi dizininde arasın (geliştirme aşaması)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(script_dir, self.resource_dir, filename)
        if os.path.exists(local_path):
            return local_path

        # 3. Bulunamazsa None döndür
        return None

    # languages klasörünü bulan metot (find_file ile aynı mantık, klasör için)
    def find_languages_dir(self):
        install_path = os.path.join(
            os.path.abspath(os.sep), "usr", "share", self.project_name, self.lang_dir_name
        )
        if os.path.isdir(install_path):
            return install_path

        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(script_dir, self.lang_dir_name)
        if os.path.isdir(local_path):
            return local_path

        return None

    # languages klasöründeki tüm .ini dosyalarını tarar ve yükler
    def load_languages(self):
        self.languages = {}
        lang_dir = self.find_languages_dir()

        if not lang_dir:
            print("languages klasörü bulunamadı.")
            self.lang_codes = []
            return

        for filename in sorted(os.listdir(lang_dir)):
            if not filename.lower().endswith(".ini"):
                continue

            code = os.path.splitext(filename)[0]
            parser = configparser.ConfigParser(interpolation=None)

            try:
                parser.read(os.path.join(lang_dir, filename), encoding="utf-8")
            except configparser.Error as e:
                print(f"{filename} okunamadı: {e}")
                continue

            if "Texts" not in parser or "Answers" not in parser:
                print(f"{filename} eksik bölüm içeriyor, atlandı.")
                continue

            display_name = parser.get("Meta", "name", fallback=code)

            texts = {}
            for key, value in parser["Texts"].items():
                texts[key] = value.replace("\\n", "\n")

            answers = [value for key, value in parser["Answers"].items()]

            self.languages[code] = {
                "name": display_name,
                "texts": texts,
                "answers": answers
            }

        self.lang_codes = list(self.languages.keys())

    # ~/.config/magiceight/settings.json dosyasından kayıtlı ayarları okur
    def load_settings(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Dil ayarını oku
                saved_lang = data.get("language")
                if saved_lang in self.languages:
                    self.current_lang = saved_lang
                else:
                    self.current_lang = "en" if "en" in self.languages else (next(iter(self.languages)) if self.languages else "en")
                
                # Ses ayarını oku
                self.is_muted = data.get("is_muted", False)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            # Dosya yoksa veya bozuksa varsayılanlar
            self.current_lang = "en" if "en" in self.languages else (next(iter(self.languages)) if self.languages else "en")
            self.is_muted = False

    # Mevcut ayarları ~/.config/magiceight/settings.json dosyasına kaydeder
    def save_settings(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            settings_data = {
                "language": self.current_lang,
                "is_muted": self.is_muted
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=4)
        except OSError as e:
            print(f"Ayarlar kaydedilemedi: {e}")

    # Pencereyi aktif hale getirme
    def on_activate(self, app):
        # Dil dosyalarını ve kayıtlı ayarları yükle
        self.load_languages()
        self.load_settings()

        # Ana pencereyi oluşturma
        self.window = Gtk.ApplicationWindow(application=app)
        
        # GTK4 Stili Düzeltme: Gtk.HeaderBar kullan eskisi iyi değildi
        self.header_bar = Gtk.HeaderBar.new()
        self.window.set_titlebar(self.header_bar)
        
        # Pencere varsayılan ayarları
        self.window.set_default_size(self.image_ball_size + 50, self.image_ball_size + 150)
        self.window.set_resizable(False)

        # Program ikonunu ayarla
        # HATA DÜZELTMESİ: İkon, pencereye değil, doğrudan uygulamaya atanır.
        # Bu, GTK4'te önerilen yöntemdir.
        # Uygulama ikonunu standart bir ikonla ayarla
        self.window.set_icon_name("magic_eight")

        # Hakkında penceresi ikonunu ayarla
        icon_path = self.find_file(self.image_icon_name)
        if icon_path:
            self.about_dialog_icon = Gdk.Texture.new_from_file(Gio.File.new_for_path(icon_path))
        else:
            self.about_dialog_icon = None

        # HeaderBar'a menü butonu ekledik sorun verirse değiştircez. 
        menu_button = Gtk.MenuButton()
        # Daha güvenli bir ikon ismi kullanıldı.
        menu_button.set_icon_name("list-add-symbolic") 
        self.header_bar.pack_end(menu_button)
        
        # Popover menüsü oluşturduk
        self.popover = Gtk.Popover.new() 
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.popover.set_child(popover_box)
        
        # Dil seçme combobox'ı (languages klasöründeki .ini dosyalarından otomatik doldurulur)
        lang_names = [self.languages[code]["name"] for code in self.lang_codes]
        lang_model = Gtk.StringList.new(lang_names)
        self.lang_dropdown = Gtk.DropDown(model=lang_model)
        self.lang_dropdown.set_margin_top(5)
        self.lang_dropdown.set_margin_bottom(5)

        if self.current_lang in self.lang_codes:
            self.lang_dropdown.set_selected(self.lang_codes.index(self.current_lang))

        self.lang_dropdown.connect("notify::selected", self.on_language_changed)
        popover_box.append(self.lang_dropdown)
        
        # Ses kapatma onay kutusu
        self.mute_check = Gtk.CheckButton()
        self.mute_check.set_active(self.is_muted) # Kayıtlı duruma göre kutuyu ayarla
        self.mute_check.set_margin_top(5)
        self.mute_check.set_margin_bottom(5)
        self.mute_check.connect("toggled", self.on_mute_toggled)
        popover_box.append(self.mute_check)
        
        # Hakkında butonu
        about_button = Gtk.Button(label="About")
        about_button.set_margin_top(5)
        about_button.set_margin_bottom(5)
        about_button.connect("clicked", self.on_about_button_clicked)
        popover_box.append(about_button)

        menu_button.set_popover(self.popover)

        # Ana dikey kutuyu (VBox) oluştur
        main_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.window.set_child(main_box)

        # Bilardo topu resmini yükle
        image_ball_path = self.find_file(self.image_ball_name)
        if image_ball_path:
            self.image_ball = Gtk.Image.new_from_file(image_ball_path)
            self.image_ball.set_size_request(self.image_ball_size, self.image_ball_size)
        else:
            self.image_ball = Gtk.Label(label="layer.png not found.")
        
        # Üst üste bindirme (overlay) oluştur
        self.overlay = Gtk.Overlay()
        self.overlay.set_child(self.image_ball)
        
        # Metin etiketini topun üzerine yerleştir
        self.answer_label = Gtk.Label(label="")
        self.answer_label.set_wrap(True)
        self.answer_label.set_justify(Gtk.Justification.CENTER)
        self.answer_label.set_max_width_chars(15) 

        # Yanıt metninin stilini ayarla
        pango_attr = Pango.AttrList.new()
        pango_attr.insert(Pango.attr_family_new("Liberation Sans"))
        pango_attr.insert(Pango.attr_size_new(12 * Pango.SCALE)) 
        pango_attr.insert(Pango.attr_foreground_new(0xFFFF, 0xFFFF, 0xFFFF)) 
        self.answer_label.set_attributes(pango_attr)
        
        self.overlay.add_overlay(self.answer_label)
        self.answer_label.set_halign(Gtk.Align.CENTER)
        self.answer_label.set_valign(Gtk.Align.CENTER)
        
        main_box.append(self.overlay)
        
        # Giriş metin kutusunu oluştur
        self.entry = Gtk.Entry()
        self.entry.connect("activate", lambda widget: self.get_answer_button.emit("clicked"))
        main_box.append(self.entry)
        
        # Butonu oluştur
        self.get_answer_button = Gtk.Button()
        self.get_answer_button.add_css_class("suggested-action")
        self.get_answer_button.connect("clicked", self.on_button_clicked)
        main_box.append(self.get_answer_button)

        # Metinleri başlangıç diline göre güncelle
        # Bu özellik tam istediğim gibi çalışmıyor yanıtı sıfırlıyor boşver böyle kalsın
        self.update_ui_texts()
        
        # Pygame mixer'ı başlatalım ses çalsın
        try:
            pygame.mixer.init()
            self.sound_file = self.find_file(self.audio_file_name)
            if self.sound_file:
                self.sound = pygame.mixer.Sound(self.sound_file)
            else:
                self.sound = None
                print("Ses dosyası bulunamadı.")
        except pygame.error as e:
            print(f"Pygame mixer başlatılırken hata oluştu: {e}")
            self.sound = None

        self.window.present()

    def update_ui_texts(self):
        """Arayüz metinlerini mevcut dile göre günceller."""
        if self.current_lang not in self.languages:
            return

        texts = self.languages[self.current_lang]["texts"]

        # Başlık çubuğunu güncelle
        title_label = Gtk.Label(label=texts.get("window_title", "Magic Eight"))
        self.header_bar.set_title_widget(title_label)

        # Diğer metinleri güncelle
        self.entry.set_placeholder_text(texts.get("entry_placeholder", ""))
        self.get_answer_button.set_label(texts.get("button_label", ""))
        self.answer_label.set_tooltip_text(texts.get("answer_tooltip", ""))
        self.get_answer_button.set_tooltip_text(texts.get("answer_tooltip", ""))
        self.mute_check.set_label(texts.get("mute_label", "Mute"))
        
    def on_language_changed(self, dropdown, param):
        """Dil combobox'ından seçim yapıldığında çağrılır."""
        selected_index = dropdown.get_selected()
        if selected_index < 0 or selected_index >= len(self.lang_codes):
            return

        new_lang = self.lang_codes[selected_index]
        if new_lang == self.current_lang:
            return

        self.current_lang = new_lang
        self.update_ui_texts()
        self.answer_label.set_text("") # Yanıt etiketini temizle
        self.save_settings() # Yeni ayarları kaydet
        self.popover.popdown()

    def on_mute_toggled(self, check_button):
        """Ses durumunu onay kutusuna göre günceller ve kaydeder."""
        self.is_muted = check_button.get_active()
        self.save_settings() # Ses değiştiğinde ayarları kaydet

    def on_about_button_clicked(self, widget):
        """Hakkında butonuna basıldığında çağrılır."""
        texts = self.languages.get(self.current_lang, {}).get("texts", {})
        about_dialog = Gtk.AboutDialog.new()
        about_dialog.set_program_name(texts.get('window_title', "Magic Eight"))
        about_dialog.set_comments(texts.get('about_comments', ""))
        about_dialog.set_version(texts.get('about_version', ""))
        about_dialog.set_license(texts.get('about_license', ""))
        about_dialog.set_authors([texts.get('about_author', "")]) 
        about_dialog.set_website(texts.get('about_website', ""))
        about_dialog.set_website_label("GitHub")
        
        # İkonu ayarla
        if self.about_dialog_icon:
            about_dialog.set_logo(self.about_dialog_icon)
        else:
            about_dialog.set_logo_icon_name("image-missing")

        about_dialog.set_transient_for(self.window)
        about_dialog.set_modal(True)
        about_dialog.present()
        self.popover.popdown() # Popover'ı doğru şekilde kapat

    def on_button_clicked(self, widget):
        # Soruyu al
        question = self.entry.get_text()
        if not question:
            texts = self.languages.get(self.current_lang, {}).get("texts", {})
            self.answer_label.set_text(texts.get("error_message", ""))
            return

        # Sesi çal (Eğer sessize alınmadıysa)
        if self.sound and not self.is_muted:
            self.sound.play()

        # Rastgele bir yanıt seç
        answers = self.languages.get(self.current_lang, {}).get("answers", [])
        if not answers:
            return
        answer = random.choice(answers)

        # Etiketi güncelle
        self.answer_label.set_text(answer)
        print(f"Soru: {question}, Cevap: {answer}")

# Uygulamayı başlat
if __name__ == "__main__":
    app = MagicEightApp(application_id="com.example.magiceight")
    app.run(None)

