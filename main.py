import eel
import keyboard
import pyautogui
import time
import threading
import sys
import qrcode
import io
import base64
import bottle
import ifaddr
import re
import os
import random
import string
import queue
import pyperclip
import traceback
from utils import get_local_ip, ensure_ssl_certs, copy_to_clipboard, load_app_data, save_app_data, delete_app_data, hash_pin, get_app_data_dir

# --- Fix for PyInstaller Path ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Logging Setup ---
LOG_FILE_PATH = os.path.join(get_app_data_dir(), "debug.log")

class LoggerWriter:
    def write(self, message):
        if message.strip():
            log_error(message)
    def flush(self):
        pass

def log_error(msg):
    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(f"{time.ctime()}: {msg}\n")
    except:
        pass

# Redirect stdout/stderr to prevent crashes in windowed mode
if sys.stdout is None: sys.stdout = LoggerWriter()
if sys.stderr is None: sys.stderr = LoggerWriter()

# Initialize Eel with the 'web' folder
eel.init('web')

# Load stored data or initialize empty
TEXT_DATA = load_app_data()

# Global state
ACTIVE_SESSION = None
DESKTOP_PORT = 8000
MOBILE_PORT = 8001
PROTOCOL = 'http' 

# Typing Queue
typing_queue = queue.Queue()

# --- Helper Functions ---

def get_network_interfaces():
    """Returns a list of dicts with 'name' and 'ip' for valid interfaces."""
    network_adapters = ifaddr.get_adapters()
    interfaces = []
    
    for adapter in network_adapters:
        for ip in adapter.ips:
            ip_str = str(ip.ip)
            if re.match(r"^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$", ip_str):
                if ip_str == "127.0.0.1" or ip_str.startswith("169.254"):
                    continue
                interfaces.append({
                    'name': f"{adapter.nice_name} ({ip_str})",
                    'ip': ip_str
                })
    
    if not interfaces:
        interfaces.append({'name': 'Localhost (127.0.0.1)', 'ip': '127.0.0.1'})
        
    return interfaces

def generate_session_key(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- Mobile Server (Bottle) ---
mobile_app = bottle.Bottle()

@mobile_app.route('/mobile_page')
def mobile_ui():
    return bottle.static_file('mobile.html', root=resource_path('web'))

@mobile_app.route('/css/<filepath:path>')
def server_static_css(filepath):
    return bottle.static_file(filepath, root=resource_path('web/css'))

@mobile_app.route('/js/<filepath:path>')
def server_static_js(filepath):
    return bottle.static_file(filepath, root=resource_path('web/js'))

@mobile_app.route('/mobile_submit', method='POST')
def mobile_submit():
    global ACTIVE_SESSION
    data = bottle.request.json
    content = data.get('content')
    key = data.get('key')
    
    if not ACTIVE_SESSION:
        return bottle.HTTPResponse(status=403, body="Session expired.")
    if ACTIVE_SESSION['key'] != key:
        return bottle.HTTPResponse(status=403, body="Invalid session key.")
        
    target_id = ACTIVE_SESSION['target_id']
    
    if content:
        if target_id == 'CLIPBOARD':
            copy_to_clipboard(content)
            eel.on_clipboard_received()
        else:
            eel.update_row_text(target_id, content)
        
        ACTIVE_SESSION = None
        return "OK"
    return "Error", 400

def run_mobile_server():
    global PROTOCOL
    local_ip = get_local_ip()
    
    try:
        ssl_files = ensure_ssl_certs()
    except Exception as e:
        log_error(f"SSL Cert Generation Failed: {e}")
        ssl_files = None

    run_args = {
        'host': '0.0.0.0',
        'port': MOBILE_PORT,
        'quiet': True
    }
    
    if ssl_files:
        PROTOCOL = 'https'
        log_error(f"Starting Mobile Server on HTTPS port {MOBILE_PORT} (IP: {local_ip})...")
        run_args['server'] = 'cheroot'
        run_args['certfile'] = ssl_files[0]
        run_args['keyfile'] = ssl_files[1]
    else:
        log_error(f"Starting Mobile Server on HTTP port {MOBILE_PORT} (No SSL)...")
    
    try:
        mobile_app.run(**run_args)
    except Exception as e:
        log_error(f"Failed to start mobile server: {e}\n{traceback.format_exc()}")

# --- Eel Exposed Functions ---

@eel.expose
def get_initial_state():
    return TEXT_DATA

@eel.expose
def get_interfaces():
    return get_network_interfaces()

@eel.expose
def generate_qr(target_id, ip_address):
    global ACTIVE_SESSION
    session_key = generate_session_key()
    ACTIVE_SESSION = {
        'key': session_key,
        'target_id': target_id
    }
    
    # Use the IP address provided by the frontend (user selection)
    mobile_url = f"{PROTOCOL}://{ip_address}:{MOBILE_PORT}/mobile_page?key={session_key}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(mobile_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        'url': mobile_url,
        'qr_image': f"data:image/png;base64,{img_str}"
    }

@eel.expose
def cancel_fetch_session():
    global ACTIVE_SESSION
    if ACTIVE_SESSION:
        ACTIVE_SESSION = None

@eel.expose
def save_row_data(row_id, text, is_password, shortcut):
    global TEXT_DATA
    row_id_str = str(row_id)
    
    old_shortcut = TEXT_DATA.get(row_id_str, {}).get('shortcut')
    
    TEXT_DATA[row_id_str] = {
        'text': text,
        'is_password': is_password,
        'shortcut': shortcut
    }
    save_app_data(TEXT_DATA)
    
    if old_shortcut != shortcut:
        update_hotkeys()

@eel.expose
def delete_row_data(row_id):
    global TEXT_DATA
    row_id_str = str(row_id)
    if row_id_str in TEXT_DATA:
        del TEXT_DATA[row_id_str]
        save_app_data(TEXT_DATA)
        update_hotkeys()

@eel.expose
def reset_application():
    global TEXT_DATA
    TEXT_DATA = {}
    delete_app_data()
    update_hotkeys()
    return True

@eel.expose
def reload_hotkeys():
    threading.Thread(target=update_hotkeys).start()

# --- PIN Logic ---

@eel.expose
def check_pin_exists():
    return '__SETTINGS__' in TEXT_DATA and 'pin_hash' in TEXT_DATA['__SETTINGS__']

@eel.expose
def set_app_pin(pin):
    global TEXT_DATA
    if '__SETTINGS__' not in TEXT_DATA:
        TEXT_DATA['__SETTINGS__'] = {}
    
    TEXT_DATA['__SETTINGS__']['pin_hash'] = hash_pin(pin)
    save_app_data(TEXT_DATA)
    return True

@eel.expose
def verify_app_pin(pin):
    if '__SETTINGS__' not in TEXT_DATA or 'pin_hash' not in TEXT_DATA['__SETTINGS__']:
        return False
    
    stored_hash = TEXT_DATA['__SETTINGS__']['pin_hash']
    return stored_hash == hash_pin(pin)

# --- Desktop Logic ---

def release_all_modifiers():
    modifiers = ['ctrl', 'alt', 'shift', 'win', 'command']
    for key in modifiers:
        try:
            pyautogui.keyUp(key)
        except:
            pass

def typing_worker():
    while True:
        item = typing_queue.get()
        if item is None: break
        
        text, is_password = item
        
        try:
            keyboard.unhook_all()
            time.sleep(0.2)
            release_all_modifiers()
            
            if is_password:
                pyautogui.write(text, interval=0.01)
            else:
                old_clipboard = pyperclip.paste()
                pyperclip.copy(text)
                
                if sys.platform == 'darwin':
                    pyautogui.hotkey('command', 'v')
                else:
                    pyautogui.hotkey('ctrl', 'v')
                
                time.sleep(0.1)
                pyperclip.copy(old_clipboard)
                
        except Exception as e:
            log_error(f"Typing error: {e}")
        finally:
            release_all_modifiers()
            update_hotkeys()
            typing_queue.task_done()

def on_hotkey_triggered(row_id):
    if row_id in TEXT_DATA:
        data = TEXT_DATA[row_id]
        text = data.get('text', '')
        is_password = data.get('is_password', False)
        if text:
            typing_queue.put((text, is_password))

def update_hotkeys():
    try:
        keyboard.unhook_all()
        time.sleep(0.1) 
    except Exception as e:
        log_error(f"Error unhooking: {e}")
    
    for row_id, data in TEXT_DATA.items():
        if row_id == '__SETTINGS__': continue # Skip settings

        shortcut = data.get('shortcut')
        if shortcut:
            try:
                keyboard.add_hotkey(shortcut, lambda r=row_id: on_hotkey_triggered(r), suppress=True)
            except Exception as e:
                log_error(f"Failed to register hotkey {shortcut}: {e}")

if __name__ == '__main__':
    # Clear log on startup
    try:
        with open(LOG_FILE_PATH, "w") as f: f.write("App Started\n")
    except: pass

    worker_thread = threading.Thread(target=typing_worker, daemon=True)
    worker_thread.start()
    
    update_hotkeys()
    
    t = threading.Thread(target=run_mobile_server)
    t.daemon = True
    t.start()
    
    try:
        print(f"Starting Desktop UI on port {DESKTOP_PORT}...")
        eel.start('index.html', size=(900, 800), port=DESKTOP_PORT)
    except (SystemExit, MemoryError, KeyboardInterrupt):
        print("Exiting...")
        keyboard.unhook_all()
        os._exit(0)
    except Exception as e:
        log_error(f"Fatal Error: {e}\n{traceback.format_exc()}")
