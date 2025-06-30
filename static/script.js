const qualityContainer = document.querySelector('.quality-cards');
let selectedCard = document.querySelector('.quality-card.selected'); // Default is 720p

qualityContainer.addEventListener('click', function (e) {
    const target = e.target;

    if (target.classList.contains('quality-card')) {
        if (target !== selectedCard) {
            selectedCard.classList.remove('selected');  // Remove from old
            target.classList.add('selected');           // Add to new
            selectedCard = target;                      // Update reference
        }
    }
});

let btn = document.getElementsByClassName('btn')[0]

btn.addEventListener('click', function (e) {
    let url = document.getElementById('url').value
    let startTime = document.getElementById('startTIME').value
    let endTime = document.getElementById('endTIME').value
    const selectedQualityValue = selectedCard.dataset.quality;

    if (!url || !startTime || !endTime || !selectedQualityValue) {
        alert("All fields are required.");
        return;
    }

    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w\-]{11}/;
    if (!youtubeRegex.test(url)) {
        alert("Please enter a valid YouTube URL.");
        return;
    }

    const timeRegex = /^\d+:[0-5]\d:[0-5]\d$/;

    if (!timeRegex.test(startTime)) {
        alert("Start time must be in the format HH:MM:SS");
        return;
    }
    if (!timeRegex.test(endTime)) {
        alert("End time must be in the format HH:MM:SS");
        return;
    }

    const toSeconds = t => {
        const [h, m, s] = t.split(':').map(Number);
        return h * 3600 + m * 60 + s;
    };

    if (toSeconds(startTime) >= toSeconds(endTime)) {
        alert("Start time must be before end time.");
        return;
    }

    console.log("URL:", url);
    console.log("Start:", startTime);
    console.log("End:", endTime);
    console.log("Quality:", selectedQualityValue);


    // btn.disabled = true;
    // btn.textContent = "⏳ Downloading...";


btn.disabled = true;
            document.getElementById('btnText').textContent = "⏳ Downloading...";
            document.getElementById("spinner").style.display = "inline-block";


    fetch('/process', {

        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: url,
            startTime: startTime,
            endTime: endTime,
            quality: selectedQualityValue
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.filename) {
                const downloadUrl = `/download/${data.filename}`;

                // Create invisible link and trigger it
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = data.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);

                // Optional: show message
                const successMsg = document.createElement("div");
                successMsg.textContent = "✅ Download started!";
                successMsg.style.position = "fixed";
                successMsg.style.top = "20px";
                successMsg.style.left = "50%";
                successMsg.style.transform = "translateX(-50%)";
                successMsg.style.backgroundColor = "#4CAF50";
                successMsg.style.color = "white";
                successMsg.style.padding = "12px 24px";
                successMsg.style.borderRadius = "8px";
                successMsg.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
                document.body.appendChild(successMsg);

                setTimeout(() => {
                    successMsg.style.opacity = "0";
                }, 1500);
                setTimeout(() => {
                    location.reload();
                }, 3000);
            } else {
                alert("Something went wrong.");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("Something went wrong while sending data.");
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = "Download";
            document.getElementById("spinner").style.display = "none";

        });

});
