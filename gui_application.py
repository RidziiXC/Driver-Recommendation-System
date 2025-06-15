import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from database_manager import DatabaseManager
from recommendation_engine import RecommendationEngine

class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, parent, data_dict, on_select_callback=None, **kwargs):
        """
        Autocomplete Combobox widget
        
        Args:
            parent: Parent widget
            data_dict: Dictionary of {location: province}
            on_select_callback: Function to call when selection is made
        """
        super().__init__(parent, **kwargs)
        
        self.data_dict = data_dict
        self.location_list = list(data_dict.keys())
        self.on_select_callback = on_select_callback
        
        # Configure combobox
        self['values'] = self.location_list
        self['state'] = 'normal'
        
        # Bind events
        self.bind('<KeyRelease>', self.on_keyrelease)
        self.bind('<<ComboboxSelected>>', self.on_select)
        self.bind('<FocusOut>', self.on_focus_out)
        
    def on_keyrelease(self, event):
        """Handle key release event for autocomplete"""
        # Get current value
        current_text = self.get().lower()
        
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Tab', 'Return'):
            return
        
        # Filter locations based on input
        if current_text:
            filtered_locations = [
                location for location in self.location_list 
                if current_text in location.lower()
            ]
        else:
            filtered_locations = self.location_list
        
        # Update dropdown values
        self['values'] = filtered_locations
        
        # Auto-select first match if exact match found
        if filtered_locations:
            for location in filtered_locations:
                if location.lower().startswith(current_text):
                    # Don't auto-complete while user is typing
                    break
    
    def on_select(self, event):
        """Handle selection event"""
        selected_location = self.get()
        
        if selected_location in self.data_dict and self.on_select_callback:
            province = self.data_dict[selected_location]
            self.on_select_callback(selected_location, province)
    
    def on_focus_out(self, event):
        """Handle focus out event"""
        current_text = self.get()
        
        # Try to find exact match
        if current_text in self.data_dict and self.on_select_callback:
            province = self.data_dict[current_text]
            self.on_select_callback(current_text, province)
    
    def clear(self):
        """Clear the combobox"""
        self.set('')
        self['values'] = self.location_list

class DriverRecommendationGUI:
    def __init__(self, root):
        """
        GUI Application for Driver Recommendation System
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Driver Recommendation Gameeeeeeeeeeeee")
        self.root.geometry("1200x800")
        
        self.db_manager = DatabaseManager()
        self.recommendation_engine = RecommendationEngine()
        self.locations_data = {}
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create GUI widgets"""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Data Management
        data_frame = ttk.Frame(notebook)
        notebook.add(data_frame, text="Data Management")
        self.create_data_tab(data_frame)
        
        # Tab 2: Route Planning
        route_frame = ttk.Frame(notebook)
        notebook.add(route_frame, text="Route Planning")
        self.create_route_tab(route_frame)
        
        # Tab 3: Results
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="Results")
        self.create_results_tab(results_frame)
    
    def create_data_tab(self, parent):
        """Create data management tab"""
        # Google Sheets section
        sheets_frame = ttk.LabelFrame(parent, text="Google Sheets Import")
        sheets_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(sheets_frame, text="Spreadsheet URL:").pack(anchor=tk.W, padx=5, pady=2)
        self.url_entry = tk.Entry(sheets_frame, width=80)
        self.url_entry.pack(fill=tk.X, padx=5, pady=2)
        
        # Set default URL
        self.url_entry.insert(0, "https://docs.google.com/spreadsheets/d/1VR2Txo8ixXEGsQXQWvuR3CBuGX9xH2Axc9dNV1TT3Tc/edit?gid=496816900#gid=496816900")
        
        tk.Label(sheets_frame, text="Credentials Path (optional):").pack(anchor=tk.W, padx=5, pady=2)
        cred_frame = tk.Frame(sheets_frame)
        cred_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.cred_entry = tk.Entry(cred_frame, width=60)
        self.cred_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(cred_frame, text="Browse", command=self.browse_credentials).pack(side=tk.RIGHT, padx=(5, 0))
        
        tk.Button(sheets_frame, text="Load Data", command=self.load_data, bg="green", fg="white").pack(pady=5)
        
        # Database info section
        info_frame = ttk.LabelFrame(parent, text="Database Information")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=15)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Button(info_frame, text="Refresh Info", command=self.refresh_info).pack(pady=5)
        
        # Load initial info
        self.refresh_info()
    
    def create_route_tab(self, parent):
        """Create route planning tab"""
        # Instructions
        inst_frame = ttk.LabelFrame(parent, text="Instructions")
        inst_frame.pack(fill=tk.X, padx=10, pady=5)
        
        instructions = "กำหนดจุดส่ง ขั้นต่ำ 1 จุด สูงสุด 4 จุด เพื่อคำนวณ Ranking ของพนักงานขับรถ\nพิมพ์ชื่อสถานที่เพื่อค้นหาและเลือกจาก dropdown (จังหวัดจะถูกใส่อัตโนมัติ)"
        tk.Label(inst_frame, text=instructions, wraplength=600, justify=tk.LEFT).pack(padx=10, pady=5)
        
        # Destinations input
        dest_frame = ttk.LabelFrame(parent, text="Destinations (1-4 จุด)")
        dest_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.destinations = []
        self.dest_entries = []
        
        for i in range(4):
            frame = tk.Frame(dest_frame)
            frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(frame, text=f"จุดที่ {i+1}:", width=8).pack(side=tk.LEFT)
            
            # Create autocomplete combobox for location
            location_combo = AutocompleteCombobox(
                frame, 
                self.locations_data,
                on_select_callback=lambda loc, prov, idx=i: self.on_location_select(idx, loc, prov),
                width=50
            )
            location_combo.pack(side=tk.LEFT, padx=(0, 10))
            
            tk.Label(frame, text="จังหวัด:", width=8).pack(side=tk.LEFT)
            
            province_entry = tk.Entry(frame, width=20, state='readonly', bg='#f0f0f0')
            province_entry.pack(side=tk.LEFT)
            
            self.dest_entries.append({
                'location': location_combo, 
                'province': province_entry
            })
            
            if i == 0:
                # Add red border to indicate required field
                location_combo.configure(style='Required.TCombobox')
        
        # Create style for required field
        style = ttk.Style()
        style.configure('Required.TCombobox', fieldbackground='#ffe6e6')
        
        # Control buttons
        button_frame = tk.Frame(dest_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        tk.Button(button_frame, text="Clear All", command=self.clear_destinations).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Refresh Locations", command=self.refresh_locations).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(button_frame, text="Calculate Ranking", command=self.calculate_ranking, 
                 bg="blue", fg="white").pack(side=tk.RIGHT)
    
    def on_location_select(self, index, location, province):
        """Handle location selection"""
        # Auto-fill province
        province_entry = self.dest_entries[index]['province']
        province_entry.config(state='normal')
        province_entry.delete(0, tk.END)
        province_entry.insert(0, province)
        province_entry.config(state='readonly')
    
    def refresh_locations(self):
        """Refresh locations data from database"""
        try:
            self.locations_data = self.db_manager.get_locations_list()
            
            # Update all comboboxes with new data
            for entry_pair in self.dest_entries:
                location_combo = entry_pair['location']
                location_combo.data_dict = self.locations_data
                location_combo.location_list = list(self.locations_data.keys())
                location_combo['values'] = location_combo.location_list
            
            messagebox.showinfo("Success", f"Refreshed {len(self.locations_data)} locations")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh locations: {str(e)}")
    
    def create_results_tab(self, parent):
        """Create results display tab"""
        # Results display
        self.results_text = scrolledtext.ScrolledText(parent, height=30, font=("Courier", 10))
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control buttons
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(button_frame, text="Clear Results", command=self.clear_results).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Export Results", command=self.export_results).pack(side=tk.RIGHT)
    
    def browse_credentials(self):
        """Browse for credentials file"""
        filename = filedialog.askopenfilename(
            title="Select Google Service Account JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.cred_entry.delete(0, tk.END)
            self.cred_entry.insert(0, filename)
    
    def load_data(self):
        """Load data from Google Sheets"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter Google Sheets URL")
            return
        
        cred_path = self.cred_entry.get().strip()
        cred_path = cred_path if cred_path else None
        
        def load_thread():
            try:
                success = self.db_manager.load_from_google_sheets(url, cred_path)
                if success:
                    # Reload recommendation engine
                    self.recommendation_engine = RecommendationEngine()
                    # Refresh locations data
                    self.locations_data = self.db_manager.get_locations_list()
                    
                    # Update comboboxes
                    self.root.after(0, self.refresh_locations)
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Data loaded successfully!"))
                    self.root.after(0, self.refresh_info)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to load data. Please check:\n1. Google Sheets is public\n2. URL is correct\n3. Sheet contains valid data"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error: {str(e)}"))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def refresh_info(self):
        """Refresh database information"""
        try:
            stats_df = self.db_manager.get_driver_stats()
            trips_df = self.db_manager.get_all_trips()
            
            info = f"📊 Database Information\n"
            info += f"{'='*50}\n\n"
            
            if len(trips_df) == 0:
                info += f"❌ No data loaded. Please load data from Google Sheets first.\n\n"
                info += f"Required steps:\n"
                info += f"1. Make Google Sheets public\n"
                info += f"2. Use correct URL\n"
                info += f"3. Click 'Load Data' button\n"
            else:
                info += f"📈 Total Trips: {len(trips_df)}\n"
                info += f"👥 Total Drivers: {len(stats_df)}\n"
                info += f"📍 Unique Locations: {len(self.locations_data)}\n\n"
                info += f"🏆 Top Drivers by Experience:\n"
                info += f"{'-'*40}\n"
                
                for i, row in stats_df.head(10).iterrows():
                    info += f"{i+1:2d}. {row['driver_name']:<20} - {row['total_trips']:2d} trips, "
                    info += f"{row['unique_locations']:2d} locations, {row['provinces_covered']:2d} provinces\n"
                
                if len(trips_df) > 0:
                    info += f"\n📍 Recent Trips:\n"
                    info += f"{'-'*40}\n"
                    for i, row in trips_df.tail(5).iterrows():
                        info += f"• {row['driver']} → {row['location']} ({row['province']})\n"
            
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info)
            
        except Exception as e:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, f"Error loading database info: {str(e)}\n\nPlease load data first.")
    
    def clear_destinations(self):
        """Clear all destination entries"""
        for entry_pair in self.dest_entries:
            entry_pair['location'].clear()
            province_entry = entry_pair['province']
            province_entry.config(state='normal')
            province_entry.delete(0, tk.END)
            province_entry.config(state='readonly')
    
    def calculate_ranking(self):
        """Calculate driver ranking for route"""
        # Check if we have data
        if not self.locations_data:
            messagebox.showerror("Error", "No location data available. Please load data from Google Sheets first.")
            return
            
        # Get destinations
        destinations = []
        for entry_pair in self.dest_entries:
            location = entry_pair['location'].get().strip()
            province = entry_pair['province'].get().strip()
            
            if location:
                destinations.append({
                    'name': location,
                    'province': province if province else None
                })
        
        if not destinations:
            messagebox.showerror("Error", "Please enter at least one destination")
            return
        
        if len(destinations) > 4:
            messagebox.showerror("Error", "Maximum 4 destinations allowed")
            return
        
        def calculate_thread():
            try:
                # Get top drivers
                top_drivers = self.recommendation_engine.get_top_drivers(destinations, top_n=30)
                
                if not top_drivers:
                    self.root.after(0, lambda: messagebox.showerror("Error", "No driver recommendations found. Please check your data."))
                    return
                
                # Format results
                results = self.format_results(destinations, top_drivers)
                
                # Display results
                self.root.after(0, lambda: self.display_results(results))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Calculation error: {str(e)}"))
        
        threading.Thread(target=calculate_thread, daemon=True).start()
    
    def format_results(self, destinations, top_drivers):
        """Format calculation results"""
        result = f"🎯 DRIVER RANKING RESULTS\n"
        result += f"{'='*80}\n\n"
        
        # Route summary
        result += f"📍 Route Summary ({len(destinations)} destinations):\n"
        for i, dest in enumerate(destinations, 1):
            result += f"   {i}. {dest['name']}"
            if dest['province']:
                result += f" ({dest['province']})"
            result += f"\n"
        result += f"\n"
        
        # Top drivers ranking
        result += f"🏆 TOP {len(top_drivers)} DRIVERS RANKING (Based on Actual Experience):\n"
        result += f"{'='*80}\n"
        
        for driver_info in top_drivers:
            visited = driver_info['destinations_visited']
            total_dest = driver_info['destinations_count']
            total_trips = driver_info['total_trips']
            
            result += f"\n📍 RANK #{driver_info['rank']}: {driver_info['driver']}\n"
            result += f"{'─'*60}\n"
            result += f"📊 Destinations Visited: {visited}/{total_dest} | Total Trips: {total_trips}\n"
            
            stats = driver_info['stats']
            if stats:
                result += f"📈 Overall Experience: {stats['total_trips']} trips, "
                result += f"{stats['unique_locations']} locations, "
                result += f"{stats['provinces_covered']} provinces\n"
            
            result += f"\n💡 Route Experience Details:\n"
            for detail in driver_info['route_details']:
                status_icon = "✅" if detail['visited'] else "❌"
                result += f"   {status_icon} {detail['destination']}"
                if detail['province']:
                    result += f" ({detail['province']})"
                
                if detail['visited']:
                    result += f" - เคยไป {detail['trip_count']} ครั้ง\n"
                else:
                    result += f" - ไม่เคยไป\n"
            
            result += f"\n"
        
        return result
    
    def display_results(self, results):
        """Display results in results tab"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, results)
        
        # Switch to results tab
        notebook = self.root.children['!notebook']
        notebook.select(2)  # Select results tab
        
        messagebox.showinfo("Success", "Ranking calculation completed!")
    
    def clear_results(self):
        """Clear results display"""
        self.results_text.delete(1.0, tk.END)
    
    def export_results(self):
        """Export results to file"""
        content = self.results_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "No results to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {str(e)}")