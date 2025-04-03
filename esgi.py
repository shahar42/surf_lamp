# wsgi.py
from app import app  # Assuming your main Flask file is app.py and the instance is 'app'

if __name__ == "__main__":
    # This part is generally not used by Gunicorn but can be helpful
    # if you ever run this file directly.
    # Gunicorn will directly import the 'app' object.
    app.run()
