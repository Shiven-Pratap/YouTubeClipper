from flask import Flask, render_template,request,jsonify,send_from_directory,after_this_request
import yt_dlp
import uuid
import os
import threading
import time

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

app.run(debug=True)