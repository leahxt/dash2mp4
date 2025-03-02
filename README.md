# dash2mp4

A lightweight HTTP server running on Docker that retrieves a DASH-encoded MP4 audio file from a network location, uses ffmpeg to reformat it into a standard faststart MP4 file (adding chapters or other metadata if provided), and returns the converted file in its response.

## Security

This server is secure when handling trusted requests (hosted on an internal network or secured using the shared secret described below). However, it is NOT safe for processing untrusted requests from users. If you allow untrusted requests, understand that this project includes NO protection against denial of service (DOS) attacks if a malicious user processes a large or badly formatted file. It also includes almost NO protection against server-side request forgery (SSRF) attacks. If the input files are stored on a private server, SSRF attacks can expose ALL data on that server (or even elsewhere in your network) to a malicious user.

If it's possible to host this application on an internal network that is not directly reachable from the Internet, the secret key is not needed. Otherwise, you MUST generate a random shared key (i.e. 64 randomly generated characters) to configure on both this server and whatever application server will be calling it. Understand that there is NO secure way to store that secret on a client-side application. You MUST implement a more secure authorization process if you need to authenticate clients that you don't control.

## Environment variables

`AUTH_KEY` - a static secret that must be provided in the `X-Auth-Key` header with all requests. Set to blank to disable this check. As described above, this server is NEVER safe for client-side access.

`PRODUCTION_BASE_PATH` - the base URL that the requested filename is appended to. Used when the `X-Environment` header is omitted or set to something other than `Development`. If the base URL refers to a folder, a trailing slash is mandatory (`https://example.com/folder/`). If it's pointed at the root of a site, the trailing slash is optional (`https://example.com`).

`DEVELOPMENT_BASE_PATH` - the base URL used when `X-Environment` is set to `Development`. Otherwise behaves exactly the same as the production path.

## Usage

Only POST requests are accepted. Any other method will result in a 405 Method Not Allowed error.

The `Content-Type` HTTP header must be provided and set to `application/json`.

The `Accept` HTTP header must be provided and set to `audio/mp4`.

The `X-Auth-Key` HTTP header must be provided if the `AUTH_KEY` environment variable is set.

The `X-Environment` HTTP header is optional. If it's set to `Development`, the `DEVELOPMENT_BASE_PATH` variable provides the base URL for retrieving the file. If it's omitted or set to anything else, the `PRODUCTION_BASE_PATH` variable is used instead.

Requests should be JSON formatted with two values:
* `filename` - a string containing the filename to retrieve from the base URL. The path, params, and fragment are preserved following Python's urljoin rules. Any schema and host are stripped off.
* `chapters` - a string containing FFMETADATA chapter timings or other metadata to be added to the output file. To leave the metadata blank, set this value to `;FFMETADATA1`.

### Example
#### Environment variables
```
AUTH_KEY=somerandomlygeneratedkey
PRODUCTION_BASE_PATH=https://example.com/media/
DEVELOPMENT_BASE_PATH=https://dev.example.com/media/
```
#### Request
```
POST /
Content-Type: application/json
Accept: audio/mp4
X-Environment: Production
X-Auth-Key: somerandomlygeneratedkey

{
    "filename": "file1.mp4",
    "chapters": ";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\ntitle=The first chapter\nSTART=1\nEND=60000\n\n[CHAPTER]\nTIMEBASE=1/1000\ntitle=The second chapter\nSTART=60000\nEND=120000\n\n"
}
```

The application will connect to and download `https://example.com/media/file1.mp4`, run ffmpeg with that file and the chapter data as inputs (along with `-vn` to omit video, `-c:a copy` to copy the audio directly, and `-movflags +faststart` to optimize it for streaming), and respond with the result as `audio/mp4`.