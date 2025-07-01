from flask import Flask, render_template,request,jsonify,send_from_directory,after_this_request
import yt_dlp
import uuid
import os
import threading
import time
from urllib.parse import urlparse, parse_qs
import requests
from datetime import datetime

API_KEY = "AIzaSyD4vh70NXpfqTORTo9VZ8qKr9EB-lSEoSs"


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

def time_to_seconds(time_str):
    """Convert time string (HH:MM:SS or MM:SS) to seconds"""
    parts = time_str.split(':')
    if len(parts) == 3: 
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:  
        return int(parts[0]) * 60 + int(parts[1])
    else:  
        return int(parts[0])


def download_video(url, start_time, end_time, quality='best', output_path='downloads'):
    filename_token = uuid.uuid4().hex[:8]  # unique part
    outtmpl = f'{output_path}/video_{filename_token}.%(ext)s'

    quality_map = {
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
        'best': 'bestvideo+bestaudio/best'
    }
    
    selected_format = quality_map.get(quality, 'bestvideo+bestaudio/best')
    
    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    
    ydl_opts = {
        'format': selected_format,
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'download_ranges': yt_dlp.utils.download_range_func(None, [(start_seconds, end_seconds)]),
        'force_keyframes_at_cuts': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    for file in os.listdir(output_path):
        if filename_token in file:
            return file
    return None


@app.route("/process",methods=['Post'])
def process():
    data = request.get_json()

    url=data['url']
    startTime=data['startTime']
    endTime= data['endTime']
    quality=data['quality']

    try:
        filename = download_video(url, startTime, endTime, quality)
        if filename:
            return jsonify({"message": "✅ Video trimmed and ready!", "filename": filename})
        else:
            return jsonify({"message": "❌ Failed to find output file."}), 500
    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "❌ Failed to download video."}), 500


@app.route("/download/<filename>")
def download_file(filename):
    # Security: prevent directory traversal
    if '..' in filename or '/' in filename:
        return jsonify({"message": "Invalid filename"}), 400
    
    file_path = os.path.join("downloads", filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        return jsonify({"message": "File not found"}), 404
    
    def delayed_cleanup():
        time.sleep(5)  # Wait 5 seconds for download to complete
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File {filename} deleted successfully")
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=delayed_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    return send_from_directory("downloads", filename, as_attachment=True)


#-----------------------------------------------------

def extract_video_id(url):
    parsed = urlparse(url)
    
    if parsed.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed.path == '/watch':
            return parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.path.startswith('/shorts/'):
            return parsed.path.split('/')[2]
    
    elif parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    
    return None

def parse_duration(duration):
    duration = duration.replace('PT', '')
    hours = minutes = seconds = 0
    
    if 'H' in duration:
        hours = int(duration.split('H')[0])
        duration = duration.split('H')[1]
    if 'M' in duration:
        minutes = int(duration.split('M')[0])
        duration = duration.split('M')[1]
    if 'S' in duration:
        seconds = int(duration.replace('S', ''))
    
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def duration_to_seconds(duration):
    """
    Convert PT4M13S format to total seconds
    """
    duration = duration.replace('PT', '')
    total_seconds = 0
    
    if 'H' in duration:
        hours = int(duration.split('H')[0])
        total_seconds += hours * 3600
        duration = duration.split('H')[1]
    if 'M' in duration:
        minutes = int(duration.split('M')[0])
        total_seconds += minutes * 60
        duration = duration.split('M')[1]
    if 'S' in duration:
        seconds = int(duration.replace('S', ''))
        total_seconds += seconds
    
    return total_seconds

def format_video_details(video_data):
    """
    Format the video data into a readable structure
    """
    snippet = video_data.get('snippet', {})
    statistics = video_data.get('statistics', {})
    content_details = video_data.get('contentDetails', {})
    status = video_data.get('status', {})
    
    # Parse duration (PT4M13S format to readable)
    duration = content_details.get('duration', 'N/A')
    if duration != 'N/A':
        duration = parse_duration(duration)
    
    # Parse published date
    published_at = snippet.get('publishedAt', '')
    if published_at:
        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Determine if it's a Short (duration <= 60 seconds)
    is_short = False
    if content_details.get('duration'):
        duration_seconds = duration_to_seconds(content_details.get('duration'))
        is_short = duration_seconds <= 60
    
    details = {
        "video_id": video_data.get('id'),
        "title": snippet.get('title', 'N/A'),
        "description": snippet.get('description', 'N/A')[:500] + "..." if len(snippet.get('description', '')) > 500 else snippet.get('description', 'N/A'),
        "channel_title": snippet.get('channelTitle', 'N/A'),
        "channel_id": snippet.get('channelId', 'N/A'),
        "published_at": published_at,
        "duration": duration,
        "is_youtube_short": is_short,
        "view_count": int(statistics.get('viewCount', 0)),
        "like_count": int(statistics.get('likeCount', 0)),
        "comment_count": int(statistics.get('commentCount', 0)),
        "privacy_status": status.get('privacyStatus', 'N/A'),
        "upload_status": status.get('uploadStatus', 'N/A'),
        "tags": snippet.get('tags', []),
        "category_id": snippet.get('categoryId', 'N/A'),
        "default_language": snippet.get('defaultLanguage', 'N/A'),
        "thumbnail_url": snippet.get('thumbnails', {}).get('high', {}).get('url', 'N/A')
    }
    
    return details

def get_video_details(api_key, video_id):
    """
    Fetch comprehensive video details from YouTube API
    """
    base_url = "https://www.googleapis.com/youtube/v3/videos"
    
    # Clean the video ID
    clean_video_id = video_id
    
    # API parameters
    params = {
        'part': 'snippet,statistics,contentDetails,status',
        'id': clean_video_id,
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('items'):
            return {"error": "Video not found or private/deleted"}
        
        video = data['items'][0]
        return format_video_details(video)
        
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# def print_video_details(details):
#     """
#     Print video details in a formatted way
#     """
#     if "error" in details:
#         print(f"❌ Error: {details['error']}")
#         return
    
#     print("=" * 60)
#     print("🎥 YOUTUBE VIDEO DETAILS")
#     print("=" * 60)
#     print(f"📝 Title: {details['title']}")
#     print(f"🆔 Video ID: {details['video_id']}")
#     print(f"📺 Channel: {details['channel_title']}")
#     print(f"📅 Published: {details['published_at']}")
#     print(f"⏱️  Duration: {details['duration']}")
#     print(f"🩳 YouTube Short: {'Yes' if details['is_youtube_short'] else 'No'}")
#     print(f"👀 Views: {details['view_count']:,}")
#     print(f"👍 Likes: {details['like_count']:,}")
#     print(f"💬 Comments: {details['comment_count']:,}")
#     print(f"🔒 Privacy: {details['privacy_status']}")
#     print(f"🏷️  Tags: {', '.join(details['tags'][:5])}{'...' if len(details['tags']) > 5 else ''}")
#     print(f"📖 Description: {details['description']}")
#     print(f"🖼️  Thumbnail: {details['thumbnail_url']}")
#     print("=" * 60)


@app.route("/api_fetch",methods=['Post'])
def metaDeta():
    data=request.get_json()
    url=data['url']
    VIDEO_ID = extract_video_id(url)
    details = get_video_details(API_KEY, VIDEO_ID)
    if "error" in details:
        return {"error": details["error"]}
    

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forcejson': True,
    }

    sizes = {
        "360p": None,
        "480p": None,
        "720p": None,
        "1080p": None
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        for f in info['formats']:
            fmt_note = f.get('format_note', '').lower()
            height = f.get('height')
            filesize = f.get('filesize')

            if filesize and height:
                if height == 360 and sizes["360p"] is None:
                    sizes["360p"] = round(filesize / (1024 * 1024), 2)
                elif height == 480 and sizes["480p"] is None:
                    sizes["480p"] = round(filesize / (1024 * 1024), 2)
                elif height == 720 and sizes["720p"] is None:
                    sizes["720p"] = round(filesize / (1024 * 1024), 2)
                elif height == 1080 and sizes["1080p"] is None:
                    sizes["1080p"] = round(filesize / (1024 * 1024), 2)

    except Exception as e:
        print("yt-dlp failed:", e)

    return {
        "title": details["title"],
        "video_id": details["video_id"],
        "channel_title": details["channel_title"],
        "published_at": details["published_at"],
        "duration": details["duration"],
        "is_youtube_short": details["is_youtube_short"],
        "view_count": details["view_count"],
        "like_count": details["like_count"],
        "comment_count": details["comment_count"],
        "privacy_status": details["privacy_status"],
        "tags": details["tags"][:5],  # Send top 5 tags
        "description": details["description"],
        "thumbnail_url": details["thumbnail_url"],
        "VideoID": f"https://www.youtube.com/embed/{VIDEO_ID}",
        "filesize_by_quality": sizes
    }
    




app.run(debug=True)