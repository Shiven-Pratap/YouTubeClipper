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

                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = data.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);

                const successMsg = document.createElement("div");
                successMsg.textContent = "✅ Download Completed!";
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


function estimateClippedSize(startTime, endTime, fullDurationSec, fullSizeMB) {
    const clipStartSec = timeStrToSeconds(startTime);
    const clipEndSec = timeStrToSeconds(endTime);
    const clipDuration = clipEndSec - clipStartSec;

    if (clipDuration <= 0 || clipStartSec < 0 || clipEndSec > fullDurationSec) {
        return "Invalid timestamps";
    }
    console.log(clipStartSec)
    console.log(clipEndSec)
    console.log(clipDuration)

    const proportion = clipDuration / fullDurationSec;
    const estimatedSize = fullSizeMB * proportion;

    console.log(proportion)
    console.log(estimatedSize)

    return estimatedSize.toFixed(2);
}////// check here cahngeeeee

    function timeStrToSeconds(timeStr) {
        const parts = timeStr.split(':').map(Number);
        if (parts.length === 3) {
            return parts[0] * 3600 + parts[1] * 60 + parts[2];
        } else if (parts.length === 2) {
            return parts[0] * 60 + parts[1];
        } else if (parts.length === 1) {
            return parts[0];
        }
        return 0;
    }





    let urlPaste = document.getElementById('url');

    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading-indicator';
        loadingDiv.style.opacity = '0';
        loadingDiv.style.transition = 'opacity 0.3s ease-in';
        loadingDiv.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <div style="border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 30px; height: 30px; animation: spin 2s linear infinite; margin: 0 auto;"></div>
            <p style="margin-top: 10px; color: #666;">Loading video data...</p>
        </div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            @keyframes slideUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .smooth-enter {
                animation: slideUp 0.5s ease-out;
            }
        </style>
    `;

        const embedPosition = document.getElementsByClassName('embed')[0];
        if (embedPosition) {
            embedPosition.innerHTML = '';
            embedPosition.appendChild(loadingDiv);

            // Fade in the loading indicator
            setTimeout(() => {
                loadingDiv.style.opacity = '1';
            }, 10);
        }
    }

    function hideLoading() {
        const loadingDiv = document.getElementById('loading-indicator');
        if (loadingDiv) {
            loadingDiv.style.transition = 'opacity 0.3s ease-out';
            loadingDiv.style.opacity = '0';
            setTimeout(() => {
                loadingDiv.remove();
            }, 300);
        }
    }

    async function fetchWithTimeout(url, options, timeout = 30000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    
    urlPaste.addEventListener('paste', function (e) {
        setTimeout(async () => {
            let input_url = urlPaste.value;
            console.log("Pasted URL:", input_url);

            const youtubeRegex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
            if (!youtubeRegex.test(input_url)) {
                alert("Please enter a valid YouTube URL.");
                setTimeout(() => {
                    location.reload();
                }, 50);
                return;
            }

            showLoading();

            try {
                let endpoint = '/api_fetch_fast';
                let response;

                try {
                    response = await fetchWithTimeout(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ url: input_url })
                    }, 10000); // 10 second timeout for fast endpoint
                } catch (fastError) {
                    console.log("Fast endpoint failed, trying regular endpoint");
                    // Fallback to regular endpoint
                    endpoint = '/api_fetch';
                    response = await fetchWithTimeout(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ url: input_url })
                    }, 30000); // 30 second timeout for regular endpoint
                }

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                if (data.error) {
                    alert("Error: " + data.error);
                    hideLoading();
                    return;
                }

                // Store global variables (keeping your original structure)
                videoID = data['VideoEmbedLink'];
                video_title = data.title;
                Channel = data.channel_title;
                published_at = data["published_at"];
                duration = data["duration"];
                view_count = data["view_count"];
                like_count = data["like_count"];
                video_size = data['filesize_by_quality'];

                // Get selected quality (assuming you have quality selection)
                const selectedCard = document.querySelector('.quality-card.selected') ||
                    document.querySelector('.quality-card[data-quality="720p"]') ||
                    document.querySelector('.quality-card');

                const current_quality_size = selectedCard ?
                    video_size[selectedCard.dataset.quality] : video_size['720p'];

                duration_in_sec = timeStrToSeconds(duration);
                let start_time = document.getElementById('startTIME').value;
                let end_time = document.getElementById('endTIME').value;

                current_size = estimateClippedSize(start_time, end_time, duration_in_sec, current_quality_size);

                // Create embed and metadata (keeping your original structure)
                embedCode = `<iframe width="370" height="250" src="${videoID}" frameborder="0"
                allowfullscreen style="border-radius: 20px;"> </iframe>`;

                metaDetaCode = `<div class="title">
                <p>${video_title.length > 35 ? video_title.substring(0, 35) + "..." : video_title}</p>
            </div>
            <div class="channel">
                <p>${Channel}</p>
            </div>
            <div class="likes">
                <span>Views : ${view_count}</span>
                <span>LikeCount : ${like_count}</span>
            </div>
            <div class="downloadSize">
                <p>${current_size}MB</p>
            </div>`;

                hideLoading();

                embedPosition = document.getElementsByClassName('data')[0];
                metaDetaPosition = document.getElementsByClassName('embed')[0];

                // Smooth simultaneous animation
                if (embedPosition && metaDetaPosition) {
                    // Set initial state - hidden
                    embedPosition.style.opacity = '0';
                    embedPosition.style.transform = 'translateY(20px)';
                    metaDetaPosition.style.opacity = '0';
                    metaDetaPosition.style.transform = 'translateY(20px)';

                    // Add CSS transitions
                    embedPosition.style.transition = 'all 0.5s ease-out';
                    metaDetaPosition.style.transition = 'all 0.5s ease-out';

                    // Set content immediately
                    embedPosition.innerHTML = metaDetaCode;
                    metaDetaPosition.innerHTML = embedCode;

                    // Trigger smooth animation after a tiny delay
                    setTimeout(() => {
                        embedPosition.style.opacity = '1';
                        embedPosition.style.transform = 'translateY(0)';
                        metaDetaPosition.style.opacity = '1';
                        metaDetaPosition.style.transform = 'translateY(0)';
                    }, 50);
                }

                
                if (data.sizes_estimated) {
                    console.log("Sizes are estimated, real sizes will be calculated in background");
                    
                }

            } catch (error) {
                console.error('Fetch error:', error);
                hideLoading();

                if (error.name === 'AbortError') {
                    alert("Request timed out. Please try again.");
                } else {
                    alert("Error loading video data: " + error.message);
                }
            }
        }, 10);
    });

    function timeStrToSeconds(timeStr) {
        if (!timeStr) return 0;
        const parts = timeStr.split(':').map(Number);
        if (parts.length === 3) {
            return parts[0] * 3600 + parts[1] * 60 + parts[2];
        } else if (parts.length === 2) {
            return parts[0] * 60 + parts[1];
        }
        return parts[0] || 0;
    }

    function estimateClippedSize(start_time, end_time, duration_in_sec, current_quality_size) {
        if (!start_time || !end_time || !duration_in_sec || !current_quality_size) {
            return current_quality_size || 0;
        }

        const startSec = timeStrToSeconds(start_time);
        const endSec = timeStrToSeconds(end_time);

        if (startSec >= endSec) return current_quality_size;

        const clipDuration = endSec - startSec;
        const ratio = clipDuration / duration_in_sec;

        return Math.round(current_quality_size * ratio * 100) / 100;
    }

    let typingTimer;
    urlPaste.addEventListener('input', function () {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            const url = urlPaste.value.trim();
            const youtubeRegex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
            if (youtubeRegex.test(url)) {
                const link = document.createElement('link');
                link.rel = 'dns-prefetch';
                link.href = '//www.youtube.com';
                document.head.appendChild(link);
            }
        }, 1000);
    });

    function logout() {
            if (confirm('Are you sure you want to logout?')) {
                window.location.href = '/logout';
            }
        }