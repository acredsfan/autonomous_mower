from multiprocessing import Process
from mower.ui.web_ui.app import create_app

def start_web():
    app = create_app()
    app.run(host="0.0.0.0", port=8000)

def launch():
    p = Process(target=start_web, daemon=True)
    p.start()
    return p
