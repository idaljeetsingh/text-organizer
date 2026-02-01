import ifaddr
import re
import platform
import subprocess
import os
import webbrowser
import sys
import socket
import ipaddress
import json
import base64
import uuid
import hashlib
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# --- Encryption Logic ---

def get_machine_id():
    """
    Retrieves a unique machine identifier to bind encryption to this specific hardware.
    """
    machine_id = None
    system = platform.system()

    try:
        if system == 'Windows':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            machine_id, _ = winreg.QueryValueEx(key, "MachineGuid")
        elif system == 'Linux':
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
            elif os.path.exists('/var/lib/dbus/machine-id'):
                with open('/var/lib/dbus/machine-id', 'r') as f:
                    machine_id = f.read().strip()
        elif system == 'Darwin':
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID"
            output = subprocess.check_output(cmd, shell=True).decode()
            machine_id = output.split('"')[-2]
    except Exception as e:
        print(f"Error fetching machine ID: {e}")

    if not machine_id:
        print("Using fallback ID for encryption.")
        machine_id = str(uuid.getnode()) + os.getlogin()
        
    return machine_id.encode('utf-8')

_SALT = b'TextOrganizer_Static_Salt_v1' 

def _get_cipher():
    password = get_machine_id()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

def hash_pin(pin):
    """Hashes a 4-digit pin with a salt."""
    return hashlib.sha256(pin.encode() + _SALT).hexdigest()

# --- Persistence Logic ---

def get_app_data_path():
    """Returns the path to the application data file."""
    app_name = "TextOrganizer"
    
    if platform.system() == "Windows":
        base_dir = os.getenv('APPDATA')
    elif platform.system() == "Darwin":
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:
        base_dir = os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))

    app_dir = os.path.join(base_dir, app_name)
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "data.dat")

def save_app_data(data):
    """Saves the data dictionary to an encrypted file."""
    try:
        file_path = get_app_data_path()
        json_str = json.dumps(data)
        cipher = _get_cipher()
        encrypted_data = cipher.encrypt(json_str.encode('utf-8'))
        
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_app_data():
    """Loads and decrypts data from the file. Returns empty dict if not found."""
    file_path = get_app_data_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            cipher = _get_cipher()
            decrypted_data = cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            print(f"Error loading/decrypting data: {e}")
            return {}
    return {}

def delete_app_data():
    """Deletes the persistent data file."""
    file_path = get_app_data_path()
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting data: {e}")
            return False
    return True

# --- Network & SSL Logic ---

def get_local_ip():
    """Helper to find the primary local IP address."""
    network_adapters = ifaddr.get_adapters()
    candidates = []
    
    for adapter in network_adapters:
        for ip in adapter.ips:
            ip_str = str(ip.ip)
            if re.match(r"^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$", ip_str):
                if ip_str == "127.0.0.1" or ip_str.startswith("169.254"):
                    continue
                candidates.append((adapter.nice_name, ip_str))

    for name, ip in candidates:
        name_lower = name.lower()
        if any(x in name_lower for x in ["wi-fi", "wifi", "ethernet", "wlan", "eth", "en"]):
            return ip
            
    if candidates:
        return candidates[0][1]
        
    return "127.0.0.1"

def get_all_ips():
    """Returns a list of all valid local IPv4 addresses."""
    network_adapters = ifaddr.get_adapters()
    ips = []
    
    for adapter in network_adapters:
        for ip in adapter.ips:
            ip_str = str(ip.ip)
            if re.match(r"^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$", ip_str):
                if ip_str == "127.0.0.1" or ip_str.startswith("169.254"):
                    continue
                ips.append(ip_str)
    
    ips.append("127.0.0.1")
    return list(set(ips)) 

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

def copy_to_clipboard(text):
    """Platform-agnostic clipboard copy."""
    system = platform.system()
    try:
        if system == 'Darwin':  # macOS
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        elif system == 'Windows':
            # Windows 'clip' command
            subprocess.run(['clip'], input=text.encode('utf-16'), check=True)
        else:
            # Linux (try xclip or xsel)
            try:
                subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)
            except FileNotFoundError:
                try:
                    subprocess.run(['xsel', '--clipboard', '--input'], input=text.encode('utf-8'), check=True)
                except FileNotFoundError:
                    print("Clipboard tool (xclip/xsel) not found on Linux.")
    except Exception as e:
        print(f"Failed to copy to clipboard: {e}")

def ensure_ssl_certs():
    """Generates a self-signed cert valid for ALL local IPs."""
    cert_path = 'cert.crt'
    key_path = 'cert.key'
    
    if os.path.exists(cert_path): os.remove(cert_path)
    if os.path.exists(key_path): os.remove(key_path)

    print("Generating self-signed certificate with SANs for all interfaces...")
    
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    ip_addresses = get_all_ips()
    alt_names = [x509.IPAddress(ipaddress.ip_address(ip)) for ip in ip_addresses]
    alt_names.append(x509.DNSName(u"localhost"))

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Text Fetch Local Server"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        subject
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(alt_names),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
            
    return (cert_path, key_path)
