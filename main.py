from flask import Flask, render_template,request,jsonify,send_from_directory,after_this_request,redirect, session, url_for
import yt_dlp
import uuid
import os
import threading
import time
from urllib.parse import urlparse, parse_qs
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

app = Flask(__name__)


API_KEY = os.environ.get("API_KEY")
app.secret_key = os.environ.get("SECRET_KEY")

cookies_content = os.environ.get("COOKIES_TXT")
if cookies_content:
    with open("cookies.txt", "w", encoding="utf-8") as f:
        f.write(cookies_content)





@app.route("/")
def home():
    # return render_template("index.html")
    if 'logged_in' in session and session['logged_in']:
        user_name = session.get('user_name')
        return render_template("index.html", logged_in=True, user_name=user_name)
    else:
        return render_template("index.html", logged_in=False)

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
        'cookiefile': 'cookies.txt', 
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

def print_video_details(details):
    """
    Print video details in a formatted way
    """
    if "error" in details:
        print(f"❌ Error: {details['error']}")
        return
    
    print("=" * 60)
    print("🎥 YOUTUBE VIDEO DETAILS")
    print("=" * 60)
    print(f"📝 Title: {details['title']}")
    print(f"🆔 Video ID: {details['video_id']}")
    print(f"📺 Channel: {details['channel_title']}")
    print(f"📅 Published: {details['published_at']}")
    print(f"⏱️  Duration: {details['duration']}")
    print(f"🩳 YouTube Short: {'Yes' if details['is_youtube_short'] else 'No'}")
    print(f"👀 Views: {details['view_count']:,}")
    print(f"👍 Likes: {details['like_count']:,}")
    print(f"💬 Comments: {details['comment_count']:,}")
    print(f"🔒 Privacy: {details['privacy_status']}")
    print(f"🏷️  Tags: {', '.join(details['tags'][:5])}{'...' if len(details['tags']) > 5 else ''}")
    print(f"📖 Description: {details['description']}")
    print(f"🖼️  Thumbnail: {details['thumbnail_url']}")
    print("=" * 60)


video_cache = {}
cache_timeout = 300  

executor = ThreadPoolExecutor(max_workers=3)


def get_basic_info_fast(url):
    """Get basic video info quickly without format details"""
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forcejson': True,
        'noplaylist': True,
        'extract_flat': False,
        'no_warnings': True,
        'ignoreerrors': True,
        'cookiefile': 'cookies.txt',
        # Speed optimizations
        'socket_timeout': 10,
        'retries': 1,
        'fragment_retries': 1,
        'skip_unavailable_fragments': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info
    except Exception as e:
        print(f"Fast info extraction failed: {e}")
        return None

def get_format_sizes_optimized(info):
    """Optimized format size extraction"""
    sizes = {
        "360p": None,
        "480p": None,
        "720p": None,
        "1080p": None
    }
    
    if not info or 'formats' not in info:
        return {"360p": 25, "480p": 40, "720p": 75, "1080p": 150}  # Default fallback
    
    # Process only the first few formats that match our criteria
    processed_count = 0
    for f in info['formats']:
        if processed_count >= 10:  # Limit processing to first 10 relevant formats
            break
            
        height = f.get('height')
        filesize = f.get('filesize') or f.get('filesize_approx')
        
        if filesize and height and height in [360, 480, 720, 1080]:
            quality_key = f"{height}p"
            if sizes[quality_key] is None:
                sizes[quality_key] = round(filesize / (1024 * 1024), 2)
                processed_count += 1
    
    # Quick estimation for missing sizes
    available_sizes = {k: v for k, v in sizes.items() if v is not None}
    if available_sizes:
        # Use the first available size as base for estimation
        base_quality, base_size = next(iter(available_sizes.items()))
        multipliers = {"360p": 1, "480p": 1.5, "720p": 2.5, "1080p": 4}
        base_multiplier = multipliers[base_quality]
        
        for quality in sizes:
            if sizes[quality] is None:
                sizes[quality] = round(base_size * multipliers[quality] / base_multiplier, 2)
    else:
        # Ultimate fallback
        sizes = {"360p": 25, "480p": 40, "720p": 75, "1080p": 150}
    
    return sizes

@app.route("/api_fetch", methods=['POST'])
def metaDeta():
    data = request.get_json()
    url = data['url']
    
    # Check cache first
    cache_key = url
    current_time = time.time()
    
    if cache_key in video_cache:
        cached_data, timestamp = video_cache[cache_key]
        if current_time - timestamp < cache_timeout:
            print("Returning cached data")
            return cached_data
    
    VIDEO_ID = extract_video_id(url)
    
    def get_api_details():
        return get_video_details(API_KEY, VIDEO_ID)
    
    def get_video_info():
        return get_basic_info_fast(url)
    
    future_api = executor.submit(get_api_details)
    future_info = executor.submit(get_video_info)
    
    try:
        details = future_api.result(timeout=15)  
    except Exception as e:
        print(f"API details failed: {e}")
        return {"error": "Failed to get video details"}
    
    if "error" in details:
        return {"error": details["error"]}
    
    try:
        info = future_info.result(timeout=20) 
        sizes = get_format_sizes_optimized(info)
    except Exception as e:
        print(f"Video info extraction failed: {e}")
        sizes = {"360p": 25, "480p": 40, "720p": 75, "1080p": 150}
    
    response_data = {
        "title": details["title"],
        "video_id": details["video_id"],
        "channel_title": details["channel_title"],
        "published_at": details["published_at"],
        "duration": details["duration"],
        "view_count": details["view_count"],
        "like_count": details["like_count"],
        "VideoEmbedLink": f"https://www.youtube.com/embed/{VIDEO_ID}",
        "filesize_by_quality": sizes
    }
    
    video_cache[cache_key] = (response_data, current_time)
    
    if len(video_cache) > 50:
        oldest_key = min(video_cache.keys(), key=lambda k: video_cache[k][1])
        del video_cache[oldest_key]
    
    return response_data

@app.route("/api_fetch_fast", methods=['POST'])
def metaDetaFast():
    """Ultra-fast version - returns basic info immediately, sizes later"""
    data = request.get_json()
    url = data['url']
    VIDEO_ID = extract_video_id(url)
    
    details = get_video_details(API_KEY, VIDEO_ID)
    if "error" in details:
        return {"error": details["error"]}
    
    estimated_sizes = {"360p": 25, "480p": 40, "720p": 75, "1080p": 150}
    
    response_data = {
        "title": details["title"],
        "video_id": details["video_id"],
        "channel_title": details["channel_title"],
        "published_at": details["published_at"],
        "duration": details["duration"],
        "view_count": details["view_count"],
        "like_count": details["like_count"],
        "VideoEmbedLink": f"https://www.youtube.com/embed/{VIDEO_ID}",
        "filesize_by_quality": estimated_sizes,
        "sizes_estimated": True 
    }
    
    def update_sizes_background():
        try:
            info = get_basic_info_fast(url)
            if info:
                real_sizes = get_format_sizes_optimized(info)
                print(f"Real sizes for {VIDEO_ID}: {real_sizes}")
        except Exception as e:
            print(f"Background size update failed: {e}")
    
    executor.submit(update_sizes_background)
    
    return response_data


def insert_values(name, email, password):
    query = """INSERT INTO DATA(NAME, EMAIL, PASSWORD) VALUES (?, ?, ?)"""
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    try:
        cursor.execute(query, (name, email, password))
        connection.commit()
    except sqlite3.IntegrityError as e:
        print("Error:", e)
    finally:
        connection.close()


def is_email_unique(email):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM DATA WHERE EMAIL = ?", (email,))
    result = cursor.fetchone()
    connection.close()
    return result is None

def is_valid_login(email,password):
    query="""SELECT PASSWORD FROM DATA WHERE EMAIL= (?)"""
    connection=sqlite3.connect("database.db")
    cursor=connection.cursor()
    cursor.execute(query,(email,))
    value=cursor.fetchone()
    connection.close()
    if value is None:
        return False
    return value[0] == password

def get_user_name(email):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    query="""SELECT NAME FROM DATA WHERE EMAIL =(?)"""
    cursor.execute(query,(email,))
    value=cursor.fetchone()
    connection.close()
    return value[0]


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form_type = request.form["form_type"]
        if form_type == "register":
            name = request.form["name"]
            email = request.form["email"].lower()
            password = request.form["password"]
            if not is_email_unique(email):
                return render_template("login.html", error="Email already registered")

            insert_values(name, email, password)
            return render_template("login.html", registered=True)
        else:
            email = request.form["email"].lower()
            password = request.form["password"]
            if is_valid_login(email,password):# check these lines of code
                user_name = get_user_name(email)  # You'll need to implement this function
                print(user_name)
                
                # Set session variables
                session['logged_in'] = True
                session['user_email'] = email
                session['user_name'] = user_name
                
                print('SUCCESSFUL')
                return redirect("/")
            else:
                return render_template("login.html",login_failed=True)
    return render_template("login.html")
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def create_connection():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    query = """CREATE TABLE IF NOT EXISTS DATA
    (
    NAME TEXT NOT NULL,
    EMAIL TEXT NOT NULL PRIMARY KEY,
    PASSWORD TEXT NOT NULL
    )
    """
    cursor.execute(query)
    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_connection()
    app.run(debug=True)