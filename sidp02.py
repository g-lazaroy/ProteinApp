from bs4 import BeautifulSoup 
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from time import sleep
import time
from typing import List, Dict, Optional
import sqlite3
import os


base_dir = os.path.dirname(os.path.abspath(__file__))  # Παίρνει τη διαδρομή του φακέλου του τρέχοντος script
db_path = os.path.join(base_dir, "products.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


def insert_data(name, price, source_url):
    if not name or not price:
        return
        
    try:
        # Καθαρισμός τιμής
        if isinstance(price, str):
            price = price.replace('€', '').replace(',', '.').strip()
        price = float(price)
        
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()  
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        source_url TEXT NOT NULL
        )
    """)     
        cursor.execute("INSERT INTO products (name, price, source_url) VALUES (?, ?, ?)", (name, price, source_url))
        conn.commit()
        conn.close()
        
    except (ValueError, sqlite3.Error) as e:
        print(f"Σφάλμα εισαγωγής προϊόντος {name}: {e}")
        
def reset_database():
    """Reset the database by dropping and recreating the table."""
    connection = sqlite3.connect('products.db')
    cursor = connection.cursor()

    # Διαγραφή του πίνακα αν υπάρχει
    cursor.execute("DROP TABLE IF EXISTS products")

    # Δημιουργία του πίνακα από την αρχή
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            source_url TEXT NOT NULL
        )
    """)
    connection.commit()
    connection.close()
    print("Database has been reset.")
        
class WebScraper:
    def __init__(self):
        self.setup_selenium_options()
        
    def setup_selenium_options(self) -> Options:
        """Initialize Chrome options for Selenium"""
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--disable-gpu')
        return self.options

    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from URL using requests"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return BeautifulSoup(response.text, "lxml")
            print(f"Error: {response.status_code}")
            return None
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None

    def extract_price(self, price_tag) -> str:
        """Extract price from a price tag element"""
        if price_tag:
            price = price_tag.find("strong") or price_tag.find("span")
            return price.text.strip() if price else "No price"
        return "No price"

    def clean_text(self, text: str) -> str:
        """Clean text by removing non-ASCII characters"""
        return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()

    def scrape_katerelos(self, urls: List[str]) -> List[Dict]:
        """Scrape products from Katerelos website"""
        products = []
        for url in urls:
            soup = self.get_soup(url)
            if not soup:
                continue

            protein_elements = soup.find_all("div", class_="block_btm")
            print(f"Found {len(protein_elements)} products on {url}")
            
            for protein in protein_elements:
                name = self.clean_text(protein.find("h4").text.strip())
                price = self.extract_price(protein.find("h6"))
                products.append({"name": name, "price": price})
                #print(f"Product: {name}, Price: {price}")
                insert_data(name, price, url)
        return products

    def scrape_fitrace(self, urls: List[str]) -> List[Dict]:
        """Scrape products from Fitrace website"""
        products = []
        for url in urls:
            soup = self.get_soup(url)
            if not soup:
                continue

            protein_elements = soup.find_all("div", class_="description")
            print(f"Found {len(protein_elements)} products on {url}")
            
            for protein in protein_elements:
                name = self.clean_text(protein.find("h4").text.strip())
                price = self.extract_price(protein.find_next("div", class_="price"))
                products.append({"name": name, "price": price})
                #print(f"Product: {name}, Price: {price}")
                insert_data(name, price, url)
                
        return products

    def scrape_growling(self, url: str) -> List[Dict]:
        """Scrape products from Growling website"""
        products = []
        driver = webdriver.Chrome(options=self.options)
        
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 40)
            
            while True:
                try:
                    load_more = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'load-more'))
                    )
                    if load_more.is_displayed():
                        print("Found Load More button. Clicking...")
                        driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                        sleep(1)
                        load_more.click()
                        sleep(3)
                    else:
                        break
                except:
                    #print("No more Load More button found.")
                    break

            soup = BeautifulSoup(driver.page_source, "lxml")
            proteins = soup.find_all("h3", class_="heading-title product-name")
            print(f"\nFound {len(proteins)} products on Growling")
            
            for protein in proteins:
                try:
                    name = protein.find("a").text.strip()
                    price_tag = protein.find_next("span", class_="price")
                    price = price_tag.text.strip() if price_tag else "No price"
                    products.append({"name": name, "price": price})
                    #print(f"Product: {name}, Price: {price}")
                    insert_data(name, price, url)
                except Exception as e:
                    print(f"Error processing product: {e}")
                    
        finally:
            driver.quit()
            
        return products

    def scrape_fit1(self, urls: List[str]) -> List[Dict]:
        """Scrape products from Fit1 website"""
        products = []
        driver = webdriver.Chrome(options=self.options)
        
        try:
            for url in urls:
                print(f"\nProcessing Fit1 URL: {url}")
                driver.get(url)
                self.scroll_to_bottom(driver)
                
                soup = BeautifulSoup(driver.page_source, "lxml")
                proteins = soup.find_all("div", class_="brand-line")
                prices = soup.find_all("div", class_="price-line")
                print(f"Found {len(proteins)} products")
                
                for i, protein in enumerate(proteins):
                    try:
                        brand_name = protein.text.strip()
                        title = protein.find_next("h3").get('title', '').strip()
                        pack_info = protein.find_next("div", class_="pack-line").text.strip()
                        full_name = f"{brand_name} {title} {pack_info}"
                        
                        price = "No price"
                        if i < len(prices):
                            price_element = prices[i].find("b", class_="green") or prices[i].find("b", class_="normalp")
                            if price_element:
                                price = self.process_price(price_element)
                                
                        products.append({"name": full_name, "price": price})
                        #print(f"Product: {full_name}, Price: {price}")
                        insert_data(full_name, price, url)
                    except Exception as e:
                        print(f"Error processing product: {e}")
                        
        finally:
            driver.quit()
            
        return products

    

    def scrape_gymbeam(self, base_url: str) -> List[Dict]:
        """Scrape products from GymBeam website, including size and price from dropdown"""
        products = []
        driver = webdriver.Chrome(options=self.options)
    
        try:
            driver.get(base_url)
            previous_count = 0
        
            while True:
                try:
                    current_products = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "product-item"))
                    )
                    current_count = len(current_products)
                
                    if current_count > previous_count:
                        previous_count = current_count

                        try:
                            load_more = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.CLASS_NAME, "amscroll-load-button"))
                            )
                            driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", load_more)
                            time.sleep(2)
                        except Exception:
                            break
                    else:
                        break
                
                except Exception:
                    break
        
            soup = BeautifulSoup(driver.page_source, "lxml")
            product_elements = soup.find_all("div", class_="product details product-item-details")
        
            for product in product_elements:
                try:
                    product_link = product.find("a", class_="product-item-link")
                    if not product_link:
                        continue
                    
                    product_name = product_link.text.strip()
                    product_url = product_link['href']
                
                    variants = self.get_gymbeam_variants(driver, product_url)
                    for variant in variants:
                        product_full_name = f"{product_name} - {variant['size']}"
                        
                        # Insert data into the database
                        insert_data(product_full_name, variant['price'], product_url)
                        
                        products.append({
                            "name": product_full_name,
                            "price": variant['price'],
                            "url": product_url
                        })
            
                except Exception:
                    continue
    
        finally:
            driver.quit()
        
        print(f"Found {len(products)} products on GymBeam")
        return products

    def get_gymbeam_variants(self, driver: webdriver.Chrome, product_url: str) -> List[Dict]:
        """Get variant prices for GymBeam product"""
        variants = []
        try:
            driver.get(product_url)
            dropdown = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'select[aria-label="Γραμμάρια (γρ)"]'))
            )
            select = Select(dropdown)
        
            for option in select.options:
                select.select_by_visible_text(option.text)
                time.sleep(1)
                price_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-test="hp-bestsellers-price"]'))
                )
                variants.append({
                    "size": option.text,
                    "price": price_element.text.strip()
                })
    
        except Exception:
            pass
    
        return variants


    def scroll_to_bottom(self, driver: webdriver.Chrome):
        """Scroll to bottom of page for infinite loading"""
        scroll_attempts = 0
        max_attempts = 15
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while scroll_attempts < max_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 100);")
            sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(2)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
            last_height = new_height
            
            try:
                if driver.find_element(By.CLASS_NAME, "no-more-products").is_displayed():
                    break
            except:
                pass

    def process_price(self, price_element) -> str:
        """Process price element to extract clean price"""
        main_price = price_element.text.strip().replace('€', '').strip()
        sup_element = price_element.find("sup")
        if sup_element:
            main_price = main_price.replace(sup_element.text, "")
            return f"{main_price},{sup_element.text.strip()}"
        return main_price


def main():
    reset_database()
    scraper = WebScraper()
    
    # Katerelos URLs
    katerelos_urls = [
        "https://www.katerelosfitness.gr/category/794_800_797/prwteines_oros_galaktos.html",
        "https://www.katerelosfitness.gr/category/794_800_797/prwteines_oros_galaktos.html?page=2",
        "https://www.katerelosfitness.gr/category/794_800_778/prwteines_apomonwmenos_oros_galaktos.html",
        "https://www.katerelosfitness.gr/category/794_800_778/prwteines_apomonwmenos_oros_galaktos.html?page=2",
        "https://www.katerelosfitness.gr/category/794_800_798/prwteines_ydrolymenos_oros_galaktos.html"
    ]
    print("\n=== Scraping Katerelos ===")
    katerelos_products = scraper.scrape_katerelos(katerelos_urls)
    
    # Fitrace URLs
    fitrace_urls = [
        'https://www.fitrace.gr/category/161/prwteines.html?page=1&sort=5a',
        'https://www.fitrace.gr/category/161/prwteines.html?page=2&sort=5a',
        'https://www.fitrace.gr/category/161/prwteines.html?page=3&sort=5a'
    ]
    print("\n=== Scraping Fitrace ===")
    fitrace_products = scraper.scrape_fitrace(fitrace_urls)
    
    # Growling
    print("\n=== Scraping Growling ===")
    growling_products = scraper.scrape_growling('https://growlingstore.gr/product-category/proteines/')
    
    # Fit1 URLs
    fit1_urls = [
        'https://fit1.gr/category/whey-protein',
        'https://fit1.gr/category/whey-protein-isolate',
        'https://fit1.gr/category/hydrolyzed-whey-protein'
    ]
    print("\n=== Scraping Fit1 ===")
    fit1_products = scraper.scrape_fit1(fit1_urls)
    
    # GymBeam
    print("\n=== Scraping GymBeam ===")
    gymbeam_products = scraper.scrape_gymbeam("https://gymbeam.gr/proteini-orou-galaktos")


if __name__ == "__main__":
 main()

def analyze_products():
    # Σύνδεση με τη βάση δεδομένων
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()

    try:
        # Δημιουργία του πίνακα αν δεν υπάρχει
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            source_url TEXT            
        )
        """)
        conn.commit()

        # Παίρνουμε όλα τα προϊόντα
        cursor.execute("SELECT id, name, price, source_url FROM products")
        products = cursor.fetchall()

        # Λίστα για τα προϊόντα με υπολογισμένη τιμή ανά γραμμάριο
        products_with_price_per_gram = []

        for product in products:
            product_id, name, price, url = product

            try:
                # Μετατροπή της τιμής σε float αφού αφαιρεθούν μη απαραίτητα σύμβολα
                clean_price = float(str(price).replace('€', '').replace(',', '.').strip())

                # **Διόρθωση τιμής αν είναι μικρότερη από 1**
                if clean_price < 1:
                    clean_price *= 100
                    cursor.execute(
                        "UPDATE products SET price = ? WHERE id = ?",
                        (f"{clean_price:.2f}", product_id)
                    )
                    conn.commit()

                # Εύρεση γραμμαρίων στο όνομα του προϊόντος
                grams_match = re.search(r"(\d+)\s*(g|gr|grams|Γραμμάρια)", name, re.IGNORECASE)
                if grams_match:
                    grams = int(grams_match.group(1))

                    # Υπολογισμός τιμής ανά γραμμάριο
                    price_per_gram = clean_price / grams

                    products_with_price_per_gram.append((product_id, name, clean_price, grams, price_per_gram, url))

            except (ValueError, TypeError, ZeroDivisionError) as e:
                continue
            
        # Ταξινόμηση με βάση την τιμή ανά γραμμάριο και πάρε τα top 5
        sorted_products = sorted(products_with_price_per_gram, key=lambda x: x[4])[:5]

        # Επιστρέφει τα αποτελέσματα
        result_text = []
        for i, product in enumerate(sorted_products, 1):
            product_id, name, price, grams, price_per_gram, url = product
            result_text.append(f"Θέση #{i}\nΠροϊόν: {name}\nΤιμή: {price}€\nΒάρος: {grams}g\nΤιμή ανά γραμμάριο: {price_per_gram:.4f}€\nURL: {url}\n{'-'*100}")

        return result_text  # Επιστρέφει τη λίστα με τα αποτελέσματα

    except sqlite3.Error as e:
        return [f"Σφάλμα βάσης δεδομένων: {e}"]
    finally:
        conn.close()


        

def clean_duplicate_products():
    """
    Καθαρίζει τη βάση δεδομένων από διπλότυπα προϊόντα, κρατώντας το προϊόν με τη χαμηλότερη τιμή.
    Αν δύο προϊόντα έχουν την ίδια τιμή, συνδυάζει τα URLs τους.
    """
    conn = sqlite3.connect('products.db')  # Ονομασία της βάσης δεδομένων
    cursor = conn.cursor()

    try:
        # Λήψη όλων των προϊόντων από τη βάση δεδομένων
        cursor.execute("SELECT id, name, price, source_url FROM products")
        products = cursor.fetchall()

        print(f"Total products fetched: {len(products)}")  # Debug

        # Dictionary για μοναδικά προϊόντα
        unique_products = {}

        for prod_id, name, price, url in products:
            try:
                # Καθαρισμός τιμής και κανονικοποίηση ονόματος
                clean_price = float(str(price).replace('€', '').replace(',', '.').strip())
                normalized_name = re.sub(r'\s+', ' ', name).strip().lower()
                
                current_data = unique_products.get(normalized_name)
                
                if current_data is None:
                    # Αν δεν υπάρχει, το προσθέτουμε
                    unique_products[normalized_name] = {
                        'name': name,
                        'price': clean_price,
                        'urls': {url}
                    }
                else:
                    # Αν υπάρχει, συγκρίνουμε τιμές
                    if clean_price < current_data['price']:
                        # Αν βρεθεί χαμηλότερη τιμή, ενημερώνουμε
                        current_data['price'] = clean_price
                        current_data['urls'] = {url}
                    elif clean_price == current_data['price']:
                        # Αν οι τιμές είναι ίδιες, προσθέτουμε το URL
                        current_data['urls'].add(url)

            except (ValueError, TypeError) as e:
                print(f"Error processing product {prod_id}: {e}")
                continue

        print(f"Unique products found: {len(unique_products)}")  # Debug

        # Καθαρισμός του πίνακα `products`
        cursor.execute("DELETE FROM products")
        conn.commit()

        # Εισαγωγή καθαρισμένων δεδομένων πίσω στη βάση
        for product_data in unique_products.values():
            cursor.execute("""
                INSERT INTO products (name, price, source_url)
                VALUES (?, ?, ?)
            """, (
                product_data['name'],
                product_data['price'],
                ', '.join(product_data['urls'])
            ))
        conn.commit()
        print("Database cleaned and updated with unique products.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()



def get_top_products_by_category(category_keywords, category_name, top_n=5):
    """
    Επιστρέφει τα Top προϊόντα μιας κατηγορίας με βάση λέξεις-κλειδιά.
    """
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    results = []

    try:
        cursor.execute("SELECT id, name, price, source_url FROM products")
        products = cursor.fetchall()

        filtered_products = []

        for product in products:
            product_id, name, price, url = product

            if any(keyword.lower() in name.lower() for keyword in category_keywords):
                try:
                    clean_price = float(str(price).replace('€', '').replace(',', '.').strip())

                    # Βελτιωμένο pattern για να αναγνωρίζει περισσότερες μορφές βάρους
                    weight_patterns = [
                        r"(\d+(?:\.\d+)?)\s*(?:g|gr|grams|Γραμμάρια)",
                        r"(\d+(?:\.\d+)?)\s*(?:kg|KG|κιλά|kgs)",
                        r"(\d+(?:\.\d+)?)\s*k(?=\s|$)"
                    ]

                    grams = None
                    for pattern in weight_patterns:
                        match = re.search(pattern, name, re.IGNORECASE)
                        if match:
                            weight = float(match.group(1))
                            if 'kg' in pattern.lower() or 'k' in pattern.lower():
                                grams = int(weight * 1000)
                            else:
                                grams = int(weight)
                            break

                    if grams:
                        price_per_gram = clean_price / grams
                        filtered_products.append((product_id, name, clean_price, grams, price_per_gram, url))

                except (ValueError, TypeError, ZeroDivisionError) as e:
                    results.append(f"Σφάλμα κατά την επεξεργασία του προϊόντος {product_id}: {e}")
                    continue

        sorted_products = sorted(filtered_products, key=lambda x: x[4])[:top_n]

        results.append(f"\nΤα Top {top_n} προϊόντα για την κατηγορία '{category_name}':")
        results.append("-" * 100)
        
        for i, product in enumerate(sorted_products, 1):
            product_id, name, price, grams, price_per_gram, url = product
            results.append(f"Θέση #{i}")
            results.append(f"Προϊόν: {name}")
            results.append(f"Τιμή: {price}€")
            results.append(f"Βάρος: {grams}g")
            results.append(f"Τιμή ανά γραμμάριο: {price_per_gram:.4f}€")
            results.append(f"URL: {url}")
            results.append("-" * 100)

        return results

    except sqlite3.Error as e:
        return [f"Σφάλμα βάσης δεδομένων: {e}"]
    finally:
        conn.close()

def top_isolate_products():
    keywords = ['iso', 'isolated', 'απομονωμένος ορός γάλακτος']
    return get_top_products_by_category(keywords, "Isolate")

def top_mass_gainer_products():
    keywords = ['mass', 'gainer', 'μάζα']
    return get_top_products_by_category(keywords, "Mass Gainer")

def top_hydrolyzed_products():
    keywords = ['hydro', 'hydrolized', 'υδρολυμένος']
    return get_top_products_by_category(keywords, "Hydrolyzed")

def top_whey_products():
    keywords = ['whey', 'ορρός γάλακτος']
    return get_top_products_by_category(keywords, "Whey")

# top_whey_products()
# top_isolate_products()
# top_mass_gainer_products()
# top_hydrolyzed_products()


# Κλήση της συνάρτησης
# if __name__ == "__main__":
#  clean_duplicate_products()



# # # # Κλήση της συνάρτησης

# analyze_products()

