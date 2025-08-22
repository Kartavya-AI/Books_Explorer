#imports
import os
import sqlite3
import requests
import urllib.parse
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv


# Config

load_dotenv()

GOOGLE_BOOKS_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")  
DB_PATH = "books_app.db"


# Database (simple SQLite)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        query TEXT,
        result_count INTEGER,
        ts TEXT
    )""")
    conn.commit()
    conn.close()

def add_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def check_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE username=? AND password=?", (username, password))
    ok = cur.fetchone()
    conn.close()
    return ok

def log_search(username, query, count):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO searches (username, query, result_count, ts) VALUES (?, ?, ?, ?)",
                (username, query, count, datetime.now().isoformat()))
    conn.commit()
    conn.close()


# Google Books helper

def search_books_google(query, max_results=6):
    """
    Query Google Books API and return a list of structured results.
    Each result is a dict with keys:
      title, authors, genre, formats (list), price (str), google_info_link, google_buy_link, amazon_link, flipkart_link
    """
    q = urllib.parse.quote_plus(query)
    key_part = f"&key={GOOGLE_BOOKS_KEY}" if GOOGLE_BOOKS_KEY else ""
    url = f"https://www.googleapis.com/books/v1/volumes?q={q}&maxResults={max_results}{key_part}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return []

    data = resp.json()
    items = data.get("items", [])
    results = []

    for item in items:
        info = item.get("volumeInfo", {})
        sale = item.get("saleInfo", {})
        access = item.get("accessInfo", {})

        title = info.get("title", "Unknown title")
        authors = info.get("authors", [])  # list
        categories = info.get("categories", [])  # list -> genre
        genre = ", ".join(categories) if categories else "Unknown"
        formats = set()
        # Google Books indicates ebook availability in saleInfo/accessInfo
        if sale.get("isEbook") or access.get("epub", {}).get("isAvailable") or access.get("pdf", {}).get("isAvailable"):
            formats.add("E-book")
        if sale.get("saleability") and "NOT_FOR_SALE" not in sale.get("saleability", ""):
            formats.add("Print / Purchase")
        if info.get("industryIdentifiers"):
            formats.add("Print (details available)")

        if not formats:
            formats.add("Unknown")

        # Price extraction
        price_str = "N/A"
        list_price = sale.get("listPrice") or sale.get("retailPrice")
        if list_price and isinstance(list_price, dict):
            amount = list_price.get("amount")
            currency = list_price.get("currencyCode", "")
            if amount is not None:
                price_str = f"{amount} {currency}".strip()

        # Google Links
        info_link = info.get("infoLink", "")
        buy_link = sale.get("buyLink") or ""

        # Construct Amazon & Flipkart search links for the book (best-effort)
        search_term = f"{title} {' '.join(authors)}".strip()
        amazon_query = urllib.parse.quote_plus(search_term)
        amazon_link = f"https://www.amazon.in/s?k={amazon_query}"
        flipkart_query = urllib.parse.quote_plus(search_term)
        flipkart_link = f"https://www.flipkart.com/search?q={flipkart_query}"

        results.append({
            "title": title,
            "authors": ", ".join(authors) if authors else "Unknown",
            "genre": genre,
            "formats": ", ".join(sorted(formats)),
            "price": price_str,
            "google_info_link": info_link,
            "google_buy_link": buy_link,
            "amazon_link": amazon_link,
            "flipkart_link": flipkart_link
        })

    return results

# Streamlit UI
def show_login():
    st.title("📚 Books Explorer — Login")
    st.write("Simple demo login (local only).")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if check_user(username, password):
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with col2:
        st.write("New user? Create account below.")
        new_user = st.text_input("New username", key="new_user")
        new_pass = st.text_input("New password", type="password", key="new_pass")
        if st.button("Create account"):
            if new_user and new_pass:
                ok = add_user(new_user, new_pass)
                if ok:
                    st.success("Account created. Now log in.")
                else:
                    st.error("Username exists. Pick another.")
            else:
                st.error("Enter username and password.")

def show_search_ui():
    st.sidebar.success(f"Logged in as {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.pop("user", None)
        st.rerun()

    st.title("📚 Books Explorer — Search")
    st.write("Type a book title, author, or genre. Results are strictly book-related and returned in structured format.")

    query = st.text_input("Search (title / author / genre)", key="search_q")
    max_results = st.slider("Max results", min_value=1, max_value=12, value=6)

    if st.button("Search") and query:
        with st.spinner("Searching Google Books..."):
            results = search_books_google(query, max_results=max_results)
        # Log the search
        log_search(st.session_state.user, query, len(results))
        if not results:
            st.warning("No books found for that query.")
            return

        # Display structured results
        st.markdown("## 🔎 Structured Results")
        for i, b in enumerate(results, start=1):
            st.markdown(f"### {i}. {b['title']}")
            st.markdown(f"- **Author(s):** {b['authors']}")
            st.markdown(f"- **Genre / Category:** {b['genre']}")
            st.markdown(f"- **Format(s):** {b['formats']}")
            st.markdown(f"- **Price:** {b['price']}")
            st.markdown(f"- **Buy options:**")
            # Google info link
            if b['google_info_link']:
                st.markdown(f"  - Google Books info: [{b['google_info_link']}]({b['google_info_link']})")
            else:
                st.markdown(f"  - Google Books info: Not available")
            # Google buy link
            if b['google_buy_link']:
                st.markdown(f"  - Google Books buy link: [{b['google_buy_link']}]({b['google_buy_link']})")
            else:
                st.markdown(f"  - Google Books buy link: Not available")
            # Amazon & Flipkart
            st.markdown(f"  - Amazon (search): [{b['amazon_link']}]({b['amazon_link']})")
            st.markdown(f"  - Flipkart (search): [{b['flipkart_link']}]({b['flipkart_link']})")
            st.markdown("---")

    # Show recent searches by this user
    st.markdown("### 🔁 Your recent searches (local)")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT query, result_count, ts FROM searches WHERE username=? ORDER BY id DESC LIMIT 8", (st.session_state.user,))
    rows = cur.fetchall()
    conn.close()
    if rows:
        for q, cnt, ts in rows:
            st.write(f"- **{q}** — {cnt} results — {ts}")
    else:
        st.write("No searches yet.")

def main():
    st.set_page_config(page_title="Books Explorer", page_icon="📚", layout="wide")
    init_db()
    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.user:
        show_login()
    else:
        show_search_ui()

if __name__ == "__main__":
    main()
