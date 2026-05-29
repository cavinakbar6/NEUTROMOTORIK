import urllib.request
import urllib.parse
from fastapi import APIRouter, Response

router = APIRouter()

@router.get("/tts")
def get_tts(text: str):
    """
    Proxy Google Translate TTS to bypass browser OpaqueResponseBlocking (ORB) and CORS issues.
    This guarantees 100% native Indonesian voice without needing local language packs.
    """
    url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=id&q={urllib.parse.quote(text)}"
    req = urllib.request.Request(
        url, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://translate.google.com/'
        }
    )
    try:
        with urllib.request.urlopen(req) as response:
            audio_data = response.read()
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        print(f"[TTS Error] {e}")
        return Response(content="Audio failed", status_code=500)
