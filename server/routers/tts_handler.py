import urllib.request
import urllib.parse
from fastapi import APIRouter, Response

router = APIRouter()

def chunk_text(text, max_len=150):
    """Split text into chunks smaller than max_len without breaking words."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_len:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_len = len(word)
        else:
            current_chunk.append(word)
            current_len += len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

@router.get("/tts")
def get_tts(text: str):
    """
    Proxy Google Translate TTS to bypass browser OpaqueResponseBlocking (ORB) and CORS issues.
    Chunks text to bypass Google's 200-character limit.
    """
    chunks = chunk_text(text, 150)
    audio_data = b""
    
    try:
        for chunk in chunks:
            if not chunk.strip(): continue
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=id&q={urllib.parse.quote(chunk)}"
            req = urllib.request.Request(
                url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://translate.google.com/'
                }
            )
            with urllib.request.urlopen(req) as response:
                audio_data += response.read()
                
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        print(f"[TTS Error] {e}")
        return Response(content="Audio failed", status_code=500)
