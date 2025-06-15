import sqlite3
from collections import defaultdict
import pandas as pd

class RecommendationEngine:
    def __init__(self, db_path="driver_data.db"):
        """
        Recommendation Engine for Driver Selection
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.experience_matrix = defaultdict(lambda: defaultdict(int))
        self.province_experience = defaultdict(lambda: defaultdict(int))
        self.drivers_stats = {}
        self.load_data()
    
    def load_data(self):
        """Load data from database and build matrices"""
        conn = sqlite3.connect(self.db_path)
        
        # Load trips
        trips_df = pd.read_sql_query("SELECT * FROM trips", conn)
        
        # Load driver stats
        stats_df = pd.read_sql_query("SELECT * FROM drivers", conn)
        
        conn.close()
        
        # Build experience matrices
        for _, row in trips_df.iterrows():
            driver = row['driver']
            location = row['location']
            province = row['province']
            
            self.experience_matrix[driver][location] += 1
            if pd.notna(province):
                self.province_experience[driver][province] += 1
        
        # Store driver stats
        for _, row in stats_df.iterrows():
            self.drivers_stats[row['driver_name']] = {
                'total_trips': row['total_trips'],
                'unique_locations': row['unique_locations'],
                'provinces_covered': row['provinces_covered']
            }
        
        print(f"✅ Loaded data for {len(self.drivers_stats)} drivers")
    
    def calculate_route_score(self, destinations):
        """
        Calculate compatibility score for multiple destinations (1-4 locations)
        
        Args:
            destinations: List of dict [{'name': str, 'province': str}, ...]
            
        Returns:
            dict: Driver scores with explanations
        """
        if not destinations or len(destinations) > 4:
            raise ValueError("Destinations must be 1-4 locations")
        
        scores = {}
        
        for driver in self.experience_matrix.keys():
            total_score = 0
            explanations = []
            route_details = []
            
            for i, dest in enumerate(destinations, 1):
                dest_name = dest['name']
                dest_province = dest.get('province', '')
                
                # Calculate score for this destination
                dest_score = 0
                dest_explanations = []
                
                # 1. Direct experience (40% weight)
                direct_exp = self.experience_matrix[driver].get(dest_name, 0)
                if direct_exp > 0:
                    points = min(direct_exp * 10, 40)
                    dest_score += points
                    dest_explanations.append(f"เคยไป {dest_name} จำนวน {direct_exp} ครั้ง ({points} คะแนน)")
                
                # 2. Province experience (30% weight)
                if dest_province:
                    province_exp = self.province_experience[driver].get(dest_province, 0)
                    if province_exp > 0:
                        points = min(province_exp * 3, 30)
                        dest_score += points
                        dest_explanations.append(f"มีประสบการณ์ในจังหวัด {dest_province} จำนวน {province_exp} ครั้ง ({points} คะแนน)")
                
                # 3. Similar locations (20% weight)
                similar_locations = self._find_similar_locations(dest_name, driver)
                if similar_locations:
                    points = min(len(similar_locations) * 4, 20)
                    dest_score += points
                    dest_explanations.append(f"เคยไปสถานที่คล้ายกัน {len(similar_locations)} แห่ง ({points} คะแนน)")
                
                # 4. Overall experience (10% weight)
                if driver in self.drivers_stats:
                    total_exp = self.drivers_stats[driver]['total_trips']
                    points = min(total_exp * 0.5, 10)
                    dest_score += points
                    if i == 1:  # Only add this explanation once
                        dest_explanations.append(f"ประสบการณ์รวม {total_exp} เที่ยว ({points} คะแนน)")
                
                total_score += dest_score
                route_details.append({
                    'destination': dest_name,
                    'province': dest_province,
                    'score': round(dest_score, 2),
                    'explanations': dest_explanations
                })
            
            # Calculate average score for the route
            avg_score = total_score / len(destinations)
            
            scores[driver] = {
                'total_score': round(total_score, 2),
                'average_score': round(avg_score, 2),
                'route_details': route_details,
                'stats': self.drivers_stats.get(driver, {}),
                'destinations_count': len(destinations)
            }
        
        return scores
    
    def _find_similar_locations(self, destination, driver):
        """Find similar locations that driver has been to"""
        similar = []
        destination_words = set(destination.lower().split())
        
        for location in self.experience_matrix[driver].keys():
            location_words = set(location.lower().split())
            common_words = destination_words.intersection(location_words)
            common_words.discard('โรงพยาบาล')
            common_words.discard('ที่')
            
            if len(common_words) > 0:
                similar.append(location)
        
        return similar[:5]
    
    def get_top_drivers(self, destinations, top_n=10):
        """
        Get top N drivers for the route
        
        Args:
            destinations: List of destinations
            top_n: Number of top drivers to return
            
        Returns:
            list: Top drivers with rankings
        """
        scores = self.calculate_route_score(destinations)
        
        # Sort by average score
        sorted_drivers = sorted(scores.items(), key=lambda x: x[1]['average_score'], reverse=True)
        
        # Return top N
        top_drivers = []
        for i, (driver, data) in enumerate(sorted_drivers[:top_n], 1):
            top_drivers.append({
                'rank': i,
                'driver': driver,
                'total_score': data['total_score'],
                'average_score': data['average_score'],
                'route_details': data['route_details'],
                'stats': data['stats'],
                'destinations_count': data['destinations_count']
            })
        
        return top_drivers