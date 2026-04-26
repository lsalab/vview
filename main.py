#!/usr/bin/env python3

import cherrypy
import av
import errno
from base64 import b64encode
from io import BytesIO
try:
    from Crypto.Hash import SHA384
except ImportError:
    try:
        from Cryptodome.Hash import SHA384
    except ImportError:
        import hashlib
        class SHA384:
            @staticmethod
            def new(data):
                return hashlib.sha384(data)
from mimetypes import guess_type
from os import mkdir, access, listdir, R_OK, W_OK, X_OK
from os.path import abspath, exists, isdir, basename, getsize
from PIL import Image
from sqlite3 import connect
from sys import stderr, exit
from types import SimpleNamespace
from yattag import Doc, indent
import signal
import sys

VID_FOLDER = './vid'
JS_FOLDER = './js'
CSS_FOLDER = './css'
BUFFER_SIZE = 8192
THUMBNAIL_HEIGHT = 200
THUMBNAIL_TIME = 60
THUMBNAIL_DB = 'metadata.sqlite'

def perr(msg : str):
    _ = stderr.write(msg.strip('\r\n') + '\r\n')
    stderr.flush()

class Viewer(object):

    def __init__(self):
        self.hashes : dict[str,dict[str,str]] = dict()
        for b in ['css', 'js']:
            self.hashes[b] = dict()
            for f in [f"{abspath(f'./{b}')}/{p}" for p in listdir(abspath(f'./{b}'))]:
                fhash = SHA384.new(open(f, 'rb').read())
                self.hashes[b][basename(f)] = b64encode(fhash.digest()).decode('utf-8')
        with connect(THUMBNAIL_DB) as con:
            cur = con.cursor()
            if 'thumbnails' not in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() if len(r)]:
                cur.execute("CREATE TABLE thumbnails(file, img)")
        self._update_thumbnails()
    
    def _update_thumbnails(self):
        with connect(THUMBNAIL_DB) as con:
            cur = con.cursor()
            metanames = [r[0] for r in cur.execute("SELECT file FROM thumbnails;").fetchall() if len(r)]
            filenames = [basename(f) for f in listdir(abspath(VID_FOLDER))]
            # Remove metadata of deleted files
            for fname in metanames:
                if fname not in filenames:
                    cur.execute(f'''DELETE FROM thumbnails WHERE file == '{fname}';''')
                    con.commit()
            # Create metadata of new files
            for fname in filenames:
                if fname not in metanames and fname[-4:] == '.mp4':
                    fname = f'{abspath(VID_FOLDER)}/{fname}'
                    # Use PyAV to get video properties and extract frame
                    container = av.open(fname)
                    video_stream = container.streams.video[0]
                    width = video_stream.width
                    height = video_stream.height
                    frate = int(video_stream.average_rate) if video_stream.average_rate else 30
                    
                    # Seek to THUMBNAIL_TIME seconds
                    seek_pts = int(THUMBNAIL_TIME * 1000000)
                    container.seek(seek_pts)
                    
                    # Get the first frame after seeking
                    frame = None
                    for frame in container.decode(video=0):
                        break
                    
                    if frame is None:
                        continue
                    
                    # Convert frame to PIL Image
                    img = frame.to_image()
                    img = img.resize( ( int( ( THUMBNAIL_HEIGHT / height ) * width ), int( ( THUMBNAIL_HEIGHT / height ) * height ) ) )
                    with BytesIO() as tnout:
                        img.save(tnout, format='PNG')
                        img = b64encode(tnout.getbuffer()).decode(encoding='utf-8')
                        cur.execute(f'''INSERT INTO thumbnails(file, img) VALUES ('{basename(fname):s}', '{img:s}')''')
                        con.commit()
                    container.close()

    @cherrypy.expose
    def index(self) -> str:
        doc, tag, text = Doc().tagtext()
        with connect(THUMBNAIL_DB) as con:
            cur = con.cursor()
            doc.asis('<!DOCTYPE html>')
            with tag('html'):
                with tag('head'):
                    doc.asis('<meta charset="utf-8">')
                    doc.asis('<meta name="viewport" content="width=device-width, initial-scale=1">')
                    with tag('title'):
                        text('Video viewer')
                    doc.stag(
                        'link',
                        href='/css/bootstrap.min.css',
                        rel='stylesheet',
                        integrity=f'sha384-{self.hashes["css"]["bootstrap.min.css"]}'
                    )
                with tag('body', style='background-color: #c0c0c0;'):
                    with tag(
                        'script',
                        src = 'js/bootstrap.bundle.min.js',
                        integrity = f'sha384-{self.hashes["js"]["bootstrap.bundle.min.js"]}'
                    ):
                        pass
                    with tag('div', klass='container-fluid'):
                        vidlst = sorted( basename(f) for f in listdir(abspath(VID_FOLDER)) if f[-4:] == '.mp4' )
                        while len(vidlst):
                            with tag('div', klass='row'):
                                rlst = vidlst[:6]
                                vidlst = vidlst[6:]
                                for fname in rlst:
                                    idata = cur.execute(f'''SELECT img FROM thumbnails WHERE file == '{fname}';''').fetchone()
                                    if idata is not None:
                                        with tag('div', klass='col-sm-2'):
                                            with tag('a', href=f'/vvid?video={fname}'):
                                                doc.stag('img', klass='img-thumbnail rounded mx-auto px-2 py-2', src=f'data:image/png;base64,{idata[0]}')
                        with tag('div', klass='row'):
                            with tag('div', klass='col-lg-5'):
                                pass
                            with tag('div', klass='col-lg-2'):
                                with tag('div', klass='text-center'):
                                    with tag('a', klass='btn btn-primary text-center my-2 mx-1', role='button', href='/refresh'):
                                        text('Refresh')
                            with tag('div', klass='col-lg-5'):
                                pass

        return indent(doc.getvalue())

    @cherrypy.expose
    def refresh(self):
        self._update_thumbnails()
        raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    def thumbnail(self, video: str = None, time: float = 0.0):
        """Generate and return a thumbnail for a video at a specific timestamp.
        
        Args:
            video: Name of the video file
            time: Timestamp in seconds
            
        Returns:
            PNG image data as binary response
        """
        if video is None:
            raise cherrypy.HTTPError(400, "Missing video parameter")
        
        try:
            time = float(time)
        except (ValueError, TypeError):
            raise cherrypy.HTTPError(400, "Invalid time parameter")
        
        # Validate video file exists and is in the video folder
        video_path = f'{abspath(VID_FOLDER)}/{basename(video)}'
        if not exists(video_path) or basename(video) not in [basename(f) for f in listdir(abspath(VID_FOLDER))]:
            raise cherrypy.HTTPError(404, "Video not found")
        
        if not video_path.endswith('.mp4'):
            raise cherrypy.HTTPError(400, "Invalid video format")
        
        try:
            # Open video file with PyAV
            container = av.open(video_path)
            video_stream = container.streams.video[0]
            
            # Get video properties
            width = video_stream.width
            height = video_stream.height
            
            # Get duration in seconds
            # PyAV duration is typically in microseconds (1/1000000 seconds)
            if container.duration is not None:
                duration = float(container.duration) / 1000000.0
            elif video_stream.duration is not None:
                # Use stream duration (in stream's time_base)
                duration = float(video_stream.duration * video_stream.time_base)
            else:
                duration = 0.0
            
            # Clamp time to valid range
            if duration > 0:
                time = max(0.0, min(time, duration))
            
            # Seek to the specified time (PyAV seek uses microseconds)
            seek_pts = int(time * 1000000)
            container.seek(seek_pts)
            
            # Decode frames and get the first one after seeking
            frame = None
            for frame in container.decode(video=0):
                # Take the first frame we get after seeking
                break
            
            if frame is None:
                raise cherrypy.HTTPError(500, "Could not extract frame at specified time")
            
            # Convert frame to PIL Image
            img = frame.to_image()
            
            # Resize to reasonable thumbnail size (maintain aspect ratio)
            thumbnail_width = 320
            thumbnail_height = int((thumbnail_width / width) * height)
            img = img.resize((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
            
            # Convert to PNG and return
            with BytesIO() as output:
                img.save(output, format='PNG')
                output.seek(0)
                cherrypy.response.headers['Content-Type'] = 'image/png'
                cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return output.read()
                
        except Exception as e:
            error_msg = str(e)
            perr(f'Error generating thumbnail: {error_msg}')
            raise cherrypy.HTTPError(500, "Error generating thumbnail")

    @cherrypy.expose
    def vvid(self, video : str = 'None') -> str:
        doc, tag, text = Doc().tagtext()
        doc.asis('<!DOCTYPE html>')
        with tag('html'):
            with tag('head'):
                doc.asis('<meta charset="utf-8">')
                doc.asis('<meta name="viewport" content="width=device-width, initial-scale=1">')
                with tag('title'):
                    text('Video viewer')
                doc.stag(
                    'link',
                    href='/css/bootstrap.min.css',
                    rel='stylesheet',
                    integrity=f'sha384-{self.hashes["css"]["bootstrap.min.css"]}'
                )
                doc.stag(
                    'link',
                    href='/css/video-js.css',
                    rel='stylesheet',
                    integrity=f'sha384-{self.hashes["css"]["video-js.css"]}'
                )
            with tag('body', style='background-color: #c0c0c0;'):
                with tag('div', klass='container-fluid'):
                    if video != 'None' and all(v in [basename(f) for f in listdir(abspath(VID_FOLDER))] for v in [video]):
                        with tag(
                            'script',
                            src = 'js/bootstrap.bundle.min.js',
                            integrity = f'sha384-{self.hashes["js"]["bootstrap.bundle.min.js"]}'
                        ):
                            pass
                        with tag('div', klass='row'):
                            with tag('div', klass='col-lg-1'):
                                pass
                            with tag('div', klass='col-lg-10'):
                                with tag(
                                    'video',
                                    'controls',
                                    'autoplay',
                                    ('data-setup', '{}'),
                                    ('data-video', video),
                                    klass='video-js',
                                    id='curr-video',
                                    preload='auto'
                                ):
                                    doc.stag('source', src=f'/vid/{video}', type='video/mp4')
                                    # doc.stag('source', src=f'/vid/{video[:-4]}.webm', type='video/webm')
                                with tag(
                                    'script',
                                    src = '/js/video.min.js',
                                    integrity = f'sha384-{self.hashes["js"]["video.min.js"]}'
                                ):
                                    pass
                                with tag(
                                    'script',
                                    src = '/js/videojs.hotkeys.min.js',
                                    integrity = f'sha384-{self.hashes["js"]["videojs.hotkeys.min.js"]}'
                                ):
                                    pass
                                with tag(
                                    'script',
                                    src = '/js/custom-player.js',
                                    integrity = f'sha384-{self.hashes["js"]["custom-player.js"]}'
                                ):
                                    pass
                            with tag('div', klass='col-lg-1'):
                                pass
                    else:
                        with tag('div'):
                            text('Not found')
                    with tag('div', klass='row'):
                        with tag('div', klass='col-lg-5'):
                            pass
                        with tag('div', klass='col-lg-2'):
                            with tag('div', klass='text-center'):
                                with tag('a', klass='btn btn-primary text-center my-2 mx-auto', role='button', href='/'):
                                    text('Back')
                        with tag('div', klass='col-lg-5'):
                            pass
        return indent(doc.getvalue())

    def stop(self):
        cherrypy.log.error(msg='Viewer Stopped!', context='VIEWER')

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    cherrypy.engine.exit()

_original_unraisablehook = sys.unraisablehook

def _is_cheroot_shutdown_bad_file_descriptor(unraisable):
    """Return True for Cheroot socket cleanup noise emitted during shutdown."""
    if unraisable.exc_type is not OSError:
        return False
    if getattr(unraisable.exc_value, "errno", None) != errno.EBADF:
        return False

    tb = unraisable.exc_traceback
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        if filename.endswith("/cheroot/makefile.py"):
            return True
        tb = tb.tb_next

    return False

def filtered_unraisablehook(unraisable):
    if _is_cheroot_shutdown_bad_file_descriptor(unraisable):
        return
    _original_unraisablehook(unraisable)

def main():
    # Suppress harmless Cheroot cleanup errors raised from object finalizers.
    sys.unraisablehook = filtered_unraisablehook
    
    # Check vid folder
    if not exists(VID_FOLDER):
        perr(f'WARNING: No {VID_FOLDER} folder. Creating ...')
        mkdir(VID_FOLDER)
    elif not isdir(VID_FOLDER):
        perr(f'ERROR: {VID_FOLDER} is not a directory')
        exit(1)
    elif not access(VID_FOLDER, R_OK | W_OK | X_OK):
        perr(f'ERROR: Insufficient privileges on {VID_FOLDER}')
        exit(2)
    # Check static folders
    if not exists(JS_FOLDER) or not isdir(JS_FOLDER):
        perr(f'ERROR: Missing {JS_FOLDER} folder.')
        exit(3)
    if not exists(CSS_FOLDER) or not isdir(CSS_FOLDER):
        perr(f'ERROR: Missing {CSS_FOLDER} folder.')
        exit(4)
    # Configure and launch app
    app : Viewer = Viewer()
    app_config : dict = dict()
    app_config['/js'] = dict()
    app_config['/js']['tools.staticdir.on'] = True
    app_config['/js']['tools.staticdir.dir'] = abspath(JS_FOLDER)
    app_config['/css'] = dict()
    app_config['/css']['tools.staticdir.on'] = True
    app_config['/css']['tools.staticdir.dir'] = abspath(CSS_FOLDER)
    app_config['/vid'] = dict()
    app_config['/vid']['tools.staticdir.on'] = True
    app_config['/vid']['tools.staticdir.dir'] = abspath(VID_FOLDER)

    cherrypy.tree.mount(app, '/', app_config)
    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.engine.subscribe('stop', app.stop)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        cherrypy.engine.start()
        cherrypy.engine.block()
    except KeyboardInterrupt:
        cherrypy.engine.exit()
    finally:
        # Ensure engine is stopped
        if cherrypy.engine.state == cherrypy.engine.states.STARTED:
            cherrypy.engine.exit()

if __name__ == '__main__':
    main()
