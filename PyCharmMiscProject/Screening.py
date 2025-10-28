import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

class Form4SubmissionsScreener:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Form4ScreenerApp aarya.patel.email@gmail.com'
        })

    def fetch_form4_document(self, url: str) -> Optional[str]:
        """Fetch Form 4 XML directly from a given URL."""
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            if "<html" not in resp.text.lower():
                print(f"✅ Successfully fetched XML: {url}")
                return resp.text
            else:
                print(f"❌ HTML page found instead of XML: {url}")
        except requests.RequestException as e:
            print(f"❌ Error fetching XML from {url}: {e}")
        return None

    def parse_form4_xml(self, xml_content: str) -> List[Dict[str, any]]:
        """Parse Form 4 XML, extracting basic non-derivative transactions."""
        transactions = []
        try:
            root = ET.fromstring(xml_content.strip())
            ns_url = root.tag[root.tag.find("{") + 1:root.tag.find("}")] if "}" in root.tag else ""
            NS = {'ns': ns_url} if ns_url else {}
            prefix = 'ns:' if ns_url else ''

            def find_text(element, path):
                if element is None:
                    return None
                return element.findtext('/'.join(f"{prefix}{p}" for p in path.split('/')), None, NS)

            # Extract reporting owner info
            owners = []
            for owner in root.findall(f'.//{prefix}reportingOwner', NS):
                owner_id = owner.find(f'{prefix}reportingOwnerId', NS)
                owner_name = find_text(owner_id, 'rptOwnerName') or find_text(owner_id, 'ownerName') or 'Unknown'
                relationship = owner.find(f'{prefix}reportingOwnerRelationship', NS)
                officer_title = find_text(relationship, 'officerTitle') or ''
                owners.append({'officer_name': owner_name, 'officer_title': officer_title})

            # Extract non-derivative transactions
            for tx in root.findall(f'.//{prefix}nonDerivativeTransaction', NS):
                tx_code = find_text(tx, 'transactionCoding/transactionCode/value')
                tx_date = find_text(tx, 'transactionDate/value')
                shares = find_text(tx, 'transactionAmounts/transactionShares/value')
                price = find_text(tx, 'transactionAmounts/transactionPricePerShare/value')
                security_title = find_text(tx, 'securityTitle/value')
                for owner in owners:
                    transactions.append({
                        **owner,
                        'transaction_code': tx_code,
                        'transaction_date': tx_date,
                        'shares': shares,
                        'price_per_share': price,
                        'security_title': security_title
                    })

        except ET.ParseError as e:
            print(f"❌ XML parsing error: {e}")

        return transactions

# --- Execution block ---

if __name__ == "__main__":
    screener = Form4SubmissionsScreener()

    # Direct URLs for testing
    test_urls = [
        "https://www.sec.gov/Archives/edgar/data/1045810/000119764925000046/wk-form4_1760134873.xml",
        "https://www.sec.gov/Archives/edgar/data/1045810/000119764925000044/wk-form4_1759876116.xml",
        "https://www.sec.gov/Archives/edgar/data/1045810/000119764925000042/wk-form4_1759441403.xml",
        "https://www.sec.gov/Archives/edgar/data/1045810/000119764925000038/wk-form4_1758752181.xml",
        "https://www.sec.gov/Archives/edgar/data/1045810/000163666525000006/wk-form4_1758662649.xml",
        "https://www.sec.gov/Archives/edgar/data/1045810/000119903925000010/wk-form4_1758662353.xml"
    ]

    all_transactions = []
    for url in test_urls:
        xml_content = screener.fetch_form4_document(url)
        if xml_content:
            transactions = screener.parse_form4_xml(xml_content)
            all_transactions.extend(transactions)

    print(f"\nTotal transactions found: {len(all_transactions)}")
    for i, tx in enumerate(all_transactions, 1):
        print(f"{i}. Officer: {tx['officer_name']} | Title: {tx['officer_title']} | "
              f"Code: {tx['transaction_code']} | Date: {tx['transaction_date']} | "
              f"Shares: {tx['shares']} | Price: {tx['price_per_share']} | Security: {tx['security_title']}")
