from app import app
import pages    # Calendar, Analytics and Profile pages
import api      # JSON API used by the login popup
import planner  # Smart Schedule page
import whatif   # What-if simulator page
import admin    # Admin panel

if __name__ == "__main__":
    app.run(debug=True)