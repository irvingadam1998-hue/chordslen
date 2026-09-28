"""Download versioned GuitarSet, add a LAB corpus, or validate an existing manifest."""
import argparse
import hashlib
import http.client
import io
import json
from pathlib import Path
import random
import re
import urllib.request
import zipfile
from .dataset import assert_no_leakage, load_manifest

RECORD = 'https://zenodo.org/records/3371780/files/'
ARCHIVES = {'annotation.zip': 'b39b78e63d3446f2e54ddb7a54df9b10',
            'audio_mono-mic.zip': '275966d6610ac34999b58426beb119c3'}


def download_archive(name, directory):
    target = directory / name
    def valid():
        if not target.is_file():
            return False
        with target.open('rb') as stream:
            return hashlib.file_digest(stream, 'md5').hexdigest() == ARCHIVES[name]
    if not valid():
        temporary = target.with_suffix('.part')
        print(f'Descargando {name} desde Zenodo...', flush=True)
        with urllib.request.urlopen(RECORD + name + '?download=1', timeout=120) as source, temporary.open('wb') as dest:
            while block := source.read(1024 * 1024):
                dest.write(block)
        temporary.replace(target)
        if not valid():
            raise ValueError(f'Checksum incorrecto: {target}')
    return target


def safe_extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            path = (destination / member.filename).resolve()
            if not path.is_relative_to(destination.resolve()):
                raise ValueError('Ruta insegura en ZIP')
            source.extract(member, destination)


class RemoteZip(io.RawIOBase):
    """HTTP Range reader: subset downloads still use zipfile CRC verification."""
    def __init__(self, url):
        self.url, self.position = url, 0
        request = urllib.request.Request(url, headers={'Range': 'bytes=0-0'})
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 206:
                raise ValueError('El servidor no admite Range; descarga el ZIP completo')
            self.length = int(response.headers['Content-Range'].split('/')[-1])

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else (self.position if whence == 1 else self.length) + offset
        return self.position

    def tell(self):
        return self.position

    def read(self, size=-1):
        size = self.length - self.position if size < 0 else min(size, self.length - self.position)
        if size <= 0:
            return b''
        end = self.position + size - 1
        chunks = []
        for _ in range(12):
            request = urllib.request.Request(self.url, headers={'Range': f'bytes={self.position}-{end}'})
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    if response.status != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes {self.position}-'):
                        raise ValueError('Respuesta Range inválida')
                    try:
                        data = response.read(end - self.position + 1)
                    except http.client.IncompleteRead as exc:
                        data = exc.partial
                chunks.append(data)
                self.position += len(data)
                if self.position > end:
                    return b''.join(chunks)
            except (TimeoutError, ConnectionError):
                continue
        raise OSError('Descarga parcial incompleta tras varios intentos')


def guitarset_rows(directory, seed=42, solo='keep'):
    artists = [f'{i:02}' for i in range(6)]
    families = ['1', '2', '3']
    rng = random.Random(seed)
    rng.shuffle(artists)
    rng.shuffle(families)
    artist_split = {a: ('train' if i < 4 else 'validation' if i == 4 else 'test')
                    for i, a in enumerate(artists)}
    family_split = dict(zip(families, ('train', 'validation', 'test')))
    rows = []
    for path in sorted((directory / 'annotations').rglob('*.jams')):
        match = re.fullmatch(r'(\d{2})_([A-Za-z]+)([123])-.*_(comp|solo)', path.stem)
        if not match:
            raise ValueError(f'Nombre GuitarSet inesperado: {path.name}')
        artist, _, family, take = match.groups()
        split = artist_split[artist]
        if family_split[family] != split:
            split = 'excluded'
        # Solo takes are single-line melodies: the chord is annotated but barely audible.
        if take == 'solo' and (solo == 'exclude' or (solo == 'train-only' and split != 'train')):
            split = 'excluded'
        # Known timing problems listed by the official repository, issue #5.
        if path.stem in {'04_BN3-154-E_comp', '04_Jazz1-200-B_comp'}:
            split = 'excluded'
        rows.append({'id': 'guitarset:' + path.stem, 'dataset': 'GuitarSet-1.1.0',
                     'audio': str((directory / 'audio' / (path.stem + '_mic.wav')).resolve()),
                     'annotation': str(path.resolve()), 'format': 'guitarset_jams',
                     'artist_id': 'guitarset:player:' + artist,
                     'origin_id': 'guitarset:progression-family:' + family,
                     'split': split, 'implicit_bass': False})
    assert_no_leakage(rows)
    return rows


AUDIO_EXTENSIONS = ('.wav', '.flac', '.mp3', '.ogg', '.m4a')


def lab_rows(annotations, audio, dataset, split='train', implicit_bass=False):
    """<artist>/[album/]<song>.lab paired with the same relative path under audio/.

    The whole artist goes to one split, so the leakage check stays meaningful.
    """
    annotations, audio = annotations.resolve(), audio.resolve()
    slug = re.sub(r'[^a-z0-9]+', '-', dataset.lower()).strip('-')
    rows, missing = [], []
    for lab in sorted(annotations.rglob('*.lab')):
        relative = lab.relative_to(annotations).with_suffix('')
        if len(relative.parts) < 2:
            raise ValueError(f'Se espera <artista>/.../<canción>.lab: {lab}')
        source = next((audio / relative.with_suffix(ext) for ext in AUDIO_EXTENSIONS
                       if (audio / relative.with_suffix(ext)).is_file()), None)
        if source is None:
            missing.append(str(relative))
            continue
        artist = relative.parts[0]
        if split == 'auto':
            # Stable across runs and machines: 80/10/10 by artist, never by song.
            bucket = int(hashlib.sha256(artist.encode()).hexdigest(), 16) % 10
            row_split = 'test' if bucket == 0 else 'validation' if bucket == 1 else 'train'
        else:
            row_split = split
        # Track numbers are dropped so re-releases of one song share an origin.
        song = re.sub(r'^\d+[\s_.-]*(-[\s_]*)?', '', relative.name).lower()
        rows.append({'id': f'{slug}:{relative.as_posix()}', 'dataset': dataset,
                     'audio': str(source), 'annotation': str(lab), 'format': 'lab',
                     'artist_id': f'{slug}:artist:{artist}',
                     'origin_id': f'{slug}:song:{artist}/{song}',
                     'split': row_split, 'implicit_bass': implicit_bass})
    if missing:
        print(f'{len(missing)} anotaciones sin audio (omitidas), p. ej. {missing[0]}', flush=True)
    if not rows:
        raise ValueError('No se emparejó ningún .lab con su audio')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guitarset', type=Path, help='Directorio de descarga/preparación')
    parser.add_argument('--manifest', type=Path, default=Path('data/manifest.jsonl'))
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--audio-limit-per-split', type=int, help='Solo prototipo; selección determinista, no benchmark completo')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--solo', choices=('keep', 'train-only', 'exclude'), default='keep',
                        help='Tomas solo de GuitarSet: en todas las particiones, solo en train, o en ninguna')
    parser.add_argument('--lab-annotations', type=Path, help='Directorio <artista>/.../<canción>.lab')
    parser.add_argument('--lab-audio', type=Path, help='Audio propio con las mismas rutas relativas')
    parser.add_argument('--lab-dataset', default='LAB', help='Nombre del corpus, p. ej. Isophonics')
    parser.add_argument('--lab-split', choices=('train', 'validation', 'test', 'auto'), default='train')
    parser.add_argument('--lab-implicit-bass', action='store_true',
                        help='Acordes sin /bajo tienen la raíz en el bajo (convención Harte)')
    parser.add_argument('--base-manifest', type=Path, help='Manifiesto existente al que añadir el corpus LAB')
    args = parser.parse_args()
    if args.lab_annotations:
        if not args.lab_audio:
            raise ValueError('--lab-annotations requiere --lab-audio')
        rows = load_manifest(args.base_manifest, check_files=False) if args.base_manifest else []
        rows += lab_rows(args.lab_annotations, args.lab_audio, args.lab_dataset,
                         args.lab_split, args.lab_implicit_bass)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        # Revalidates IDs, files and artist/origin/audio leakage across both corpora.
        load_manifest(args.manifest)
        print(json.dumps({s: sum(r['split'] == s for r in rows)
                          for s in ('train', 'validation', 'test', 'excluded')}, indent=2))
        return
    if not args.guitarset:
        rows = load_manifest(args.manifest)
        print(f'Manifiesto válido: {len(rows)} grabaciones; artistas/orígenes/audio sin cruces')
        return
    directory = args.guitarset.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if args.download:
        safe_extract(download_archive('annotation.zip', directory), directory / 'annotations')
    rows = guitarset_rows(directory, args.seed, args.solo)
    if not rows:
        raise ValueError('No hay JAMS; usa --download o extrae annotation.zip en annotations/')
    if args.audio_limit_per_split:
        rng = random.Random(args.seed)
        for split in ('train', 'validation', 'test'):
            candidates = [r for r in rows if r['split'] == split]
            rng.shuffle(candidates)
            for row in candidates[args.audio_limit_per_split:]:
                row['split'] = 'excluded'
    if args.download:
        if args.audio_limit_per_split:
            with zipfile.ZipFile(RemoteZip(RECORD + 'audio_mono-mic.zip?download=1')) as source:
                members = {Path(name).name: name for name in source.namelist()}
                for row in rows:
                    target = Path(row['audio'])
                    if row['split'] != 'excluded' and not target.is_file():
                        print(f'Descargando {target.name}', flush=True)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        temporary = target.with_suffix('.part')
                        temporary.write_bytes(source.read(members[target.name]))
                        temporary.replace(target)
        else:
            safe_extract(download_archive('audio_mono-mic.zip', directory), directory / 'audio')
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    load_manifest(args.manifest)
    print(json.dumps({s: sum(r['split'] == s for r in rows)
                      for s in ('train', 'validation', 'test', 'excluded')}, indent=2))


if __name__ == '__main__':
    main()
