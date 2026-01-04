import ifaddr
import re
import platform
import subprocess
import os
import webbrowser
import sys

def get_network_interfaces():
    """Returns a list of dicts with 'name' and 'ip' for valid interfaces."""
    network_adapters = ifaddr.get_adapters()
    interfaces = []
    
    for adapter in network_adapters:
        for ip in adapter.ips:
            ip_str = str(ip.ip)
            # IPv4 regex check
            if re.match(r"^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$", ip_str):
                # Exclude localhost and APIPA (169.254.x.x)
                if ip_str == "127.0.0.1" or ip_str.startswith("169.254"):
                    continue
                
                interfaces.append({
                    'name': f"{adapter.nice_name} ({ip_str})",
                    'ip': ip_str
                })
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
    """Generates self-signed certs if they don't exist."""
    cert_path = 'cert.crt'
    key_path = 'cert.key'
    
    # Check if cryptography is installed
    try:
        import cryptography
    except ImportError:
        print("\n" + "="*60)
        print("WARNING: 'cryptography' library is missing.")
        print("Cannot generate SSL certificates for HTTPS.")
        print("Please run: pip install cryptography")
        print("Falling back to HTTP mode (Clipboard auto-paste might not work).")
        print("="*60 + "\n")
        return None

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("Generating self-signed certificates...")
        try:
            from werkzeug.serving import make_ssl_devcert
            # This generates cert.crt and cert.key
            make_ssl_devcert('cert', host='localhost')
        except Exception as e:
            print(f"Error generating certs: {e}")
            return None
            
    return (cert_path, key_path)

def open_browser(protocol, port):
    url = f'{protocol}://127.0.0.1:{port}/'
    print(f"Attempting to open browser at {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Error opening browser: {e}")

def print_server_info(protocol, port):
    print(f'Starting server on {protocol} protocol with port: {port}...')
    print('Available interfaces:')
    network_adapters = ifaddr.get_adapters()
    for adapter in network_adapters:
        for ip in adapter.ips:
            ip_str = str(ip.ip)
            if re.match(r"^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$", ip_str):
                print(f'• {protocol}://{ip_str}:{port} \tof "{adapter.nice_name}"')
            
    print('\n** (Press CTRL+C) to stop screen share')
