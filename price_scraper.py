import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import time

# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------
BASE_URL = "https://books.toscrape.com/catalogue/"
CATALOGUE_URL = f"{BASE_URL}page-1.html"
FX_URL = "https://api.exchangerate-api.com/v4/latest/USD"
DEFAULT_CURRENCY = "KES"      # Kenyan Shilling
FALLBACK_RATE = 129.28        # USD→KES fallback (mock data)
GBP_USD_RATE = 1 / 0.741      # 1 GBP = 1.35 USD (mock data)

# ------------------------------------------------------------------
# FX HELPER
# ------------------------------------------------------------------
def get_currency_rate(target: str) -> float:
    """
    Fetch current exchange rate from USD to target currency.
    Uses fallback rate if API request fails.
    """
    try:
        data = requests.get(FX_URL, timeout=10).json()
        return data["rates"].get(target, FALLBACK_RATE)
    except Exception as e:
        print("⚠️  FX fetch failed, using fallback rate:", e)
        return FALLBACK_RATE

# ------------------------------------------------------------------
# SCRAPING WITH PAGINATION
# ------------------------------------------------------------------
def scrape_books(limit: int = 10, max_pages: int = 3):
    """
    Scrape books from multiple pages to ensure we get at least the requested limit.
    """
    books = []
    page = 1
    
    while len(books) < limit and page <= max_pages:
        try:
            url = f"{BASE_URL}page-{page}.html"
            print(f"📄 Scraping page {page}: {url}")
            
            resp = requests.get(url, timeout=10)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find all books on the page
            book_elements = soup.find_all("article", class_="product_pod")
            
            if not book_elements:
                print("No more books found.")
                break
                
            for book in book_elements:
                if len(books) >= limit:
                    break
                    
                title = book.h3.a["title"]
                price_str = book.find("p", class_="price_color").text.strip("£")
                price_gbp = float(price_str)
                
                # Get book URL for potential future use
                book_url = book.h3.a["href"]
                if book_url.startswith("../../../"):
                    book_url = book_url.replace("../../../", BASE_URL)
                elif book_url.startswith("catalogue/"):
                    book_url = BASE_URL + book_url
                
                books.append({
                    "title": title, 
                    "price_gbp": price_gbp,
                    "book_url": book_url
                })
            
            print(f"✅ Found {len(books)} books so far")
            
            # Check if there's a next page
            next_button = soup.select_one("li.next a")
            if not next_button:
                print("No more pages available.")
                break
                
            page += 1
            time.sleep(1)  # Be polite to the server
            
        except Exception as e:
            print(f"❌ Error scraping page {page}:", e)
            break
    
    return books[:limit]  # Return exactly the requested number

# ------------------------------------------------------------------
# CONVERSION
# ------------------------------------------------------------------
def convert_prices(books, target_currency):
    """
    Convert prices from GBP to target currency using USD as intermediate.
    Adds separate fields for original and converted currency details.
    """
    usd_to_target = get_currency_rate(target_currency)
    
    for book in books:
        # Convert GBP to USD
        price_usd = book["price_gbp"] * GBP_USD_RATE
        
        # Convert USD to target currency
        price_converted = round(price_usd * usd_to_target, 2)
        
        # Add detailed currency information
        book["price_usd"] = round(price_usd, 2)
        book["price_converted"] = price_converted
        book["original_currency"] = "GBP"
        book["target_currency"] = target_currency
        book["conversion_rate_gbp_to_target"] = round(GBP_USD_RATE * usd_to_target, 4)
        book["conversion_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return books

# ------------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------------
def save_csv(books, filename="book_prices.csv"):
    """Save book data to CSV file with comprehensive currency information."""
    df = pd.DataFrame(books)
    
    # Reorder columns for better readability
    columns = [
        "title", "price_gbp", "original_currency", 
        "price_usd", "price_converted", "target_currency",
        "conversion_rate_gbp_to_target", "conversion_date", "book_url"
    ]
    
    # Only include columns that exist in the data
    available_columns = [col for col in columns if col in df.columns]
    df = df[available_columns]
    
    df.to_csv(filename, index=False)
    print(f"✅ Saved {len(df)} books to {filename}")

def display_table(books):
    """Display a formatted table of book prices."""
    df = pd.DataFrame(books)
    
    # Format for display
    display_df = df.copy()
    display_df["GBP Price"] = display_df["price_gbp"].apply(lambda x: f"£{x:.2f}")
    display_df["Converted Price"] = display_df.apply(
        lambda r: f"{r['price_converted']:.2f} {r['target_currency']}", axis=1
    )
    
    print("\n📊 Book Prices:")
    print(display_df[["title", "GBP Price", "Converted Price"]].to_markdown(index=False))

def plot_prices(books):
    """Create a visualization comparing original and converted prices."""
    if not books:
        print("No data to plot.")
        return
        
    df = pd.DataFrame(books)
    
    # Normalize for comparison
    norm = df["price_converted"].max() / df["price_gbp"].max() if df["price_gbp"].max() > 0 else 1

    plt.figure(figsize=(12, 8))
    
    # Create the plot
    x_pos = range(len(df))
    plt.bar([x - 0.2 for x in x_pos], df["price_gbp"], width=0.4, label="GBP", color='blue', alpha=0.7)
    plt.bar(
        [x + 0.2 for x in x_pos],
        df["price_converted"] / norm,
        width=0.4,
        label=f"{books[0]['target_currency']} (normalized)",
        color='orange',
        alpha=0.7
    )
    
    plt.xticks(x_pos, df["title"], rotation=45, ha="right")
    plt.ylabel("Price")
    plt.title(f"Original vs Converted Prices (Normalized for Comparison)")
    plt.legend()
    plt.tight_layout()
    plt.show()

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    print("📚 Book Scraper with Currency Conversion")
    print("=" * 50)
    
    # Explain mock data usage
    print("ℹ️  Note: Using mock GBP-USD exchange rate for demonstration.")
    print("ℹ️  Fallback rates will be used if API requests fail.\n")
    
    # Get user input
    try:
        num_books = int(input("How many books to scrape? (default: 10): ") or "10")
    except ValueError:
        print("Invalid input, using default of 10 books.")
        num_books = 10
        
    target_currency = input(
        f"Target currency (3-letter code, default {DEFAULT_CURRENCY}): "
    ).strip().upper() or DEFAULT_CURRENCY

    # Scrape books with pagination
    print(f"\n🔄 Scraping {num_books} books...")
    books = scrape_books(limit=num_books, max_pages=5)
    
    if not books:
        print("❌ No books were scraped. Exiting.")
        return
        
    print(f"✅ Successfully scraped {len(books)} books")
    
    # Convert prices
    books = convert_prices(books, target_currency)
    
    # Display and save results
    display_table(books)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"book_prices_{target_currency}_{timestamp}.csv"
    save_csv(books, filename)
    
    # Ask about plotting
    plot_choice = input("\nShow price comparison chart? (y/n, default: y): ").strip().lower()
    if plot_choice != "n":
        plot_prices(books)

if __name__ == "__main__":
    main()