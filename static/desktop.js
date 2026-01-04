var qrcode = new QRCode(document.getElementById("qrcode"), {
    width: 220,
    height: 220,
    colorDark : "#000000",
    colorLight : "#ffffff",
    correctLevel : QRCode.CorrectLevel.H
});

function updateQR() {
    var ip = document.getElementById('networkSelect').value;
    if (!ip) return;
    
    // 'protocol' and 'serverPort' variables must be defined in the HTML before this script runs
    var mobileUrl = protocol + "://" + ip + ":" + serverPort + "/mobile";
    document.getElementById('urlDisplay').innerText = mobileUrl;
    
    qrcode.clear();
    qrcode.makeCode(mobileUrl);
}

// Initial setup
updateQR();
document.getElementById('networkSelect').addEventListener('change', updateQR);

function pollForContent() {
    fetch('/poll')
        .then(response => response.json())
        .then(data => {
            if (data.received) {
                document.getElementById('scan-section').style.display = 'none';
                document.getElementById('interface-selector').style.display = 'none';
                document.querySelector('.warning')?.remove();
                document.querySelector('h1').innerText = "Text Received";
                
                const contentDiv = document.getElementById('receivedContent');
                contentDiv.style.display = 'block';
                document.getElementById('textContentDisplay').innerText = data.content;
                return;
            }
            setTimeout(pollForContent, 1000);
        })
        .catch(err => {
            console.error("Polling error:", err);
            setTimeout(pollForContent, 2000);
        });
}
pollForContent();

// Reset functionality
document.getElementById('resetBtn').addEventListener('click', () => {
    fetch('/reset', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'reset') {
                // Reset UI
                document.getElementById('receivedContent').style.display = 'none';
                document.getElementById('scan-section').style.display = 'block';
                document.getElementById('interface-selector').style.display = 'block';
                document.querySelector('h1').innerText = "Text Fetch";
                
                // Restart polling
                pollForContent();
            }
        });
});
