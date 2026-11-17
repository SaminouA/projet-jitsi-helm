#!/usr/bin/env python3
"""Contexte en RAM, sources publiques et caches Maven uniquement, aucun secret."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/tmp/jitsi-meet-torture-light')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=SOURCE, help='Clone Torture public epingle')
    parser.add_argument('--with-cache', action='store_true', help='Option volumineuse, seulement avec budget disque adapte')
    args = parser.parse_args()
    root = args.directory
    if root.exists() and any(p.is_file() or p.is_symlink() for p in root.rglob('*')):
        raise SystemExit('Contexte non vide : aucun ecrasement.')
    if subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip() != '4c00915e97006ff2224bb509eb3582bf3a10ca85':
        raise SystemExit('Version Torture inattendue.')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = root / 'payload'; payload.mkdir(exist_ok=True)
    url = 'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.8.7/apache-maven-3.8.7-bin.tar.gz'
    with urllib.request.urlopen(url) as response: body = response.read()
    with urllib.request.urlopen('https://archive.apache.org/dist/maven/maven-3/3.8.7/binaries/apache-maven-3.8.7-bin.tar.gz.sha512', timeout=20) as response: checksum = response.read().decode().split()[0]
    if hashlib.sha512(body).hexdigest() != checksum: raise SystemExit('SHA512 Maven invalide.')
    archive = root / 'maven.tar.gz'; archive.write_bytes(body)
    with tarfile.open(archive) as tar: tar.extractall(payload, filter='data')
    archive.unlink()
    if args.with_cache:
        shutil.copytree(Path.home() / '.m2/repository', payload / 'repository', ignore=shutil.ignore_patterns('*.lastUpdated', 'settings.xml'))
        cache = payload / 'driver-cache/chromedriver/linux64/130.0.6723.116'; cache.mkdir(parents=True)
        shutil.copy2(Path.home() / '.cache/selenium/chromedriver/linux64/130.0.6723.116/chromedriver', cache / 'chromedriver')
    source = payload / 'torture'; source.mkdir()
    for name in ['pom.xml', 'checkstyle.xml']:
        shutil.copy2(args.source / name, source / name)
    shutil.copytree(args.source / 'src', source / 'src')
    shutil.copy2(ROOT / 'tests/load/docker/MalleusSmoke.java', payload / 'MalleusSmoke.java')
    shutil.copy2(ROOT / 'tests/load/docker/MalleusSmoke.java', source / 'src/test/java/MalleusSmoke.java')
    shutil.copy2(ROOT / 'tests/load/docker/smoke-testng.xml', payload / 'smoke-testng.xml')
    for name in ['Dockerfile.malleus', 'run-malleus-container.sh']:
        shutil.copy2(ROOT / 'tests/load/docker' / name, root / name)
    size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    print('Contexte public prepare en RAM :', size, 'bytes ; aucune image construite par ce script.')


if __name__ == '__main__':
    main()
