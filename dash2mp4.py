from http import HTTPStatus
from tempfile import NamedTemporaryFile

from ffmpeg.asyncio import FFmpeg  # type: ignore
from starlette.applications import Starlette
from starlette.config import Config
from starlette.datastructures import Secret
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

config = Config(".env")
auth_key = config('AUTH_KEY', cast=Secret)

async def convert(req: Request) -> Response:
    provided_key = req.headers.get('X-Auth-Key')
    if provided_key != str(auth_key):
        return PlainTextResponse('Invalid key', status_code=HTTPStatus.UNAUTHORIZED.value)
    
    if req.headers.get('Content-Type') != 'audio/mp4':
        return PlainTextResponse('Only conversions from MP4 audio are supported', status_code=HTTPStatus.BAD_REQUEST.value)
    if req.headers.get('Accept') != 'audio/mp4':
        return PlainTextResponse('Only conversions to MP4 audio are supported', status_code=HTTPStatus.BAD_REQUEST.value)

    with NamedTemporaryFile(suffix='.mp4') as tmpfile:
        ffmpeg = FFmpeg().option('y').input('pipe:0').output(tmpfile.name, options={'vn': None, 'codec:a': 'copy', 'movflags': '+faststart'})  #type: ignore
        await ffmpeg.execute(await req.body(), timeout=60)
        output = tmpfile.read()

    return Response(output)

app = Starlette(routes=[
        Route('/', convert, methods=['POST'])
    ]
)