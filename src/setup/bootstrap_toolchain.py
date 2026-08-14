#!/usr/bin/env python
"""Fetch and pin the P2 network-build toolchain.

P2 needs three things this repository does not carry and cannot regenerate: a
JVM, the pt2matsim converter, and SUMO's `netconvert`. All three land under
`.tools/` (gitignored, ~700 MB unpacked) and every one is pinned by version
**and** by sha256, so a rebuilt toolchain is the same toolchain.

    JDK        Eclipse Temurin 25 - pt2matsim 26.6's pom sets <release>25</release>,
               so a 21 JDK will not load its classes.
    pt2matsim  the published *shaded* jar. It carries MATSim and every transitive
               dependency and declares PublicTransitMapper as its Main-Class, so
               neither Maven nor a build step is required.
    SUMO       the eclipse-sumo wheel, installed into an isolated venv purely to
               obtain netconvert. SUMO publishes no GitHub release assets; the
               wheel is the only pinnable Windows distribution.

Writes `.tools/toolchain.json`: version, source URL, sha256 and retrieval date
for each component - the provenance record for the tools, mirroring what
`data/raw/provenance_*.json` does for the data.

Usage:
    python src/setup/bootstrap_toolchain.py            # fetch what is missing
    python src/setup/bootstrap_toolchain.py --verify   # check digests, fetch nothing
"""
import os
import sys
import glob
import json
import shutil
import hashlib
import zipfile
import datetime
import argparse
import subprocess
import urllib.request

TOOLS = '.tools'

# ---------------------------------------------------------------------------
# Pins. Changing any of these is a toolchain change: re-run, re-hash and record
# it in DECISIONS.md - a different netconvert can move a corridor result.
# ---------------------------------------------------------------------------
JDK_VERSION = '25.0.4+7'
JDK_URL = ('https://github.com/adoptium/temurin25-binaries/releases/download/'
           'jdk-25.0.4%2B7/OpenJDK25U-jdk_x64_windows_hotspot_25.0.4_7.zip')
JDK_SHA256 = '7caab7db43bf4b94a2e6252c699e70d90084f9aa7c943cd3414761fd540937ae'
JDK_DIRNAME = 'jdk-25.0.4+7'

PT2MATSIM_VERSION = '26.6'
PT2MATSIM_URL = ('https://repo.matsim.org/repository/matsim/org/matsim/pt2matsim/'
                 '26.6/pt2matsim-26.6-shaded.jar')

SUMO_VERSION = '1.27.1'

LICENCES = {
    'jdk': 'GPLv2 with Classpath Exception (Eclipse Temurin)',
    'pt2matsim': 'GPL-2.0 (pt2matsim); bundles MATSim, GPL-2.0',
    'sumo': 'EPL-2.0 (Eclipse SUMO)',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def download(url, dest, expect=None):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and (expect is None or sha256(dest) == expect):
        print('   cached  %s' % os.path.basename(dest))
        return sha256(dest)
    print('   fetch   %s' % url)
    tmp = dest + '.part'
    with urllib.request.urlopen(url, timeout=300) as r, open(tmp, 'wb') as f:
        shutil.copyfileobj(r, f, 1 << 20)
    got = sha256(tmp)
    if expect and got != expect:
        os.remove(tmp)
        raise SystemExit('digest mismatch for %s\n  expected %s\n  got      %s'
                         % (url, expect, got))
    os.replace(tmp, dest)
    print('   ok      %s  %.1f MB  sha256=%s' % (os.path.basename(dest),
                                                 os.path.getsize(dest) / 1e6, got[:16]))
    return got


def jdk_archive():
    return os.path.join(TOOLS, 'dl', JDK_URL.split('/')[-1])


def install_jdk():
    home = os.path.join(TOOLS, 'jdk')
    digest = download(JDK_URL, jdk_archive(), JDK_SHA256)
    if not java_path():
        print('   unpack  JDK %s' % JDK_VERSION)
        stage = os.path.join(TOOLS, '_jdk_stage')
        shutil.rmtree(stage, ignore_errors=True)
        with zipfile.ZipFile(jdk_archive()) as z:
            z.extractall(stage)
        src = os.path.join(stage, JDK_DIRNAME)
        if not os.path.isdir(src):
            cands = [d for d in sorted(os.listdir(stage))
                     if os.path.isdir(os.path.join(stage, d))]
            src = os.path.join(stage, cands[0])
        shutil.rmtree(home, ignore_errors=True)
        shutil.move(src, home)
        shutil.rmtree(stage, ignore_errors=True)
    return dict(component='jdk', version=JDK_VERSION, url=JDK_URL, sha256=digest,
                home=home.replace('\\', '/'), licence=LICENCES['jdk'])


def install_pt2matsim():
    jar = os.path.join(TOOLS, 'jars', 'pt2matsim-%s-shaded.jar' % PT2MATSIM_VERSION)
    digest = download(PT2MATSIM_URL, jar)
    return dict(component='pt2matsim', version=PT2MATSIM_VERSION, url=PT2MATSIM_URL,
                sha256=digest, jar=jar.replace('\\', '/'), licence=LICENCES['pt2matsim'])


def install_sumo():
    venv = os.path.join(TOOLS, 'sumo-venv')
    py = venv_python(venv)
    if not py:
        print('   venv    %s' % venv)
        subprocess.check_call([sys.executable, '-m', 'venv', venv])
        py = venv_python(venv)
    if not netconvert_path():
        print('   pip     eclipse-sumo==%s' % SUMO_VERSION)
        subprocess.check_call([py, '-m', 'pip', 'install', '--quiet', '--no-input',
                               'eclipse-sumo==%s' % SUMO_VERSION])
    nc = netconvert_path()
    if not nc:
        raise SystemExit('netconvert not found after installing eclipse-sumo')
    return dict(component='sumo', version=SUMO_VERSION,
                url='https://pypi.org/project/eclipse-sumo/%s/' % SUMO_VERSION,
                sha256=sha256(nc), netconvert=nc.replace('\\', '/'),
                sumo_home=sumo_home().replace('\\', '/'), licence=LICENCES['sumo'])


def venv_python(venv):
    for cand in (os.path.join(venv, 'Scripts', 'python.exe'),
                 os.path.join(venv, 'bin', 'python')):
        if os.path.exists(cand):
            return cand
    return ''


def _site_dirs():
    venv = os.path.join(TOOLS, 'sumo-venv')
    for sub in (('Lib', 'site-packages'), ('lib', 'site-packages')):
        d = os.path.join(venv, *sub)
        if os.path.isdir(d):
            yield d
    lib = os.path.join(venv, 'lib')
    if os.path.isdir(lib):
        for d in sorted(os.listdir(lib)):
            sp = os.path.join(lib, d, 'site-packages')
            if os.path.isdir(sp):
                yield sp


def sumo_home():
    for sp in _site_dirs():
        h = os.path.join(sp, 'sumo')
        if os.path.isdir(h):
            return h
    return ''


def netconvert_path():
    h = sumo_home()
    if not h:
        return ''
    for cand in (os.path.join(h, 'bin', 'netconvert.exe'),
                 os.path.join(h, 'bin', 'netconvert')):
        if os.path.exists(cand):
            return cand
    return ''


JAVA_SRC = os.path.join('src', 'java')
CLASSES = os.path.join(TOOLS, 'classes')


def javac_path():
    for cand in (os.path.join(TOOLS, 'jdk', 'bin', 'javac.exe'),
                 os.path.join(TOOLS, 'jdk', 'bin', 'javac')):
        if os.path.exists(cand):
            return cand
    return None


def compile_java():
    """Compile the project's MATSim entry point against the pinned jar.

    `run_matsim.py` runs `wickham.WickhamControler`, not the stock MATSim
    Controler, because two bindings differ: ride availability (DECISIONS.md 9.11)
    and the ride travel time that issue #28 fixed. The source is committed;
    `.tools/` is not. Until this step existed the classes were built by hand, so
    a fresh checkout had the source, the jar and no way to run - the classpath
    would simply lack the main class. Compiling here, with the pinned javac
    against the pinned jar, is what makes a run reproducible from a clone.
    """
    javac = javac_path()
    jar = pt2matsim_jar()
    if not javac or not jar:
        print('\nskip javac: toolchain incomplete (javac=%s jar=%s)' % (javac, jar))
        return False
    srcs = sorted(glob.glob(os.path.join(JAVA_SRC, '*', '*.java')))
    if not srcs:
        print('\nno java sources under %s' % JAVA_SRC)
        return False
    os.makedirs(CLASSES, exist_ok=True)
    cmd = [javac, '-cp', jar, '-d', CLASSES] + srcs
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        print('\njavac FAILED\n%s' % (out.stderr or out.stdout))
        raise SystemExit(1)
    print('\njavac      %d source(s) -> %s' % (len(srcs), CLASSES))
    for src in srcs:
        print('             %s' % src.replace('\\', '/'))
    return True


def java_path():
    for cand in (os.path.join(TOOLS, 'jdk', 'bin', 'java.exe'),
                 os.path.join(TOOLS, 'jdk', 'bin', 'java')):
        if os.path.exists(cand):
            return cand
    return ''


def pt2matsim_jar():
    p = os.path.join(TOOLS, 'jars', 'pt2matsim-%s-shaded.jar' % PT2MATSIM_VERSION)
    return p if os.path.exists(p) else ''


def load_manifest():
    p = os.path.join(TOOLS, 'toolchain.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def require():
    """Return (java, jar, netconvert, sumo_home) or exit with instructions."""
    j, p, n = java_path(), pt2matsim_jar(), netconvert_path()
    if not (j and p and n):
        raise SystemExit(
            'toolchain incomplete (java=%s pt2matsim=%s netconvert=%s)\n'
            'run: python src/setup/bootstrap_toolchain.py' % (bool(j), bool(p), bool(n)))
    return j, p, n, sumo_home()


def verify():
    man = load_manifest()
    if not man:
        print('no .tools/toolchain.json - run without --verify first')
        return 1
    bad = 0
    for c in man['components']:
        target = {'jdk': jdk_archive(),
                  'pt2matsim': c.get('jar'),
                  'sumo': c.get('netconvert')}[c['component']]
        if not target or not os.path.exists(target):
            print('  MISSING  %-9s %s' % (c['component'], target))
            bad += 1
            continue
        got = sha256(target)
        ok = got == c['sha256']
        print('  %-8s %-9s %s' % ('ok' if ok else 'MISMATCH', c['component'], got[:16]))
        bad += 0 if ok else 1
    # The custom controler is part of the toolchain a run depends on, and its
    # classes live under the gitignored .tools/. Recompiling here keeps --verify
    # an honest statement that this checkout can actually run.
    if not bad:
        compile_java()
    print('toolchain %s' % ('OK' if not bad else 'FAILED'))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', action='store_true',
                    help='check recorded digests, download nothing')
    a = ap.parse_args()
    if a.verify:
        raise SystemExit(verify())

    os.makedirs(TOOLS, exist_ok=True)
    comps = []
    print('JDK:')
    comps.append(install_jdk())
    print('pt2matsim:')
    comps.append(install_pt2matsim())
    print('SUMO:')
    comps.append(install_sumo())

    man = dict(
        purpose='P2 network-build toolchain for NewcastleLRSIM',
        retrieved=datetime.date.today().isoformat(),
        platform=sys.platform,
        components=comps)
    with open(os.path.join(TOOLS, 'toolchain.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(man, f, indent=2)
        f.write('\n')

    compile_java()

    print('\njava       %s' % java_path())
    print('pt2matsim  %s' % pt2matsim_jar())
    print('netconvert %s' % netconvert_path())
    print('SUMO_HOME  %s' % sumo_home())
    for cmd in ([java_path(), '-version'], [netconvert_path(), '--version']):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            line = (out.stdout or out.stderr).strip().splitlines()[0]
            print('\n$ %s\n%s' % (' '.join(cmd), line))
        except Exception as e:
            print('could not run %s (%s)' % (cmd[0], e))


if __name__ == '__main__':
    main()
