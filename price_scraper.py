import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------
BASE_CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
FX_URL = "https://api.exchangerate-api.com/v4/latest/USD"
DEFAULT_CURRENCY = "KES"      # Kenyan Shilling
FALLBACK_RATE = 129.28        # USD→KES fallback
GBP_USD_RATE = 1 / 0.741      # 1 GBP = 1.35 USD (live: 1/0.741)

# ------------------------------------------------------------------
# FX HELPER
# ------------------------------------------------------------------
def get_currency_rate(target: str) -> float:
    try:
        data = requests.get(FX_URL, timeout=10).json()
        return data["rates"].get(target, FALLBACK_RATE)
    except Exception as e:
        print("⚠️  FX fetch failed, using fallback:", e)
        return FALLBACK_RATE

# ------------------------------------------------------------------
# SCRAPING
# ------------------------------------------------------------------
def scrape_books(limit: int = 10):
    try:
        resp = requests.get(BASE_CATALOGUE_URL, timeout=10)
        resp.encoding = "utf-8"                       # fix encoding
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print("❌  Scraping error:", e)
        return None

    books = []
    for book in soup.find_all("article", class_="product_pod")[:limit]:
        title = book.h3.a["title"]
        price_str = book.find("p", class_="price_color").text.strip("£")
        price_gbp = float(price_str)
        books.append({"title": title, "price_gbp": price_gbp})
    return books

# ------------------------------------------------------------------
# CONVERSION
# ------------------------------------------------------------------
def convert_prices(books, target):
    usd_to_target = get_currency_rate(target)
    for b in books:
        price_usd = b["price_gbp"] * GBP_USD_RATE
        b["price_converted"] = round(price_usd * usd_to_target, 2)
        b["target_currency"] = target
    return books

# ------------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------------
def save_csv(books, name="book_prices.csv"):
    df = pd.DataFrame(books)
    df["conversion_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(name, index=False)
    print(f"✅ Saved to {name}")

def display_table(books):
    df = pd.DataFrame(books)
    df["price_gbp"] = df["price_gbp"].apply(lambda x: f"£{x:.2f}")
    df["price_converted"] = df.apply(
        lambda r: f"{r['price_converted']:.2f} {r['target_currency']}", axis=1
    )
    print("\n", df[["title", "price_gbp", "price_converted"]].to_markdown(index=False))

def plot_prices(books):
    df = pd.DataFrame(books)
    norm = df["price_converted"].max() / df["price_gbp"].max()

    plt.figure(figsize=(12, 6))
    plt.bar(df["title"], df["price_gbp"], width=0.4, label="GBP")
    plt.bar(
        df["title"],
        df["price_converted"] / norm,
        width=0.4,
        label=f"{DEFAULT_CURRENCY} (norm)",
        align="edge",
    )
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Price")
    plt.title("Original vs Converted Prices")
    plt.legend()
    plt.tight_layout()
    plt.show()

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    print("📚 Scraping books …")
    books = scrape_books(10)
    if not books:
        return

    target = input(f"Target currency (default {DEFAULT_CURRENCY}): ").strip().upper() or DEFAULT_CURRENCY
    books = convert_prices(books, target)

    display_table(books)
    save_csv(books)
    plot_prices(books)

if __name__ == "__main__":
    main()