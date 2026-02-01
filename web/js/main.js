let rowCount = 0;
let activeTargetId = null; 
let activeRowForPin = null;
let pinMode = null; // 'SET', 'CONFIRM', 'VERIFY'
let tempPin = null;

document.addEventListener('DOMContentLoaded', async () => {
    const storedData = await eel.get_initial_state()();
    const storedKeys = Object.keys(storedData).filter(k => k !== '__SETTINGS__').sort((a, b) => parseInt(a) - parseInt(b));
    
    if (storedKeys.length > 0) {
        for (const key of storedKeys) {
            const data = storedData[key];
            const id = parseInt(key);
            if (id >= rowCount) rowCount = id + 1;
            renderRow(id, data.text, data.is_password, data.shortcut);
        }
        while (document.getElementsByClassName('row-card').length < 3) {
            addRow(false);
        }
    } else {
        for (let i = 0; i < 5; i++) {
            addRow(false); 
        }
    }
    
    const modalEl = document.getElementById('qrModal');
    modalEl.addEventListener('hidden.bs.modal', () => {
        eel.cancel_fetch_session();
    });

    // PIN Modal Logic
    setupPinInputs();
    
    // Action Modal Logic
    document.getElementById('btnTempView').addEventListener('click', () => handleAction('TEMP'));
    document.getElementById('btnPermRemove').addEventListener('click', () => handleAction('PERM'));
    
    // Auto-focus PIN input when modal opens
    const pinModalEl = document.getElementById('pinModal');
    pinModalEl.addEventListener('shown.bs.modal', () => {
        const firstInput = document.querySelector('.pin-digit');
        if (firstInput) firstInput.focus();
    });
});

function setupPinInputs() {
    const inputs = document.querySelectorAll('.pin-digit');
    
    inputs.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            if (e.inputType === 'insertText' && e.data) {
                // Move to next
                if (index < 3) {
                    inputs[index + 1].focus();
                } else {
                    // Last digit entered, submit
                    input.blur(); // Remove focus
                    handlePinSubmit();
                }
            }
        });
        
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
            if (e.key === 'Enter') {
                handlePinSubmit();
            }
        });
        
        // Prevent non-numeric input
        input.addEventListener('keypress', (e) => {
            if (!/[0-9]/.test(e.key)) {
                e.preventDefault();
            }
        });
        
        // Handle paste
        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = e.clipboardData.getData('text').slice(0, 4).replace(/[^0-9]/g, '');
            if (pasteData) {
                pasteData.split('').forEach((char, i) => {
                    if (index + i < 4) {
                        inputs[index + i].value = char;
                    }
                });
                if (index + pasteData.length >= 4) {
                    inputs[3].blur();
                    handlePinSubmit();
                } else {
                    inputs[index + pasteData.length].focus();
                }
            }
        });
    });
}

function getPinValue() {
    const inputs = document.querySelectorAll('.pin-digit');
    let pin = '';
    inputs.forEach(input => pin += input.value);
    return pin;
}

function clearPinInputs() {
    const inputs = document.querySelectorAll('.pin-digit');
    inputs.forEach(input => input.value = '');
    inputs[0].focus();
}

function renderRow(id, text = '', isPassword = false, shortcut = '') {
    const container = document.getElementById('rows-container');
    
    const rowHtml = `
        <div class="row-card" id="row-${id}">
            <div class="form-check form-switch" title="Toggle Password Mode">
                <input class="form-check-input" type="checkbox" id="chk-${id}" onclick="handleToggleClick(event, ${id})" ${isPassword ? 'checked' : ''}>
            </div>
            
            <input type="${isPassword ? 'password' : 'text'}" class="form-control text-input" id="text-${id}" placeholder="Enter text to paste..." value="${text}" oninput="saveRow(${id})">
            
            <div class="shortcut-wrapper">
                <input type="text" class="form-control shortcut-input" id="shortcut-${id}" placeholder="Shortcut" value="${shortcut}" title="${shortcut}" onkeydown="captureShortcut(event, ${id})" onblur="saveRow(${id})" readonly>
                <button class="btn-clear-shortcut" onclick="clearShortcut(${id})" title="Clear Shortcut">
                    <i class="bi bi-x-circle-fill"></i>
                </button>
            </div>
            
            <button class="btn btn-fetch" onclick="openFetchModal(${id})" title="Fetch from Mobile">
                <i class="bi bi-phone"></i>
            </button>
            
            <button class="btn btn-outline-danger btn-sm ms-2" onclick="deleteRow(${id})" title="Delete Row">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', rowHtml);
}

function addRow(animate = true) {
    const id = rowCount++;
    renderRow(id);
    saveRow(id);
    
    if (animate) {
        const newRow = document.getElementById(`row-${id}`);
        newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function deleteRow(id) {
    const container = document.getElementById('rows-container');
    const currentRows = container.getElementsByClassName('row-card').length;
    
    if (currentRows <= 3) {
        const toastEl = document.getElementById('errorToast');
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        return;
    }
    
    const row = document.getElementById(`row-${id}`);
    row.remove();
    
    eel.delete_row_data(id);
}

function resetApp() {
    if (confirm("Are you sure you want to reset the application? This will delete all stored data.")) {
        eel.reset_application()().then(() => {
            location.reload();
        });
    }
}

function reloadHotkeys() {
    eel.reload_hotkeys();
    alert("Hotkeys reloaded.");
}

// --- PIN Logic ---

async function handleToggleClick(event, id) {
    const checkbox = event.target;
    const isTurningOn = checkbox.checked; 
    
    event.preventDefault();
    checkbox.checked = !isTurningOn; 
    
    activeRowForPin = id;
    
    if (isTurningOn) {
        const hasPin = await eel.check_pin_exists()();
        if (hasPin) {
            checkbox.checked = true;
            document.getElementById(`text-${id}`).type = "password";
            saveRow(id);
        } else {
            openPinModal('SET');
        }
    } else {
        openPinModal('VERIFY');
    }
}

function updatePinModalUI(mode) {
    pinMode = mode;
    const title = document.getElementById('pinModalTitle');
    const msg = document.getElementById('pinModalMsg');
    const error = document.getElementById('pinError');
    const success = document.getElementById('pinSuccess');
    
    clearPinInputs();
    error.style.display = 'none';
    success.style.display = 'none';
    
    if (mode === 'SET') {
        title.innerText = "Set Master PIN";
        msg.innerText = "Create a 4-digit PIN for all password fields.";
    } else if (mode === 'CONFIRM') {
        title.innerText = "Confirm PIN";
        msg.innerText = "Re-enter to confirm.";
    } else {
        title.innerText = "Enter PIN";
        msg.innerText = "Enter PIN to unlock.";
    }
}

function openPinModal(mode) {
    tempPin = null;
    updatePinModalUI(mode);
    
    const modalEl = document.getElementById('pinModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

async function handlePinSubmit() {
    const error = document.getElementById('pinError');
    const success = document.getElementById('pinSuccess');
    const pin = getPinValue();
    
    if (pin.length !== 4 || isNaN(pin)) {
        error.innerText = "Enter 4 digits.";
        error.style.display = 'block';
        return;
    }
    
    const modalEl = document.getElementById('pinModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    
    if (pinMode === 'SET') {
        tempPin = pin;
        updatePinModalUI('CONFIRM');
        
    } else if (pinMode === 'CONFIRM') {
        if (pin === tempPin) {
            await eel.set_app_pin(pin)();
            
            document.getElementById('pinInputsContainer').style.display = 'none'; 
            success.style.display = 'block';
            
            setTimeout(() => {
                modal.hide();
                document.getElementById('pinInputsContainer').style.display = 'flex';
                success.style.display = 'none';
                
                const checkbox = document.getElementById(`chk-${activeRowForPin}`);
                checkbox.checked = true;
                document.getElementById(`text-${activeRowForPin}`).type = "password";
                saveRow(activeRowForPin);
            }, 1000);
            
        } else {
            error.innerText = "PINs do not match. Restarting...";
            error.style.display = 'block';
            
            setTimeout(() => {
                tempPin = null;
                updatePinModalUI('SET');
            }, 1500);
        }
        
    } else if (pinMode === 'VERIFY') {
        const isValid = await eel.verify_app_pin(pin)();
        if (isValid) {
            modal.hide();
            const actionModal = new bootstrap.Modal(document.getElementById('actionModal'));
            actionModal.show();
        } else {
            error.innerText = "Incorrect PIN.";
            error.style.display = 'block';
            clearPinInputs();
        }
    }
}

function handleAction(type) {
    const modalEl = document.getElementById('actionModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();
    
    const id = activeRowForPin;
    const checkbox = document.getElementById(`chk-${id}`);
    const input = document.getElementById(`text-${id}`);
    
    if (type === 'TEMP') {
        checkbox.checked = false;
        input.type = "text";
    } else {
        checkbox.checked = false;
        input.type = "text";
        saveRow(id);
    }
}

// --- End PIN Logic ---

function captureShortcut(event, id) {
    event.preventDefault();
    const keys = [];
    if (event.ctrlKey) keys.push('ctrl');
    if (event.altKey) keys.push('alt');
    if (event.shiftKey) keys.push('shift');
    
    if (!['Control', 'Alt', 'Shift'].includes(event.key)) {
        keys.push(event.key.toLowerCase());
    }
    
    if (keys.length > 0) {
        const shortcut = keys.join('+');
        const input = document.getElementById(`shortcut-${id}`);
        input.value = shortcut;
        input.title = shortcut;
        saveRow(id); 
    }
}

function clearShortcut(id) {
    const input = document.getElementById(`shortcut-${id}`);
    input.value = '';
    input.title = '';
    saveRow(id);
}

function saveRow(id) {
    const text = document.getElementById(`text-${id}`).value;
    const isPassword = document.getElementById(`chk-${id}`).checked;
    const shortcut = document.getElementById(`shortcut-${id}`).value;
    
    eel.save_row_data(id, text, isPassword, shortcut);
}

async function openFetchModal(targetId) {
    activeTargetId = targetId;
    const modal = new bootstrap.Modal(document.getElementById('qrModal'));
    modal.show();
    
    document.getElementById('qrcode').innerHTML = '<div class="spinner-border text-primary" role="status"></div>';
    document.getElementById('status-msg').style.display = 'none';
    document.getElementById('urlDisplay').innerText = '';
    
    const interfaces = await eel.get_interfaces()();
    const select = document.getElementById('networkSelect');
    select.innerHTML = '';
    
    interfaces.forEach(iface => {
        const option = document.createElement('option');
        option.value = iface.ip;
        option.text = iface.name;
        select.appendChild(option);
    });
    
    updateQR();
}

async function updateQR() {
    const ip = document.getElementById('networkSelect').value;
    if (!ip || activeTargetId === null) return;
    
    const qrContainer = document.getElementById('qrcode');
    qrContainer.innerHTML = '<div class="spinner-border text-primary" role="status"></div>';
    
    const data = await eel.generate_qr(activeTargetId, ip)();
    
    qrContainer.innerHTML = '';
    const img = document.createElement('img');
    img.src = data.qr_image;
    img.style.display = 'block';
    qrContainer.appendChild(img);
    
    document.getElementById('urlDisplay').innerText = data.url;
}

eel.expose(update_row_text);
function update_row_text(rowId, text) {
    const input = document.getElementById(`text-${rowId}`);
    if (input) {
        input.value = text;
        saveRow(rowId);
        showSuccess();
    }
}

eel.expose(on_clipboard_received);
function on_clipboard_received() {
    showSuccess();
}

function showSuccess() {
    const statusMsg = document.getElementById('status-msg');
    if (statusMsg) {
        statusMsg.style.display = 'block';
        setTimeout(() => {
            const modalEl = document.getElementById('qrModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }, 1500);
    }
}
