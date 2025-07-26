
import os
import logging
import requests
from flask import Flask, request, render_template, jsonify
from time import sleep
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

GLADIA_API_KEY = os.environ.get("GLADIA_API_KEY")
UPLOAD_ENDPOINT = os.environ.get("UPLOAD_ENDPOINT")
TRANSCRIBE_ENDPOINT =os.environ.get("TRANSCRIBE_ENDPOINT") 


def make_request(url, headers, method="GET", data=None, files=None):
    try:
        if method == "POST":
            response = requests.post(url, headers=headers, json=data, files=files)
        else:
            response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error making request to {url}: {e}")
        return {"error": str(e)}


@app.route('/transcribe', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_file = request.files.get('audio_file')

        if not uploaded_file:
            return jsonify({'error': 'No file uploaded'}), 400

        file_content = uploaded_file.read()
        file_ext = os.path.splitext(uploaded_file.filename)[1][1:]  # Remove dot

        headers = {
            "x-gladia-key": GLADIA_API_KEY,
            "accept": "application/json"
        }

        files = [("audio", (uploaded_file.filename, file_content, f"audio/{file_ext}"))]

        logging.info("Uploading file to Gladia...")
        upload_response = make_request(UPLOAD_ENDPOINT, headers, "POST", files=files)
        audio_url = upload_response.get("audio_url")

        if not audio_url:
            return jsonify({'error': 'Upload failed', 'details': upload_response}), 500

        # Prepare transcription request
        headers["Content-Type"] = "application/json"
        data = {
            "audio_url": audio_url,
            "diarization": True
        }

        logging.info("Sending transcription request to Gladia...")
        transcribe_response = make_request(TRANSCRIBE_ENDPOINT, headers, "POST", data=data)
        result_url = transcribe_response.get("result_url")

        if not result_url:
            return jsonify({'error': 'Transcription initiation failed', 'details': transcribe_response}), 500

        # Polling for results
        logging.info("Polling for transcription results...")
        while True:
            poll_response = make_request(result_url, headers)
            status = poll_response.get("status")

            if status == "done":
                res=poll_response.get("result")['transcription']['full_transcript']
                return jsonify({'result':res})
                # return jsonify({'result': poll_response.get("result")['transcription']['full_transcript']})
            elif status == "error":
                return jsonify({'error': 'Transcription failed', 'details': poll_response}), 500
            else:
                sleep(1)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)



