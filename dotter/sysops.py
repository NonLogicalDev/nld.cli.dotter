import shutil
import logging
import os
import stat
import errno

from distutils.dir_util import copy_tree
from .utils import yes_no_prompt, PP

class SysOps:
    log = logging.getLogger("SysOps")

    def __init__(self, dry_run=True, force=False, backup=False):
        self.log.debug("[INIT] Args: [dry_run: {}, force: {}, backup: {}]".format(dry_run, force, backup))

        self.dry_run = dry_run
        self.force = force
        self.backup = backup

    def ensure_folder(self, path, force=None):
        if not os.path.isdir(path):
            self.ensure_folder(self._dirname(path))

            PP.yellow("FOLDER : {}".format(path))
            if not self.dry_run:
                try:
                    os.mkdir(path)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        if self.force:
                            if yes_no_prompt("Should replace file {} with folder?".format(path)):
                                os.remove(path)
                                os.mkdir(path)
                        else:
                            raise RuntimeError("Can not create {}".format(e.filename))
                    else:
                        raise

    def touch(self, src, dest, force=None):
        src = self._path_sanitize(src)
        dest = self._path_sanitize(dest)

        if force is None:
            force = self.force

        self.ensure_folder(self._dirname(dest), force=force)

        if self._exists(dest):
            PP.green("[E]TOCH: {}\n -> {}".format(src, dest))
            return

        PP.yellow("TOCH   : {}\n -> {} (force:{})".format(src, dest, force))
        if not self.dry_run:
            self._copy(src, dest)

    def copy(self, src, dest, force=None):
        src = self._path_sanitize(src)
        dest = self._path_sanitize(dest)

        if force is None:
            force = self.force

        self.ensure_folder(self._dirname(dest), force=force)

        def do_copy():
            PP.yellow("COPY   : {}\n -> {} (force:{})".format(src, dest, force))
            if not self.dry_run:
                self._copy(src, dest)

        if self._exists(dest):
            diff_code = os.popen("diff -q '{}' '{}'".format(src, dest)).close()
            if diff_code is None:
                PP.green("[E]COPY: {}\n -> {}".format(src, dest))
                return
            else:
                PP.blue("[D]COPY: {}\n -> {}".format(src, dest))
                if self.force and yes_no_prompt("CO: Replace {} with {}?".format(dest, src)):
                    PP.red("     RM: {}".format(src, dest))
                    self._remove(dest)

                    do_copy()
                    return
        else:
            PP.green("[D]COPY: {}\n :: {}".format(src, dest))

            do_copy()
            return

    def link(self, src, dest, force=None):
        src = self._path_sanitize(src)
        dest = self._path_sanitize(dest)

        if force is None:
            force = self.force

        self.ensure_folder(self._dirname(dest), force=force)

        def do_link():
            PP.yellow("   LINK: {}\n -> {} (force:{})".format(src, dest, force))
            if not self.dry_run:
                self._link(src, dest)

        if self._exists(dest):
            if os.path.realpath(dest) == os.path.realpath(src):
                PP.green("[E]LINK: {}\n -> {}".format(src, dest))
                return
            else:
                PP.blue("[D]LINK: {}\n :: {}".format(src, dest))
                if self.force and yes_no_prompt("LN: Replace {} with {}?".format(dest, src)):
                    PP.red("     RM: {}".format(dest))
                    self._remove(dest)

                    do_link()
                    return
        else:
            PP.blue("[D]LINK: {}\n :: {}".format(src, dest))

            do_link()
            return

    # { Abstracted Low Level Ops }
    def _link(self, src, dest):
        os.symlink(src, dest)

    def _copy(self, src, dest):
        if os.path.isdir(src):
            copy_tree(src, dest)
        else:
            shutil.copy(src, dest)

    def _remove(self, path):
        try:
            dest_mod = os.stat(path).st_mode
        except:
            dest_mod = None

        if dest_mod is not None and stat.S_ISDIR(dest_mod):
            shutil.rmtree(path)
        else:
            os.remove(path)

    # { Abstracted Low Level Queries }

    def _exists(self, path):
        return os.path.exists(path) or os.path.islink(path)

    def _dirname(self, path):
        return os.path.dirname(self._path_sanitize(path))

    def _path_sanitize(self, path):
        if path[-1] == "/":
            path = path[:-1]
        return path
