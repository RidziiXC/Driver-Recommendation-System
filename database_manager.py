import sqlite3
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import os

class DatabaseManager:
    def __init__(self, db_path="driver_data.db"):
        """
        Database Manager for Driver Recommendation System
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trips table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                province TEXT,
                driver TEXT NOT NULL,
                representative TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create drivers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drivers (
                driver_name TEXT PRIMARY KEY,
                total_trips INTEGER DEFAULT 0,
                unique_locations INTEGER DEFAULT 0,
                provinces_covered INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Database initialized: {self.db_path}")
    
    def load_from_google_sheets(self, spreadsheet_url, credentials_path=None, sheet_name="datatrip"):
        """Load data from Google Sheets and save to database"""
        try:
            # Extract spreadsheet ID and gid
            sheet_id = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url).group(1)
            
            # Extract gid if present in URL
            gid_match = re.search(r'[#&]gid=([0-9]+)', spreadsheet_url)
            gid = gid_match.group(1) if gid_match else "0"
            
            print(f"🔍 Trying to access sheet: {sheet_id}, gid: {gid}")
            
            if credentials_path and os.path.exists(credentials_path):
                # Use service account
                scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
                data = sheet.get_all_records()
                df = pd.DataFrame(data)
            else:
                # Try public access with multiple methods
                success = False
                
                # Method 1: Try with extracted gid
                try:
                    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                    print(f"🔗 Trying URL: {csv_url}")
                    df = pd.read_csv(csv_url, encoding='utf-8')
                    print(f"✅ Successfully loaded with gid {gid}")
                    success = True
                except Exception as e1:
                    print(f"⚠️ Failed with gid {gid}: {e1}")
                    
                    # Method 2: Try with gid=0
                    try:
                        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                        print(f"🔗 Trying URL: {csv_url}")
                        df = pd.read_csv(csv_url, encoding='utf-8')
                        print("✅ Successfully loaded with gid 0")
                        success = True
                    except Exception as e2:
                        print(f"⚠️ Failed with gid 0: {e2}")
                        
                        # Method 3: Try different encoding
                        try:
                            df = pd.read_csv(csv_url, encoding='latin1')
                            print("✅ Successfully loaded with latin1 encoding")
                            success = True
                        except Exception as e3:
                            print(f"⚠️ Failed with latin1: {e3}")
                
                if not success:
                    print("❌ All methods failed, cannot proceed without real data")
                    return False
            
            # Validate data
            if df.empty:
                print("❌ Empty dataframe, cannot proceed")
                return False
                
            if len(df.columns) < 3:
                print("❌ Invalid data format (too few columns), cannot proceed")
                return False
            
            # Check if we have expected columns
            expected_cols = ['สถานที่ส่ง', 'จังหวัด', 'Driver', 'ผู้แทน']
            if not any(col in df.columns for col in expected_cols):
                print("❌ Expected columns not found, cannot proceed")
                print(f"Available columns: {list(df.columns)}")
                return False
            
            # Save to database
            self.save_trips_data(df)
            print(f"✅ Loaded {len(df)} records from Google Sheets")
            return True
            
        except Exception as e:
            print(f"❌ Error loading from Google Sheets: {e}")
            return False
    
    def save_trips_data(self, df):
        """Save trips data to database"""
        conn = sqlite3.connect(self.db_path)
        
        # Clear existing data
        conn.execute("DELETE FROM trips")
        
        # Insert new data
        for _, row in df.iterrows():
            if pd.notna(row.get('สถานที่ส่ง')) and pd.notna(row.get('Driver')):
                drivers = str(row.get('Driver', '')).split('+')
                for driver in drivers:
                    driver = driver.strip()
                    if driver and driver != 'ยกเลิก' and driver != 'nan':
                        conn.execute('''
                            INSERT INTO trips (location, province, driver, representative)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            row.get('สถานที่ส่ง', ''),
                            row.get('จังหวัด', ''),
                            driver,
                            row.get('ผู้แทน', '')
                        ))
        
        conn.commit()
        conn.close()
        self._update_driver_stats()
        print("✅ Data saved to database")
    
    def _update_driver_stats(self):
        """Update driver statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing driver stats
        cursor.execute("DELETE FROM drivers")
        
        # Calculate and insert new stats
        cursor.execute('''
            INSERT INTO drivers (driver_name, total_trips, unique_locations, provinces_covered)
            SELECT 
                driver,
                COUNT(*) as total_trips,
                COUNT(DISTINCT location) as unique_locations,
                COUNT(DISTINCT province) as provinces_covered
            FROM trips 
            WHERE driver != 'ยกเลิก'
            GROUP BY driver
        ''')
        
        conn.commit()
        conn.close()
    
    def get_all_trips(self):
        """Get all trips from database"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        conn.close()
        return df
    
    def get_locations_list(self):
        """Get list of all unique locations with their provinces"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT location, province 
            FROM trips 
            WHERE location IS NOT NULL AND location != ''
            ORDER BY location
        ''')
        
        locations = cursor.fetchall()
        conn.close()
        
        # Return as dict for easy lookup
        location_dict = {}
        for location, province in locations:
            location_dict[location] = province if province else ""
        
        return location_dict

    def get_driver_stats(self):
        """Get driver statistics"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM drivers ORDER BY total_trips DESC", conn)
        conn.close()
        return df