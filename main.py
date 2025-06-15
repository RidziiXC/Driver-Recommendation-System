import tkinter as tk
from gui_application import DriverRecommendationGUI

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = DriverRecommendationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()