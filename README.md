# Text Organizer & Fetcher

A powerful, cross-platform desktop application to organize frequently used text snippets, assign global hotkeys, and securely fetch text from your mobile device's clipboard.

This tool is targeted to be used on laptops/devices where cloud clipboard services are either not available or are blocked 


## 🚀 Key Features

### 🖥️ Desktop Text Organizer
*   **5+ Dynamic Rows:** Store frequently used text (emails, code snippets, templates).
*   **Global Hotkeys:** Assign custom shortcuts (e.g., `Ctrl+Shift+1`) to auto-type text into *any* active application.
*   **Password Mode:** Toggle visibility for sensitive data.
*   **Secure PIN Protection:** Set a master PIN to lock/unlock password fields.
*   **Encrypted Storage:** All data is AES-256 encrypted and bound to your specific machine hardware.

### 📱 Mobile Text Fetch
*   **Seamless Transfer:** Scan a QR code to instantly send text from your phone's clipboard to the desktop app.
*   **Direct to Clipboard:** Option to fetch text directly to your computer's clipboard without saving it to a row.
*   **Secure Connection:** Uses a local HTTPS server with self-signed certificates to ensure secure transfer.
*   **One-Time Sessions:** Each QR code is valid for a single use only, preventing replay attacks.

### 🛡️ Security & Privacy
*   **Local Only:** No cloud servers. All data stays on your local network and machine.
*   **Hardware Binding:** Encrypted data file which cannot be decrypted if copied to another computer.
*   **Smart Typing:** Password fields are typed out character-by-character to avoid clipboard history leaks.

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.8+
*   A mobile device on the same Wi-Fi network.

### 1. Clone the Repository
```bash
git clone git@github.com:idaljeetsingh/text-organizer.git
cd text-organizer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```


## ▶️ Usage

### Running the App
```bash
python main.py
```
This will launch the desktop interface.

### Using Hotkeys
1.  Enter text in a row.
2.  Click the "Shortcut" box and press your desired key combination (e.g., `Alt+Shift+T`).
3.  Switch to any other app (Notepad, Browser, etc.).
4.  Press the shortcut to auto-type the text.

### Fetching from Mobile
1.  Click the **Phone Icon** next to a row (or "Clipboard" button at the bottom).
2.  Scan the QR code with your phone's camera.
3.  Open the link (accept the "Self-Signed Certificate" warning if prompted).
4.  Tap the text box on your phone to paste your clipboard content.
5.  Tap **Send**. The text will instantly appear in the desktop app.

### PIN Protection
1.  Click the **Toggle Switch** on a row to enable Password Mode.
2.  On first use, you will be prompted to set a **4-digit Master PIN**.
3.  To view the password later or remove protection, you must enter this PIN.

## 🔧 Troubleshooting

*   **"Site can't be reached" on Mobile:** Ensure your phone and computer are on the same Wi-Fi network. Check if your firewall is blocking port `8001`.
*   **Hotkeys stopped working:** Click the **Settings (Gear Icon) -> Reload Hotkeys** to refresh the keyboard hooks.
*   **Garbage text when typing:** The app tries to release modifier keys automatically. If issues persist, try releasing keys faster after pressing the shortcut.

## 🏗️ Tech Stack
*   **Frontend:** HTML5, Bootstrap 5, JavaScript (Eel).
*   **Backend:** Python (Eel, Bottle, CherryPy).
*   **Automation:** PyAutoGUI, Keyboard.
*   **Security:** Cryptography (Fernet/AES), Self-Signed SSL.

## Author

Daljeet Singh Chhabra

## 📄 License
MIT License
