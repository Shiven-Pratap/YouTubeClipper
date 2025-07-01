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

  return estimatedSize.toFixed(2); // size in MB
}

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


let urlPaste = document.getElementById('url')
urlPaste.addEventListener('paste', function (e) {
    setTimeout(() => {
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
        fetch('/api_fetch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: input_url })  // from pasted input
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                    return;
                }

                videoID = data['VideoID']
                video_title = data.title;
                Channel = data.channel_title;
                published_at = data["published_at"]
                duration = data["duration"]
                view_count = data["view_count"]
                like_count = data["like_count"]
                video_size = data['filesize_by_quality']

                const current_quality_size=video_size[selectedCard.dataset.quality]
                
                duration_in_sec=timeStrToSeconds(duration)
                let start_time=document.getElementById('startTIME').value
                let end_time=document.getElementById('endTIME').value

                current_size = estimateClippedSize(start_time,end_time,duration_in_sec,current_quality_size,)              


                embedCode = `<iframe width="370" height="250" src="${videoID}" frameborder="0"
                    allowfullscreen style="border-radius: 20px;"> </iframe>`

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
                </div>`

                
                embedPosition=document.getElementsByClassName('data')[0]
                metaDetaPosition=document.getElementsByClassName('embed')[0]

                setTimeout(() => {
                    embedPosition.innerHTML = metaDetaCode
                metaDetaPosition.innerHTML = embedCode
                }, 1);
                
                

                // console.log("is_youtube_short", data["is_youtube_short"],)
                // console.log("comment_count", data["comment_count"])
                // console.log("privacy_status", data["privacy_status"])
                // console.log("tags", data["tags"])
                // console.log("description", data["description"])
                // console.log("thumbnail_url", data["thumbnail_url"])

            });

    }, 10);

});

