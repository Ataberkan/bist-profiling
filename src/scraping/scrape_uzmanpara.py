import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import re
import argparse

# Set to True to enable debug mode
DEBUG = True

def get_date_range_backwards(start_date, days=7):
    """Creates a list of business days going backwards from the specified date."""
    date_list = []
    
    # Starting date
    current_date = start_date
    
    # Go backwards and collect business days
    days_count = 0
    while days_count < days:
        # Exclude weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5:
            date_list.append(current_date)
            days_count += 1
        
        # Go back one day
        current_date = current_date - timedelta(days=1)
    
    return date_list

def turkce_temizle(metin):
    """Replaces Turkish characters in text with English characters"""
    if not isinstance(metin, str):
        return metin
    
    degisimler = {
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
        'İ': 'I', 'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C'
    }
    
    for tr, eng in degisimler.items():
        metin = metin.replace(tr, eng)
    
    return metin

def baslik_duzenle(baslik):
    """Converts header text to a standardized format"""
    # Clean Turkish characters
    baslik = turkce_temizle(baslik)
    
    # Basic cleaning before matching
    # Replace spaces and other characters with underscores
    temiz_baslik = re.sub(r'[^a-zA-Z0-9]', '_', baslik).strip('_')
    temiz_baslik = re.sub(r'_+', '_', temiz_baslik)
    
    # Known header mappings - covers headers that may be in multiple formats
    baslik_map = {
        # Original headers
        "Menkul Ad": "Stock_Code",
        "Menkul_Ad": "Stock_Code",
        "Son": "Last_Price",
        "Dun": "Previous_Price",
        "D_n": "Previous_Price",
        "Deger": "Change_Percent",
        "Yuksek": "High",
        "Y_ksek": "High",
        "Dusuk": "Low",
        "D_k": "Low",
        "A_Ort": "Weighted_Average",
        "Agirlikli_Ortalama": "Weighted_Average",
        "Hacim_LOT": "Volume_Lot",
        "Hacim_Lot": "Volume_Lot",
        "Hacim_Bin_TL": "Volume_TL",
        "HacimBin_TL": "Volume_TL",
        
        # Content-based matching
        "Menkul": "Stock_Code",
        "Kod": "Stock_Code",
        "Fiyat": "Last_Price",
        "Onceki": "Previous_Price",
        "Degisim": "Change_Percent",
        "Yuzde": "Change_Percent",
        "En_Yuksek": "High",
        "Max": "High",
        "En_Dusuk": "Low",
        "Min": "Low",
        "Agirlikli": "Weighted_Average",
        "Ortalama": "Weighted_Average",
        "Lot": "Volume_Lot",
        "Hacim_TL": "Volume_TL",
        "Bin_TL": "Volume_TL",
    }
    
    # Simple matching check
    if baslik in baslik_map:
        return baslik_map[baslik]
    
    if temiz_baslik in baslik_map:
        return baslik_map[temiz_baslik]
    
    # Content-based matching
    for anahtar, deger in baslik_map.items():
        if anahtar.lower() in baslik.lower() or anahtar.lower() in temiz_baslik.lower():
            return deger
    
    # Special case: Headers containing percentage sign are probably change ratios
    if "%" in baslik:
        return "Change_Percent"
    
    # Default values
    if baslik.lower().startswith("men") or baslik.lower().startswith("kod"):
        return "Stock_Code"
    elif baslik.lower().startswith("son") or baslik.lower().startswith("fiy"):
        return "Last_Price"
    elif baslik.lower().startswith("dun") or baslik.lower().startswith("onc"):
        return "Previous_Price"
    elif baslik.lower().startswith("deg") or baslik.lower().startswith("yuz"):
        return "Change_Percent"
    elif baslik.lower().startswith("yuk") or baslik.lower().startswith("max"):
        return "High"
    elif baslik.lower().startswith("dus") or baslik.lower().startswith("min"):
        return "Low"
    elif baslik.lower().startswith("ort") or baslik.lower().startswith("agi"):
        return "Weighted_Average"
    elif baslik.lower().startswith("hac") and ("lot" in baslik.lower() or "adet" in baslik.lower()):
        return "Volume_Lot"
    elif baslik.lower().startswith("hac") and ("tl" in baslik.lower()):
        return "Volume_TL"
    
    # If still no match, use cleaned version
    return temiz_baslik if temiz_baslik else "Value"

def extract_bist30_stocks(all_data, stock_symbols):
    """Extracts BIST 30 stocks from all data."""
    
    if all_data.empty:
        return all_data
        
    # Search for each BIST 30 stock across all columns
    result_df = pd.DataFrame()
    
    # First column is probably the stock code column
    stock_column = all_data.columns[0]
    
    # Filter BIST 30 stocks
    for stock in stock_symbols:
        # Exact match or containment check
        try:
            matches = all_data[all_data[stock_column].str.contains(f"^{stock}($|[\s\.])", case=False, regex=True, na=False)]
            if not matches.empty:
                result_df = pd.concat([result_df, matches])
        except Exception as e:
            print(f"Stock filtering error ({stock}): {e}")
    
    # Remove duplicates
    if not result_df.empty:
        result_df = result_df.drop_duplicates()
    
    # If still nothing found, data format is probably different
    if result_df.empty:
        print("BIST 30 stocks could not be detected, trying a different approach...")
        # Find probable stock code column
        for col in all_data.columns:
            for stock in stock_symbols:
                try:
                    # Exact match or containment check
                    matches = all_data[all_data[col].str.contains(f"^{stock}($|[\s\.])", case=False, regex=True, na=False)]
                    if not matches.empty:
                        result_df = pd.concat([result_df, matches])
                except Exception as e:
                    continue
        
        # Remove duplicates
        if not result_df.empty:
            result_df = result_df.drop_duplicates()
    
    return result_df

def get_fundamental_data(stock_code):
    """Retrieves fundamental analysis data for a specific stock from uzmanpara.milliyet.com.tr site."""
    
    # Stock detail URL
    url = f"https://uzmanpara.milliyet.com.tr/canli-borsa/hisse-detay-bilgileri/{stock_code}/"
    
    print(f"Retrieving fundamental analysis data: {url}")
    
    try:
        # Send request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: Stock detail page retrieval error. Status: {response.status_code}")
            return {}
            
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find fundamental data table
        fundamental_data = {}
        
        # Find all tables
        tables = soup.find_all('table')
        
        if not tables:
            print(f"Warning: No table found for {stock_code}.")
            return {}
        
        # Examine all tables
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                # Each row has two cells: label and value
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # Get label and value
                    label = cells[0].text.strip()
                    value = cells[1].text.strip()
                    
                    # Clean Turkish characters
                    label = turkce_temizle(label)
                    
                    # Handle special cases
                    if "Beta" in label:
                        fundamental_data["Beta"] = value
                    elif "Halka" in label and "Aciklik" in label:
                        fundamental_data["Halka_Aciklik"] = value.replace("%", "").strip()
                    elif "BIST" in label and "Agirlik" in label:
                        fundamental_data["BIST_Agirlik"] = value.replace("%", "").strip()
                    elif "F/K" in label or "FK" in label:
                        fundamental_data["FK_Orani"] = value
                    elif "Piyasa Deg" in label and "Defter Deg" in label:
                        fundamental_data["PD_DD"] = value
                    elif "Dibe Uzaklik" in label:
                        fundamental_data["Dibe_Uzaklik"] = value.replace("%", "").strip()
                    elif "Piyasa Degeri" in label and "(USD)" in label:
                        fundamental_data["Piyasa_Degeri_USD"] = value
                    elif "Piyasa Degeri" in label and "(TL)" in label:
                        fundamental_data["Piyasa_Degeri_TL"] = value
                    elif "Ozsermaye" in label:
                        fundamental_data["Ozsermaye_TL"] = value
                    elif "Sermaye" in label:
                        fundamental_data["Sermaye_TL"] = value
                    elif "Net Kar" in label:
                        fundamental_data["Net_Kar_TL"] = value
        
        return fundamental_data
        
    except Exception as e:
        print(f"Fundamental data retrieval error: {e}")
        return {}

def scrape_stock_data_and_fundamentals(date, stock_list=None, max_pages=13):
    """Retrieves price data and fundamental analysis data for a specific date from uzmanpara.milliyet.com.tr site."""
    
    # Format date (Day, Month, Year)
    day = date.day
    month = date.month
    year = date.year
    
    all_data = []
    fundamental_data = []
    found_stocks = set()
    stock_codes = set(stock_list) if stock_list else set()
    
    # 1. Retrieve price data for specific date
    print(f"\n--- Retrieving Price Data for {date.strftime('%d.%m.%Y')} ---")
    
    # Loop for specified number of pages
    for page_num in range(1, max_pages + 1):
        # Page URL
        url = f"https://uzmanpara.milliyet.com.tr/borsa/gecmis-kapanislar/?Pagenum={page_num}&tip=Hisse&gun={day}&ay={month}&yil={year}&Harf=-1"
        
        print(f"Retrieving page {page_num} data: {url}")
        
        try:
            # Send request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            
            if DEBUG:
                print(f"URL response code: {response.status_code}")
            
            # If we get 500 error, break the loop for other pages
            if response.status_code == 500:
                print(f"Server error: Page {page_num}. Skipping other pages.")
                break
                
            response.raise_for_status()  # For other HTTP errors
                
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find table - get the first table in the page
            table = soup.find('table')
            
            if not table:
                print(f"Warning: No table found on page {page_num}. Might be the last page.")
                break
            
            # Find table headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all('th'):
                    text = th.text.strip()
                    # Clean header text
                    headers.append(baslik_duzenle(text))
            
            if not headers:
                # If no headers, create default headers
                headers = ["Stock_Code", "Last_Price", "Previous_Price", "Change_Percent", "High", "Low", "Weighted_Average", "Volume_Lot", "Volume_TL"]
            else:
                # Standardize headers and prevent duplicates
                # If same header exists multiple times, number them
                header_counts = {}
                standardized_headers = []
                
                for h in headers:
                    if h in header_counts:
                        header_counts[h] += 1
                        standardized_headers.append(f"{h}_{header_counts[h]}")
                    else:
                        header_counts[h] = 1
                        standardized_headers.append(h)
                
                headers = standardized_headers
            
            if DEBUG:
                print(f"Table headers: {headers}")
            
            # Get table rows
            rows = table.find_all('tr')[1:]  # First row is header
            
            if not rows:
                print(f"Warning: No data rows found on page {page_num}.")
                break
            
            # Extract data from each row
            for row in rows:
                cols = row.find_all('td')
                if cols:
                    row_data = []
                    stock_code = None
                    
                    for i, col in enumerate(cols):
                        # Get text from link (stock name is usually inside a link)
                        link = col.find('a')
                        if link:
                            value = link.text.strip()
                        else:
                            value = col.text.strip()
                        
                        # First column might be stock code, save it
                        if i == 0:
                            stock_code = value
                        
                        # Clean Turkish characters
                        value = turkce_temizle(value)
                        
                        # Fix numerical values
                        value = value.replace('.', '').replace(',', '.')
                        row_data.append(value)
                    
                    # If all data is retrieved, add to list
                    if len(row_data) > 0:
                        all_data.append(row_data)
                        
                        # Save stock code (for fundamental data)
                        if stock_code:
                            for code in stock_list:
                                if code in stock_code:
                                    found_stocks.add(code)
                                    break
            
            if DEBUG:
                print(f"Collected {len(rows)} rows from page {page_num}.")
            
            # Short wait before moving to next page
            time.sleep(1)
            
        except requests.RequestException as e:
            print(f"Error: Page {page_num} could not be retrieved: {e}")
            if page_num > 1:  # If error on first page, cancel entire operation; otherwise continue
                break
        except Exception as e:
            print(f"Unexpected error: Page {page_num} - {e}")
            if page_num > 1:  # If error on first page, cancel entire operation; otherwise continue
                break
    
    # 2. Retrieve fundamental data for BIST 30 stocks - COMMENTED OUT
    """
    print("\n--- Retrieving Fundamental Analysis Data ---")
    
    # Found stocks + stocks in stock list
    stocks_to_process = found_stocks.union(stock_codes)
    
    if not stocks_to_process:
        print("No stock code found. Fundamental data could not be retrieved.")
    else:
        for stock in stocks_to_process:
            print(f"Retrieving fundamental data: {stock}")
            fund_data = get_fundamental_data(stock)
            
            if fund_data:
                # Add stock code and date
                fund_data["Stock_Code"] = stock
                fund_data["Date"] = date.strftime('%Y-%m-%d')
                fundamental_data.append(fund_data)
                print(f"✅ {stock} fundamental data successfully retrieved.")
            else:
                print(f"❌ {stock} fundamental data could not be retrieved.")
            
            # Wait time to avoid overloading the server
            time.sleep(1)
    """
    
    # Convert price data to DataFrame
    price_df = None
    if all_data:
        try:
            # Create DataFrame
            price_df = pd.DataFrame(all_data)
            
            # Check column count
            if len(price_df.columns) != len(headers):
                print(f"Warning: Column count ({len(price_df.columns)}) and header count ({len(headers)}) do not match.")
                # Match header count to data column count
                if len(headers) < len(price_df.columns):
                    headers = headers + [f"Column{i+1}" for i in range(len(headers), len(price_df.columns))]
                else:
                    headers = headers[:len(price_df.columns)]
            
            # Assign column names
            price_df.columns = headers
            
            # Filter BIST 30 stocks
            if stock_list:
                price_df = extract_bist30_stocks(price_df, stock_list)
            
            # Add date column
            price_df['Date'] = date.strftime('%Y-%m-%d')
            
        except Exception as e:
            print(f"Error creating price DataFrame: {e}")
            price_df = None
    
    # Convert fundamental data to DataFrame
    fund_df = None
    """
    if fundamental_data:
        try:
            fund_df = pd.DataFrame(fundamental_data)
        except Exception as e:
            print(f"Error creating fundamental data DataFrame: {e}")
            fund_df = None
    """
    
    return price_df, fund_df, found_stocks

def main(output_file="uzmanpara_stock_data.csv", stock_list=None, days=7, separate_days=False):
    """
    Main function: retrieves data for specified number of days and saves to CSV file.
    
    Parameters:
    -----------
    output_file : str
        Output file name
    stock_list : list
        List of stock codes to retrieve
    days : int
        How many days of data to retrieve
    separate_days : bool
        Option to save data to separate files by day
    """
    
    # Check data folder and create if necessary
    # data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    # Point to src/data folder
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Create folder for daily files
    daily_data_dir = os.path.join(data_dir, "daily")
    if separate_days and not os.path.exists(daily_data_dir):
        os.makedirs(daily_data_dir)
    
    # Main output file
    price_output_path = os.path.join(data_dir, "price_" + output_file)
    
    # BIST 30 stocks (default)
    if stock_list is None:
        stock_list = [
            "AEFES", "AKBNK", "ASELS", "ASTOR", "BIMAS", "CIMSA", "EKGYO", "ENKAI", 
            "EREGL", "FROTO", "GARAN", "HEKTS", "ISCTR", "KCHOL", "KOZAL", "KRDMD", 
            "MGROS", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", 
            "THYAO", "TOASO", "TTKOM", "TUPRS", "ULKER", "YKBNK"
        ]
    
    # Use computer's current date
    start_date = datetime.now()
    date_list = get_date_range_backwards(start_date, days=days)
    
    print(f"Data will be retrieved for a total of {len(date_list)} dates.")
    print(f"First date: {date_list[0].strftime('%d.%m.%Y')}")
    print(f"Last date: {date_list[-1].strftime('%d.%m.%Y')}")
    
    all_price_data = []
    all_fundamental_data = []
    success_count = 0
    found_stocks = set()
    
    for date in date_list:
        price_df, fund_df, stocks_found = scrape_stock_data_and_fundamentals(date, stock_list)
        
        if price_df is not None and not price_df.empty:
            all_price_data.append(price_df)
            success_count += 1
            found_stocks.update(stocks_found)
            
            print(f"✅ Price data for {date.strftime('%d.%m.%Y')} successfully retrieved. ({success_count}/{len(date_list)})")
            print(f"   Number of stocks found: {len(price_df)}, Unique stock count: {len(set(price_df[price_df.columns[0]].unique()))}")
            
            # If separate daily files are requested, save each day's data separately
            if separate_days:
                date_str = date.strftime('%Y%m%d')
                daily_filename = f"bist30_data_{date_str}.csv"
                daily_output_path = os.path.join(daily_data_dir, daily_filename)
                price_df.to_csv(daily_output_path, index=False, encoding='utf-8')
                print(f"   Daily data file saved: {daily_filename}")
        else:
            print(f"❌ No price data found for {date.strftime('%d.%m.%Y')}.")
        
        # Wait time to avoid overloading the server
        time.sleep(2)
    
    # Save price data
    if all_price_data:
        # Combine all data
        final_price_df = pd.concat(all_price_data, ignore_index=True)
        
        # Convert date column to date format
        final_price_df['Date'] = pd.to_datetime(final_price_df['Date'])
        
        # Save data
        final_price_df.to_csv(price_output_path, index=False, encoding='utf-8')
        print(f"\nTotal of {len(final_price_df)} rows of price data for {success_count} days successfully saved to '{price_output_path}'.")
        print(f"Unique stock count found: {len(found_stocks)}/{len(stock_list)}")
        
        missing_stocks = set(stock_list) - found_stocks
        if missing_stocks:
            print(f"Stocks not found: {sorted(list(missing_stocks))}")
        
        # Also copy to standard file name (for use by other modules)
        standard_output_path = os.path.join(data_dir, "price_bist30_historical_data_13052025_7days.csv")
        final_price_df.to_csv(standard_output_path, index=False, encoding='utf-8')
        print(f"Data also saved to standard file name: {standard_output_path}")
    else:
        print("No price data could be retrieved!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieves BIST stock data from Uzmanpara Milliyet")
    parser.add_argument("--days", type=int, default=7, help="How many days of data to retrieve (default: 7)")
    parser.add_argument("--output", type=str, default="bist30_historical_data.csv", help="Output file name")
    parser.add_argument("--separate-days", action="store_true", help="Save data to separate files by day")
    parser.add_argument("--stocks", nargs="+", help="Stock codes to retrieve (if left empty, BIST 30 stocks will be used)")
    
    args = parser.parse_args()
    
    # Output file name
    output_filename = args.output
    
    # Use your list in the order you provided (important)
    stocks_to_fetch = args.stocks
    
    main(output_filename, stocks_to_fetch, days=args.days, separate_days=args.separate_days) 