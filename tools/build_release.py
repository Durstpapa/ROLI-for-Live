"""Builds dist/ROLI-for-Live-v<version>.zip with double-click installers for Windows and macOS.

Usage: py -3.11 tools/build_release.py
"""
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(ROOT, 'src', 'ROLI_for_Live')


def version():
    text = open(os.path.join(SCRIPT_DIR, '__init__.py')).read()
    return re.search(r"__version__ = '([^']+)'", text).group(1)


def main():
    ver = version()
    top = 'ROLI-for-Live-v%s' % ver
    out_dir = os.path.join(ROOT, 'dist')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, top + '.zip')

    files = [  # (source, path in zip, executable)
        (os.path.join(ROOT, 'packaging', 'Install on Windows.cmd'), 'Install on Windows.cmd', False),
        (os.path.join(ROOT, 'packaging', 'Install on Mac.command'), 'Install on Mac.command', True),
        (os.path.join(ROOT, 'install.ps1'), 'install.ps1', False),
        (os.path.join(ROOT, 'install.sh'), 'install.sh', True),
        (os.path.join(ROOT, 'README.md'), 'README.md', False),
        (os.path.join(ROOT, 'LICENSE'), 'LICENSE', False),
        (os.path.join(ROOT, 'CHANGELOG.md'), 'CHANGELOG.md', False),
    ]
    for name in sorted(os.listdir(SCRIPT_DIR)):
        if name.endswith('.py'):
            files.append((os.path.join(SCRIPT_DIR, name), 'ROLI_for_Live/' + name, False))

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for src, arc, executable in files:
            data = open(src, 'rb').read()
            if arc.endswith(('.command', '.sh')):
                data = data.replace(b'\r\n', b'\n')  # shell scripts must have Unix line endings
            elif arc.endswith('.cmd'):
                data = data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            info = zipfile.ZipInfo('%s/%s' % (top, arc), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # Unix, so the permission bits below are honoured on macOS
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            z.writestr(info, data)
    print(out)


if __name__ == '__main__':
    main()
