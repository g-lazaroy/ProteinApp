from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from threading import Thread

import os

# Αυτό βρίσκει το τρέχον directory που εκτελείται το script
base_path = os.path.dirname(os.path.abspath(__file__))

print(f"Τρέχουμε από το: {base_path}")

# Εισαγωγές από τον αρχικό κώδικα
from sidp02 import main, clean_duplicate_products, analyze_products
from sidp02 import top_isolate_products, top_mass_gainer_products, top_hydrolyzed_products, top_whey_products

class ProteinApp(MDApp):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Τίτλος εφαρμογής
        title = MDLabel(
            text="Εφαρμογή Πρωτεϊνών",
            halign="center",
            theme_text_color="Primary",
            font_style="H4",
            size_hint=(1, 0.1)
        )
        layout.add_widget(title)

        # Κουμπί για Scraping
        scrape_button = MDRaisedButton(
            text="Ξεκίνα Scraping",
            size_hint=(1, 0.2),
            md_bg_color=(0.1, 0.6, 0.2, 1),
            pos_hint={"center_x": 0.5}
        )
        scrape_button.bind(on_press=self.run_scraping)
        layout.add_widget(scrape_button)

        # Κουμπιά για τις κατηγορίες
        categories = [
            ("Top Isolate Products", self.show_isolate_products),
            ("Top Mass Gainer Products", self.show_mass_products),
            ("Top Hydrolyzed Products", self.show_hydrolyzed_products),
            ("Top Whey Products", self.show_whey_products)
        ]

        for text, callback in categories:
            button = MDRaisedButton(
                text=text,
                size_hint=(1, 0.2),
                md_bg_color=(0.1, 0.6, 0.2, 1),
                pos_hint={"center_x": 0.5}
            )
            button.bind(on_press=callback)
            layout.add_widget(button)

        # Περιοχή εμφάνισης αποτελεσμάτων
        scroll_view = ScrollView(size_hint=(1, 1))
        self.result_label = MDLabel(
            text="",
            size_hint_y=None,
            halign="left",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1),
            markup=True  # Υποστήριξη για μορφοποίηση κειμένου
        )
        self.result_label.bind(texture_size=self.result_label.setter('size'))
        scroll_view.add_widget(self.result_label)
        layout.add_widget(scroll_view)

        return layout

    def update_label(self, message):
        """Ενημέρωση ετικέτας αποτελεσμάτων."""
        def update(dt):
            if isinstance(message, list):
                self.result_label.text = "\n".join(message)
            else:
                current_text = self.result_label.text
                self.result_label.text = current_text + "\n" + message if current_text else message
        Clock.schedule_once(update, 0)

    def run_scraping(self, instance):
        """Ξεκινάει το scraping και εμφανίζει μήνυμα."""
        self.result_label.text = "Ξεκινάμε το scraping...\nΠαρακαλώ περιμένετε."
        Thread(target=self.scraping_task).start()

    def scraping_task(self):
        """Εκτελεί το scraping σε ξεχωριστό thread."""
        try:
            main()
            clean_duplicate_products()
            analysis_results = analyze_products()  # Αποθήκευση των αποτελεσμάτων ανάλυσης
            if analysis_results:
                self.update_label(analysis_results)  # Εμφάνιση αποτελεσμάτων ανάλυσης
            else:
                self.update_label(["Δεν βρέθηκαν αποτελέσματα ανάλυσης."])
        except Exception as e:
            self.update_label([f"Σφάλμα: {str(e)}"])

    def show_isolate_products(self, instance):
        """Εμφάνιση προϊόντων Isolate."""
        self.display_results(top_isolate_products())

    def show_mass_products(self, instance):
        """Εμφάνιση προϊόντων Mass Gainer."""
        self.display_results(top_mass_gainer_products())

    def show_hydrolyzed_products(self, instance):
        """Εμφάνιση προϊόντων Hydrolyzed."""
        self.display_results(top_hydrolyzed_products())

    def show_whey_products(self, instance):
        """Εμφάνιση προϊόντων Whey."""
        self.display_results(top_whey_products())

    def display_results(self, results):
        """Εμφάνιση αποτελεσμάτων στη λίστα."""
        self.result_label.text = ""
        if results:
            self.update_label(results)
        else:
            self.update_label(["Δεν βρέθηκαν αποτελέσματα."])

if __name__ == "__main__":
    ProteinApp().run()

