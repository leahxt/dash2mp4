from http import HTTPStatus
from typing import cast
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit
from tempfile import NamedTemporaryFile

from httpx import AsyncClient
from ffmpeg.asyncio import FFmpeg  # type: ignore
from starlette.applications import Starlette
from starlette.config import Config
from starlette.datastructures import Secret
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

config = Config(".env")
auth_key = config('AUTH_KEY', cast=Secret)
production_base_path = config('PRODUCTION_BASE_PATH')
development_base_path = config('DEVELOPMENT_BASE_PATH')

async def convert(req: Request) -> Response:
    provided_key = req.headers.get('X-Auth-Key')
    if str(auth_key) != '' and provided_key != str(auth_key):
        return PlainTextResponse('Invalid key', status_code=HTTPStatus.UNAUTHORIZED.value)
    
    if req.headers.get('Content-Type') != 'application/json':
        return PlainTextResponse('Only JSON-formatted requests are accepted', status_code=HTTPStatus.BAD_REQUEST.value)

    if req.headers.get('Accept') != 'audio/mp4':
        return PlainTextResponse('Only conversions to MP4 audio are supported', status_code=HTTPStatus.BAD_REQUEST.value)

    base_url = production_base_path
    if req.headers.get('X-Environment') == 'Development':
        base_url = development_base_path

    body = await req.json()
    chapters: str = body.get('chapters')

    filename = body.get('filename')
    filename_parts = cast(SplitResult, urlsplit(filename))
    filename_url = urlunsplit(['', '', filename_parts.path, filename_parts.query, filename_parts.fragment])
    file_url = urljoin(base_url, filename_url)

    with (NamedTemporaryFile(suffix='.mp4') as tmp_input,
          NamedTemporaryFile(suffix='.txt') as tmp_chapters, 
          NamedTemporaryFile(suffix='.mp4') as tmp_output):
        
        async with AsyncClient() as client:
            input_request = await client.get(file_url)
            for _ in range(3):
                if input_request.is_success:
                    break
                else:
                    print(f'Received status code {input_request.status_code} from {file_url}')
                    input_request = await client.get(file_url)

            if not input_request.is_success:
                return PlainTextResponse(f'Failed to download requested file for encoding ({input_request.status_code}):\n\n{(await input_request.aread()).decode('utf8')}', status_code=HTTPStatus.BAD_GATEWAY)
    
            tmp_input.write(input_request.content)
            tmp_input.flush()

        tmp_chapters.write(chapters.encode('utf8'))
        tmp_chapters.flush()

        ffmpeg = FFmpeg().option('y').input(tmp_input.name).input(tmp_chapters.name).output(tmp_output.name, options={'vn': None, 'codec:a': 'copy', 'movflags': '+faststart'})  #type: ignore
        await ffmpeg.execute(timeout=60)
        output = tmp_output.read()

    return Response(output, headers={'Content-Type': 'audio/mp4'})

app = Starlette(routes=[
        Route('/', convert, methods=['POST'])
    ]
)