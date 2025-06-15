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
        Calculate actual trip counts for multiple destinations (1-4 locations)
        
        Args:
            destinations: List of dict [{'name': str, 'province': str}, ...]
            
        Returns:
            dict: Driver trip counts with details
        """
        if not destinations or len(destinations) > 4:
            raise ValueError("Destinations must be 1-4 locations")
        
        results = {}
        
        for driver in self.experience_matrix.keys():
            route_details = []
            total_trips = 0
            destinations_visited = 0
            
            for i, dest in enumerate(destinations, 1):
                dest_name = dest['name']
                dest_province = dest.get('province', '')
                
                # Get actual trip count for this destination
                trip_count = self.experience_matrix[driver].get(dest_name, 0)
                
                route_details.append({
                    'destination': dest_name,
                    'province': dest_province,
                    'trip_count': trip_count,
                    'visited': trip_count > 0
                })
                
                total_trips += trip_count
                if trip_count > 0:
                    destinations_visited += 1
            
            results[driver] = {
                'total_trips': total_trips,
                'destinations_visited': destinations_visited,
                'destinations_count': len(destinations),
                'completion_ratio': destinations_visited / len(destinations),
                'route_details': route_details,
                'stats': self.drivers_stats.get(driver, {})
            }
        
        return results
    
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
    
    def get_top_drivers(self, destinations, top_n=30):
        """
        Get top N drivers for the route based on actual trip counts
        
        Args:
            destinations: List of destinations
            top_n: Number of top drivers to return (default 30)
            
        Returns:
            list: Top drivers with rankings based on actual experience
        """
        results = self.calculate_route_score(destinations)
        
        # Sort by:
        # 1. Number of destinations visited (descending)
        # 2. Total trips to those destinations (descending)
        # 3. Driver name (ascending) for ties
        sorted_drivers = sorted(
            results.items(), 
            key=lambda x: (
                x[1]['destinations_visited'],      # Primary: destinations visited
                x[1]['total_trips'],               # Secondary: total trips
                -ord(x[0][0])                     # Tertiary: driver name (reverse alphabetical)
            ), 
            reverse=True
        )
        
        # Return top N
        top_drivers = []
        for i, (driver, data) in enumerate(sorted_drivers[:top_n], 1):
            top_drivers.append({
                'rank': i,
                'driver': driver,
                'destinations_visited': data['destinations_visited'],
                'total_trips': data['total_trips'],
                'destinations_count': data['destinations_count'],
                'completion_ratio': data['completion_ratio'],
                'route_details': data['route_details'],
                'stats': data['stats']
            })
        
        return top_drivers