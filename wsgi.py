# WSGI entrypoint for PythonAnywhere deployment
import main
from server import create_app

# PythonAnywhere looks for 'application' or 'app'
application = create_app({
    "info": main.info,
    "start": main.start,
    "move": main.move,
    "end": main.end
})
app = application

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
