
````markdown
# 🩺 MyFootDr Clinic Scraper

A clean and reliable Python web scraper that collects clinic data (name, address, phone, email, and services) from the **archived MyFootDr** website via the Wayback Machine.  
The scraper uses `requests` and `BeautifulSoup` for parsing and exports the data into a structured CSV file.

---

## 🚀 Features

- 🗺 Scrapes clinics grouped by **region**
- 📞 Extracts key info: Name, Address, Phone, Email, Services
- ⏱ Handles timeouts, retries, and random delays
- 🧹 Cleans and validates phone numbers and emails
- 📄 Exports results into a `clinics.csv` file
- ⚙️ Fully configurable via `ScraperConfig`

---

## 🧠 Technologies Used

- **Python 3.10+**
- **BeautifulSoup4**
- **Requests**
- **lxml**
- **Dataclasses**

---

## 🛠️ Installation

Clone this repository and set up the environment:

```bash
git clone https://github.com/Mr-N0b0dy1/scraper.git
cd scraper
````

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Usage

Run the scraper:

```bash
python scraper.py
```

The scraper will:

1. Fetch all **regions** from the MyFootDr “Our Clinics” page.
2. Visit each region and extract **clinic links**.
3. Visit each clinic page and scrape details (name, address, phone, email, services).
4. Write results into `clinics.csv`.

Example snippet to customize config:

```python
from scraper import MyFootDrScraper, ScraperConfig

config = ScraperConfig(
    min_delay=1.5,
    max_delay=2.5,
    max_retries=5,
    output_file="output_clinics.csv"
)

with MyFootDrScraper(config) as scraper:
    scraper.scrape_all_clinics()
```

---

## 📂 Project Structure

```
scraper/
│
├── scraper.py             # Main scraper code
├── requirements.txt       # Project dependencies
├── README.md              # Documentation
├── LICENSE                # MIT License
├── .gitignore             # Ignored files and folders
└── clinics.csv            # (Generated output file)
```

---

## 🧩 Example Output (CSV)

| Region     | Clinic_Name        | Address              | Phone          | Email                                               | Services             |
| ---------- | ------------------ | -------------------- | -------------- | --------------------------------------------------- | -------------------- |
| Queensland | My FootDr Brisbane | 123 Main Street, QLD | (07) 1234 5678 | [info@myfootdr.com.au](mailto:info@myfootdr.com.au) | Orthotics; Foot Care |

---

## 🧾 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Pull requests, suggestions, and improvements are welcome!
If you find an issue or want to enhance functionality (like async scraping or multi-threading), feel free to open an issue.

---

## ✉️ Contact

**Author:** Sanjay Aray
**Email:** [sanjayaranapaheli@gmail.com](mailto:sanjayaranapaheli@gmail.com)
**GitHub:** [Mr-N0b0dy1](https://github.com/Mr-N0b0dy1)

---

⭐ **If you found this helpful, give the repo a star on GitHub!**

