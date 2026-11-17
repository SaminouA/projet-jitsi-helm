#!/usr/bin/env python3
"""Liens locaux et syntaxe shell des livrables ; aucune commande documentaire executee."""
import re
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / 'README.md', *sorted((ROOT / 'docs').glob('*.md'))]


def main():
    errors = []
    links = blocks = 0
    external = set()
    for path in FILES:
        content = path.read_text()
        # Les exemples dans les blocs ne sont pas des liens documentaires.
        prose = re.sub(r'```.*?```', '', content, flags=re.S)
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', prose):
            target = match.group(1).strip().split(' "', 1)[0].strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme in ('http', 'https'):
                if not parsed.netloc:
                    errors.append(f'{path.relative_to(ROOT)} : URL externe mal formee')
                external.add(target)
                continue
            if parsed.scheme:
                continue
            if parsed.path:
                dest = (path.parent / unquote(parsed.path)).resolve()
                if not dest.is_file():
                    errors.append(f'{path.relative_to(ROOT)} : lien local absent : {parsed.path}')
                links += 1
        for number, match in enumerate(re.finditer(r'```(bash|sh)\s*\n(.*?)```', content, re.S), 1):
            language, code = match.groups()
            result = subprocess.run([language, '-n'], input=code, text=True, capture_output=True)
            if result.returncode:
                errors.append(f'{path.relative_to(ROOT)} : bloc {language} numero {number} invalide')
            blocks += 1
        if len(re.findall(r'^```', content, re.M)) % 2:
            errors.append(f'{path.relative_to(ROOT)} : cloture de bloc Markdown manquante')
    for error in errors:
        print(error)
    print(f'Documents : {len(FILES)} ; liens locaux : {links} ; blocs shell : {blocks} ; erreurs : {len(errors)}')
    print(f'URLs externes : {len(external)}, syntaxe seulement ; aucune requete HTTP ni commande de procedure executee.')
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
