import requests
from bs4 import BeautifulSoup
import csv
import time
import logging
from urllib.parse import urljoin
import re
from dataclasses import dataclass
from typing import List, Optional, Set
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    base_url: str = "https://web.archive.org/web/20250708180027/https://www.myfootdr.com.au"
    min_delay: float = 1.0
    max_delay: float = 2.0
    max_retries: int = 3
    request_timeout: int = 10
    output_file: str = 'clinics.csv'


class ClinicData:
    
    def __init__(self, name: str, address: str, phone: str, email: str, services: str, url: str, region: str = ""):
        self.name = name
        self.address = address
        self.phone = self._normalize_phone(phone)
        self.email = self._validate_email(email)
        self.services = services
        self.url = url
        self.region = region
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        if phone == "Not found":
            return phone
        cleaned = re.sub(r'[^\d\-\s\(\)]', '', phone).strip()
        return cleaned if cleaned else "Not found"
    
    @staticmethod
    def _validate_email(email: str) -> str:
        if email == "Not found":
            return email
        match = re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email)
        if match:
            return email
        logger.warning(f"Invalid email format: {email}")
        return "Not found"
    
    def to_dict(self) -> dict:
        return {
            'Region': self.region,
            'Clinic_Name': self.name,
            'Address': self.address,
            'Phone': self.phone,
            'Email': self.email,
            'Services': self.services
        }


class MyFootDrScraper:
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.seen_clinic_urls: Set[str] = set()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        
    def delay(self):
        import random
        time.sleep(random.uniform(self.config.min_delay, self.config.max_delay))
        
    def safe_request(self, url: str, max_retries: Optional[int] = None) -> Optional[requests.Response]:
        max_retries = max_retries or self.config.max_retries
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Requesting: {url}")
                response = self.session.get(url, timeout=self.config.request_timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Timeout: {url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Connection error: {url}")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - HTTP {e.response.status_code}: {url}")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Error: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        
        logger.error(f"Failed after {max_retries} attempts: {url}")
        return None

    def extract_regions(self) -> List[dict]:
        regions = []
        url = f"{self.config.base_url}/our-clinics/"
        response = self.safe_request(url)
        
        if not response:
            logger.error("Could not fetch main clinics page")
            return regions
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        selectors = [
            '.region-list a[href*="/regions/"]',
            '.clinic-regions a[href*="/regions/"]',
            '[class*="region"] a[href*="/regions/"]',
            'a[href*="/regions/"]'
        ]
        
        seen_regions = set()
        for selector in selectors:
            links = soup.select(selector)
            
            for link in links:
                href = link.get('href', '')
                full_url = urljoin(self.config.base_url, href)
                
                if full_url not in seen_regions:
                    region_name = link.get_text(strip=True) or href.split('/')[-1].replace('-', ' ').title()
                    regions.append({'name': region_name, 'url': full_url})
                    seen_regions.add(full_url)
            
            if regions:
                break
        
        logger.info(f"Found {len(regions)} regions")
        return regions

    def extract_clinics_from_region(self, region_url: str) -> List[dict]:
        clinics = []
        response = self.safe_request(region_url)
        
        if not response:
            logger.warning(f"Failed to fetch region: {region_url}")
            return clinics
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        clinic_selectors = [
            '.clinic-list a', '.clinic-item a', '.clinic-name a',
            'h3 a', 'article a', '.entry-title a', 'a[href*="/our-clinics/"]'
        ]
        
        for selector in clinic_selectors:
            links = soup.select(selector)
            
            for link in links:
                href = link.get('href', '')
                full_url = urljoin(self.config.base_url, href)
                clinic_name = link.get_text(strip=True)
                
                if '/our-clinics/' in href and '/regions/' not in href and clinic_name:
                    if clinic_name not in ['Our Clinics', 'Clinics', ''] and full_url not in self.seen_clinic_urls:
                        clinics.append({'name': clinic_name, 'url': full_url})
            
            if clinics:
                break
                
        logger.info(f"Found {len(clinics)} clinics in region")
        return clinics

    def extract_clinic_details(self, clinic_url: str) -> Optional[ClinicData]:
        if clinic_url in self.seen_clinic_urls:
            logger.debug(f"Skipping duplicate: {clinic_url}")
            return None
        
        response = self.safe_request(clinic_url)
        if not response:
            logger.warning(f"Failed to fetch clinic: {clinic_url}")
            return None
        
        self.seen_clinic_urls.add(clinic_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        try:
            clinic = ClinicData(
                name=self._extract_name(soup),
                address=self._extract_address(soup),
                phone=self._extract_phone(soup),
                email=self._extract_email(soup),
                services=self._extract_services(soup),
                url=clinic_url
            )
            return clinic
        except Exception as e:
            logger.error(f"Error extracting {clinic_url}: {e}")
            return None

    def _extract_name(self, soup: BeautifulSoup) -> str:
        name_element = soup.select_one('h1.entry-title')
        if name_element:
            return name_element.get_text(strip=True)
        logger.warning("Clinic name not found")
        return "Not found"

    def _extract_address(self, soup: BeautifulSoup) -> str:
        address_div = soup.select_one('.address')
        if not address_div:
            logger.warning("Address not found")
            return "Not found"

        address_copy = BeautifulSoup(str(address_div), 'html.parser').select_one('.address')
        
        for tag in address_copy.find_all(['i', 'svg', 'span']):
            tag.decompose()

        for br in address_copy.find_all('br'):
            br.replace_with(' ')

        address_text = address_copy.get_text(" ", strip=True)
        address_text = re.sub(r'^\s*[^A-Za-z0-9]*', '', address_text).strip()
        
        return address_text if address_text else "Not found"

    def _extract_phone(self, soup: BeautifulSoup) -> str:
        phone_tag = soup.select_one('a.rose-button[href^="tel:"]')
        if phone_tag:
            display_text = phone_tag.get_text(strip=True)
            phone_match = re.search(r'(\(?\d{2}\)?[-.\s]?\d{4}[-.\s]?\d{4})', display_text)
            if phone_match:
                return phone_match.group(1).strip()
        
        tel_link = soup.find('a', href=re.compile(r'^tel:'))
        if tel_link:
            return tel_link['href'].replace('tel:', '').strip()
        
        contact_sections = soup.select('.contact, .phone, .clinic-info, [class*="contact"]')
        if not contact_sections:
            contact_sections = [soup]
        
        phone_pattern = r'\(?\d{2}\)?[-.\s]?\d{4}[-.\s]?\d{4}'
        for section in contact_sections:
            phones = re.findall(phone_pattern, section.get_text())
            if phones:
                return phones[0]
        
        logger.warning("Phone not found")
        return "Not found"

    def _extract_email(self, soup: BeautifulSoup) -> str:
        email_link = soup.find('a', href=re.compile(r'^mailto:', re.I))
        if email_link:
            email = email_link['href'].replace('mailto:', '').strip()
            if '@' in email:
                return email
        
        contact_sections = soup.select('.contact, .email, .clinic-info, [class*="contact"]')
        if not contact_sections:
            contact_sections = [soup.select_one('body')] if soup.select_one('body') else [soup]
        
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w{2,}'
        for section in contact_sections:
            emails = re.findall(email_pattern, section.get_text())
            if emails:
                return emails[0]
        
        logger.warning("Email not found")
        return "Not found"

    def _extract_services(self, soup: BeautifulSoup) -> str:
        services = []
        
        selectors = [
            '.clinic-2020-services .featured-posts article',
            '.services article', '.services-list li',
            '[class*="service"] article', '[class*="service"] li'
        ]
        
        for selector in selectors:
            articles = soup.select(selector)
            
            for article in articles:
                h3 = article.find(['h3', 'h2', 'h4'])
                if h3:
                    service_name = h3.get_text(strip=True)
                    if service_name and service_name not in services:
                        services.append(service_name)
            
            if services:
                break
        
        return '; '.join(services) if services else "Not found"

    def scrape_all_clinics(self, filename: Optional[str] = None) -> int:
        filename = filename or self.config.output_file
        
        if Path(filename).exists():
            logger.warning(f"Overwriting existing file: {filename}")
        
        regions = self.extract_regions()
        if not regions:
            logger.error("No regions found")
            return 0
        
        total_scraped = 0
        fieldnames = ['Region', 'Clinic_Name', 'Address', 'Phone', 'Email', 'Services']
        
        csvfile = open(filename, 'w', newline='', encoding='utf-8')
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        try:
            for region in regions:
                logger.info(f"Processing region: {region['name']}")
                self.delay()
                
                clinics = self.extract_clinics_from_region(region['url'])
                
                for clinic in clinics:
                    logger.info(f"  Scraping: {clinic['name']}")
                    self.delay()
                    
                    details = self.extract_clinic_details(clinic['url'])
                    
                    if details:
                        details.region = region['name']
                        writer.writerow(details.to_dict())
                        total_scraped += 1
                        logger.info(f"    ✓ {details.name}")
                    else:
                        logger.warning(f"    ✗ Failed: {clinic['name']}")
        
        finally:
            csvfile.close()
        
        logger.info(f"Completed: {total_scraped} clinics saved to {filename}")
        return total_scraped


if __name__ == "__main__":
    with MyFootDrScraper() as scraper:
        scraper.scrape_all_clinics()