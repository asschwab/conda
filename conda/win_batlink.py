"""
Generate batch scripts to allow conda to update Python in the root
environment in Windows.  conda cannot do this because it itself runs in
Python, and Windows will not allow writing to a dll that is open.

The scripts should remain as small as possible. Only those things that conda
itself cannot do should be in them. The rest should be done by conda.

The way this works is that when conda comes to an action that it cannot
perform (such as linking Python in the root environment), it serializes the
actions that it cannot perform into a batch script (that's what's done here in
this module), performs the rest of the actions that it can perform, calls this
script, and exits (see conda.plan.execute_plan()).

Implementation wise, the action serialization is just a custom batch file that
does the linking/unlinking of everything in the package list, written to
%PREFIX%\batlink.bat (note, we can assume that we have write permissions to
%PREFIX% because otherwise we wouldn't be able to install in the root
environment anyway (this issue only comes up when installing into the root
environment)). conda calls this script and exits.

Notes:

- `mklink /H` creates a hardlink on Windows NT 6.0 and later (i.e., Windows
Vista or later)
- On older systems, like Windows XP, `fsutil.exe hardlink create` creates
hard links.
- In either case, the order of the arguments is backwards: dest source

"""

from os.path import join, abspath, split
from distutils.spawn import find_executable

# Redirect stderr on the mkdirs to ignore errors about directories that
# already exist
BAT_LINK_HEADER = """\
@echo off
> NUL (
{mkdirs}
)

> NUL (
{links}
)
"""

# Hide stderr for this one because it warns about nonempty directories, like
# C:\Anaconda.
BAT_UNLINK_HEADER = """\
@echo off

> NUL (
{filedeletes}

{dirdeletes}
)
"""

WINXP_LINK = "fsutil.exe hardlink create {dest} {source}"

WINVISTA_LINK = "mklink /H {dest} {source}"

MAKE_DIR = "mkdir {dst_dir}"

FILE_DELETE = "del /Q {dest}"

DIR_DELETE = "rmdir /Q {dest}"

def make_bat_link(files, prefix, dist_dir):
    links = []
    has_mklink = find_executable('mklink')
    LINK =  WINVISTA_LINK if has_mklink else WINXP_LINK
    dirs = set()
    for file in files:
        source = abspath(join(dist_dir, file))
        fdn, fbn = split(file)
        dst_dir = join(prefix, fdn)
        dirs.add(abspath(dst_dir))
        dest = abspath(join(dst_dir, fbn))
        links.append(LINK.format(source=source, dest=dest))

    # mkdir will make intermediate directories, so we do not need to care
    # about the order
    mkdirs = [MAKE_DIR.format(dst_dir=dn) for dn in dirs]

    batchfile = BAT_LINK_HEADER.format(links='\n'.join(links),
                                       mkdirs='\n'.join(mkdirs))

    return batchfile

def make_bat_unlink(files, directories, prefix, dist_dir):
    filedeletes = [FILE_DELETE.format(dest=abspath(file)) for file in files]
    dirdeletes = [DIR_DELETE.format(dest=abspath(dir)) for dir in directories]
    batchfile = BAT_UNLINK_HEADER.format(filedeletes='\n'.join(filedeletes),
        dirdeletes='\n'.join(dirdeletes))

    return batchfile
