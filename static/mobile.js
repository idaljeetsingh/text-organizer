const textContent = document.getElementById('textContent');
const sendBtn = document.getElementById('sendBtn');

async function sendData(text) {
    if (!text) {
        alert("Please enter some text.");
        return;
    }
    
    sendBtn.disabled = true;
    sendBtn.innerText = "Sending...";
    
    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: text }),
        });

        if (response.ok) {
            document.getElementById('mainContainer').style.display = 'none';
            document.getElementById('successContainer').style.display = 'flex';
        } else {
            alert('Failed to send text.');
            sendBtn.disabled = false;
            sendBtn.innerText = "Send Text";
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to send text. Check network connection.');
        sendBtn.disabled = false;
        sendBtn.innerText = "Send Text";
    }
}

function enableManualMode() {
    textContent.readOnly = false;
    textContent.placeholder = "Type or paste here...";
    textContent.style.borderStyle = "solid"; 
    textContent.style.borderColor = "#007bff";
    sendBtn.style.display = "block";
    
    textContent.blur(); 
    setTimeout(() => {
        textContent.focus(); 
    }, 50); 
}

let isProcessing = false;

const handleInteraction = (e) => {
    if (isProcessing) return;
    if (!textContent.readOnly) return; 

    isProcessing = true;
    
    enableManualMode();

    navigator.clipboard.readText()
        .then(text => {
            if (text && text.trim().length > 0) {
                textContent.value = text;
                sendData(text);
            } else {
                console.log("Clipboard empty.");
            }
            isProcessing = false;
        })
        .catch(err => {
            console.warn('Auto-paste failed:', err);
            isProcessing = false;
        });
};

textContent.addEventListener('click', handleInteraction);

sendBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    sendData(textContent.value);
});
