#!/usr/bin/env python3

import cherrypy
import ffmpeg
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
                    vprobe = ffmpeg.probe(fname)
                    vstream = next((s for s in vprobe['streams'] if s['codec_type'] == 'video'), None)
                    width = int(vstream['width'])
                    height = int(vstream['height'])
                    frate = int(eval(vstream['r_frame_rate']))
                    raw_frame, _ = (ffmpeg.input(fname).filter('select', f'gte(n, {THUMBNAIL_TIME * frate})').output('pipe:', vframes=1, format='rawvideo', pix_fmt='rgb24').run(capture_stdout=True, capture_stderr=True))
                    img = Image.frombytes('RGB', (width, height), raw_frame, 'raw')
                    img = img.resize( ( int( ( THUMBNAIL_HEIGHT / height ) * width ), int( ( THUMBNAIL_HEIGHT / height ) * height ) ) )
                    with BytesIO() as tnout:
                        img.save(tnout, format='PNG')
                        img = b64encode(tnout.getbuffer()).decode(encoding='utf-8')
                        cur.execute(f'''INSERT INTO thumbnails(file, img) VALUES ('{basename(fname):s}', '{img:s}')''')
                        con.commit()

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
                                with tag('script'):
                                    text('''
var player = videojs('curr-video', {
    plugins: {
        hotkeys: {
            volumeStep: 0.1,
            seekStep: 5,
            enableModifiersForNumbers: false,
        },
    },
});
player.fluid(true);
player.aspectRatio('16:9');
''')
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

def main():
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
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    main()
