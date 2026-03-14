import csv
import io

def parse_csv_upload(file_content: bytes):
    """
    Parse uploaded CSV file for financial data import
    """
    decoded = file_content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    records = [row for row in reader]
    return records
