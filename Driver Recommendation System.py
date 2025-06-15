import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict, Counter
import re

class DriverRecommendationSystem:
    def __init__(self, credentials_path=None):
        """
        Initialize Driver Recommendation System
        
        Args:
            credentials_path: Path to Google Service Account JSON file
        """
        self.credentials_path = credentials_path
        self.raw_data = None
        self.experience_matrix = defaultdict(lambda: defaultdict(int))
        self.province_experience = defaultdict(lambda: defaultdict(int))
        self.hospital_types = defaultdict(set)
        self.drivers_stats = defaultdict(dict)
        
    def load_data_from_sheets(self, spreadsheet_url, sheet_name="datatrip"):
        """
        Load data from Google Sheets
        
        Args:
            spreadsheet_url: URL of Google Sheets
            sheet_name: Name of the sheet to read
        """
        try:
            # Extract spreadsheet ID from URL
            sheet_id = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url).group(1)
            
            if self.credentials_path:
                # Use service account credentials
                scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_file(self.credentials_path, scopes=scope)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
                data = sheet.get_all_records()
                self.raw_data = pd.DataFrame(data)
            else:
                # Use public access (if available)
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                self.raw_data = pd.read_csv(csv_url)
                
            print(f"✅ โหลดข้อมูลสำเร็จ: {len(self.raw_data)} รายการ")
            return True
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
            return False
    
    def load_sample_data(self):
        """Load sample data for testing without Google Sheets access"""
        sample_data = [
            {"สถานที่ส่ง": "โรงพยาบาลระยอง", "จังหวัด": "ระยอง", "Driver": "อนุชา", "ผู้แทน": "พงศกร"},
            {"สถานที่ส่ง": "โรงพยาบาลระยอง", "จังหวัด": "ระยอง", "Driver": "อนุชา", "ผู้แทน": "พงศกร"},
            {"สถานที่ส่ง": "โรงพยาบาลสมเด็จพระบรมราชเทวี ณ ศรีราชา", "จังหวัด": "ชลบุรี", "Driver": "อนุชา", "ผู้แทน": "พงศกร"},
            {"สถานที่ส่ง": "โรงพยาบาลแม่สาย", "จังหวัด": "เชียงราย", "Driver": "ไพบูรณ์", "ผู้แทน": "เพิ่มศักดิ์"},
            {"สถานที่ส่ง": "โรงพยาบาลแม่สาย", "จังหวัด": "เชียงราย", "Driver": "ไพบูรณ์", "ผู้แทน": "เพิ่มศักดิ์"},
            {"สถานที่ส่ง": "โรงพยาบาลศรีสะเกษ", "จังหวัด": "ศรีสะเกษ", "Driver": "ไพบูรณ์+อนุวัตน์+อาลี", "ผู้แทน": "ปรีชา"},
            {"สถานที่ส่ง": "โรงพยาบาลศิริราช", "จังหวัด": "กรุงเทพมหานคร", "Driver": "สมเกียรติ", "ผู้แทน": "เจนจิรา"},
            {"สถานที่ส่ง": "โรงพยาบาลศิริราช", "จังหวัด": "กรุงเทพมหานคร", "Driver": "ศักดิ์สิทธิ์", "ผู้แทน": "เจนจิรา"},
            {"สถานที่ส่ง": "โรงพยาบาลกรุงเทพคริสเตียน", "จังหวัด": "กรุงเทพมหานคร", "Driver": "สยุมภู", "ผู้แทน": "ภัทรอร"},
            {"สถานที่ส่ง": "โรงพยาบาลกรุงเทพคริสเตียน", "จังหวัด": "กรุงเทพมหานคร", "Driver": "อนุสิทธิ์+ศักดิ์สิทธิ์+มังกร", "ผู้แทน": "ภัทรอร"},
        ]
        self.raw_data = pd.DataFrame(sample_data)
        print(f"✅ โหลดข้อมูลตัวอย่าง: {len(self.raw_data)} รายการ")
        
    def build_experience_matrix(self):
        """Build experience matrix for drivers"""
        if self.raw_data is None:
            print("❌ ไม่มีข้อมูล กรุณาโหลดข้อมูลก่อน")
            return
            
        # Clean data
        df = self.raw_data.copy()
        df = df.dropna(subset=['สถานที่ส่ง', 'Driver'])
        df = df[df['Driver'] != 'ยกเลิก']  # Remove cancelled entries
        
        for _, row in df.iterrows():
            location = row['สถานที่ส่ง']
            province = row['จังหวัด']
            drivers = str(row['Driver']).split('+')  # Handle multiple drivers
            
            for driver in drivers:
                driver = driver.strip()
                if driver and driver != 'nan':
                    # Count exact location experience
                    self.experience_matrix[driver][location] += 1
                    
                    # Count province experience
                    if pd.notna(province):
                        self.province_experience[driver][province] += 1
                    
                    # Categorize hospital types
                    self.hospital_types[driver].add(self._categorize_hospital(location))
        
        # Calculate driver statistics
        self._calculate_driver_stats()
        print("✅ สร้างเมทริกซ์ประสบการณ์เสร็จสิ้น")
        
    def _categorize_hospital(self, location):
        """Categorize hospital type based on name"""
        location = str(location).lower()
        if 'กรุงเทพ' in location or 'bangkok' in location:
            return 'เอกชน-ใหญ่'
        elif 'รามาธิบดี' in location or 'ศิริราช' in location or 'จุฬาลงกรณ์' in location:
            return 'รัฐ-มหาวิทยาลัย'
        elif 'โรงพยาบาล' in location:
            return 'รัฐ-ทั่วไป'
        else:
            return 'อื่นๆ'
            
    def _calculate_driver_stats(self):
        """Calculate statistics for each driver"""
        for driver in self.experience_matrix.keys():
            total_trips = sum(self.experience_matrix[driver].values())
            unique_locations = len(self.experience_matrix[driver])
            provinces = len(self.province_experience[driver])
            
            self.drivers_stats[driver] = {
                'total_trips': total_trips,
                'unique_locations': unique_locations,
                'provinces_covered': provinces,
                'avg_trips_per_location': total_trips / unique_locations if unique_locations > 0 else 0,
                'hospital_types': list(self.hospital_types[driver])
            }
    
    def calculate_compatibility_score(self, destination, destination_province=None):
        """
        Calculate compatibility score for each driver
        
        Args:
            destination: Target destination
            destination_province: Province of destination
            
        Returns:
            dict: Driver scores with explanations
        """
        scores = {}
        
        for driver in self.experience_matrix.keys():
            score = 0
            explanations = []
            
            # 1. Direct experience (40 points)
            direct_exp = self.experience_matrix[driver].get(destination, 0)
            if direct_exp > 0:
                score += min(direct_exp * 10, 40)  # Max 40 points
                explanations.append(f"เคยไป {destination} จำนวน {direct_exp} ครั้ง")
            
            # 2. Province experience (30 points)
            if destination_province:
                province_exp = self.province_experience[driver].get(destination_province, 0)
                if province_exp > 0:
                    score += min(province_exp * 3, 30)  # Max 30 points
                    explanations.append(f"มีประสบการณ์ในจังหวัด {destination_province} จำนวน {province_exp} ครั้ง")
            
            # 3. Similar locations (20 points)
            similar_locations = self._find_similar_locations(destination, driver)
            if similar_locations:
                score += min(len(similar_locations) * 5, 20)  # Max 20 points
                explanations.append(f"เคยไปสถานที่คล้ายกัน: {', '.join(similar_locations[:3])}")
            
            # 4. Overall experience (10 points)
            total_exp = self.drivers_stats[driver]['total_trips']
            if total_exp > 0:
                score += min(total_exp * 0.5, 10)  # Max 10 points
                explanations.append(f"ประสบการณ์รวม {total_exp} เที่ยว")
            
            scores[driver] = {
                'score': round(score, 2),
                'explanations': explanations,
                'stats': self.drivers_stats[driver]
            }
        
        return scores
    
    def _find_similar_locations(self, destination, driver):
        """Find similar locations that driver has been to"""
        similar = []
        destination_words = set(destination.lower().split())
        
        for location in self.experience_matrix[driver].keys():
            location_words = set(location.lower().split())
            # Find common words (excluding common words)
            common_words = destination_words.intersection(location_words)
            common_words.discard('โรงพยาบาล')
            common_words.discard('ที่')
            
            if len(common_words) > 0:
                similar.append(location)
                
        return similar[:5]  # Return top 5 similar locations
    
    def get_top_10_drivers(self, destination, destination_province=None, waypoints=None):
        """
        Get top 10 recommended drivers for destination
        
        Args:
            destination: Target destination
            destination_province: Province of destination
            waypoints: List of waypoints (for future use)
            
        Returns:
            list: Top 10 drivers with scores and explanations
        """
        if not self.experience_matrix:
            print("❌ ยังไม่ได้สร้างเมทริกซ์ประสบการณ์ กรุณาเรียก build_experience_matrix() ก่อน")
            return []
        
        scores = self.calculate_compatibility_score(destination, destination_province)
        
        # Sort by score
        sorted_drivers = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Return top 10
        top_10 = []
        for i, (driver, data) in enumerate(sorted_drivers[:10], 1):
            top_10.append({
                'rank': i,
                'driver': driver,
                'score': data['score'],
                'explanations': data['explanations'],
                'stats': data['stats']
            })
        
        return top_10
    
    def print_recommendations(self, destination, destination_province=None):
        """Print formatted recommendations"""
        print(f"\n🎯 แนะนำพนักงานขับรถสำหรับ: {destination}")
        if destination_province:
            print(f"📍 จังหวัด: {destination_province}")
        print("=" * 80)
        
        recommendations = self.get_top_10_drivers(destination, destination_province)
        
        if not recommendations:
            print("❌ ไม่พบข้อมูลแนะนำ")
            return
        
        for rec in recommendations:
            print(f"\n🏆 อันดับ {rec['rank']}: {rec['driver']}")
            print(f"📊 คะแนน: {rec['score']}/100")
            print("💡 เหตุผล:")
            for explanation in rec['explanations']:
                print(f"   • {explanation}")
            
            stats = rec['stats']
            print(f"📈 สถิติ: {stats['total_trips']} เที่ยว | "
                  f"{stats['unique_locations']} สถานที่ | "
                  f"{stats['provinces_covered']} จังหวัด")
        
        print("\n" + "=" * 80)
    
    def get_driver_summary(self):
        """Get summary of all drivers"""
        if not self.drivers_stats:
            return "ไม่มีข้อมูลสถิติ"
        
        summary = []
        for driver, stats in self.drivers_stats.items():
            summary.append({
                'driver': driver,
                'total_trips': stats['total_trips'],
                'unique_locations': stats['unique_locations'],
                'provinces': stats['provinces_covered']
            })
        
        # Sort by total trips
        summary.sort(key=lambda x: x['total_trips'], reverse=True)
        return summary

# Example usage
if __name__ == "__main__":
    # Initialize system
    system = DriverRecommendationSystem()
    
    # Option 1: Load from Google Sheets (requires credentials)
    # system.load_data_from_sheets("YOUR_GOOGLE_SHEETS_URL")
    
    # Option 2: Load sample data for testing
    system.load_sample_data()
    
    # Build experience matrix
    system.build_experience_matrix()
    
    # Get recommendations
    system.print_recommendations("โรงพยาบาลมหาราชนครเชียงใหม่", "เชียงใหม่")
    
    # Print driver summary
    print("\n📋 สรุปข้อมูลพนักงานขับรถ:")
    summary = system.get_driver_summary()
    for i, driver_info in enumerate(summary[:5], 1):
        print(f"{i}. {driver_info['driver']}: {driver_info['total_trips']} เที่ยว, "
              f"{driver_info['unique_locations']} สถานที่, {driver_info['provinces']} จังหวัด")