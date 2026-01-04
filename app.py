from flask import Flask, render_template, request, jsonify
import logging
import os
import sys
from threading import Timer
from utils import get_network_interfaces, copy_to_clipboard, ensure_ssl_certs, open_browser, print_server_info

base_dir = '.'
if hasattr(sys, '_MEIPASS'):
    base_dir = os.path.join(sys._MEIPASS)

app = Flask(__name__,
            static_folder=os.path.join(base_dir, 'static'),
            template_folder=os.path.join(base_dir, 'templates'))

# Global variables
LATEST_TEXT = None
PROTOCOL = 'http'
PORT = 6999

@app.route('/')
def index():
    global LATEST_TEXT
    LATEST_TEXT = None  # Reset on reload
    interfaces = get_network_interfaces()
    return render_template('index.html', interfaces=interfaces, protocol=PROTOCOL, port=PORT)


@app.route('/mobile')
def mobile_page():
    return render_template('mobile.html')


@app.route('/submit', methods=['POST'])
def receive_text():
    global LATEST_TEXT
    data = request.get_json() or request.form
    content = data.get('content')
    
    if content:
        print(f"Received text: {content}")
        LATEST_TEXT = content
        copy_to_clipboard(content)
        return "Received"
    return "No content", 400

@app.route('/poll')
def poll_content():
    global LATEST_TEXT
    if LATEST_TEXT:
        return jsonify({'received': True, 'content': LATEST_TEXT})
    return jsonify({'received': False})

@app.route('/reset', methods=['POST'])
def reset_state():
    global LATEST_TEXT
    LATEST_TEXT = None
    return jsonify({'status': 'reset'})


if __name__ == '__main__':
    # Setup logging
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # Try to setup SSL
    ssl_context = ensure_ssl_certs()
    if ssl_context:
        PROTOCOL = 'https'
    else:
        PROTOCOL = 'http'

    # Print info
    print_server_info(PROTOCOL, PORT)
    
    # Open browser after 1.5 seconds
    Timer(1.5, lambda: open_browser(PROTOCOL, PORT)).start()
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, ssl_context=ssl_context)
    except Exception as e:
        print(f"\n!!! Error starting server with HTTPS: {e}")
        if PROTOCOL == 'https':
            print("Falling back to HTTP...")
            PROTOCOL = 'http'
            app.run(host='0.0.0.0', port=PORT, debug=False, ssl_context=None)
