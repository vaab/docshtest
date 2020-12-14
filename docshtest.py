#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Shell Doctest

"""

from __future__ import print_function


import re
import sys
import os.path
import difflib
import threading
import locale


from io import open

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x


PY3 = sys.version_info[0] >= 3
WIN32 = sys.platform == 'win32'

EXNAME = os.path.basename(__file__ if WIN32 else sys.argv[0])

if WIN32:
    import tempfile

## Note that locale.getpreferredencoding() does NOT follow
## PYTHONIOENCODING by default, but ``sys.stdout.encoding`` does. In
## PY2, ``sys.stdout.encoding`` without PYTHONIOENCODING set does not
## get any values set in subshells.  However, if _preferred_encoding
## is not set to utf-8, it leads to encoding errors.
_preferred_encoding = os.environ.get("PYTHONIOENCODING") or \
                      locale.getpreferredencoding()


for ext in (".py", ".pyc", ".exe", "-script.py", "-script.pyc"):
    if EXNAME.endswith(ext):
        EXNAME = EXNAME[:-len(ext)]
        break


##
## Python 2 and WIN32 bug correction
##

if WIN32 and not PY3:  ## noqa: C901

    ## Sorry about the following, all this code is to ensure full
    ## compatibility with python 2.7 under windows about sending unicode
    ## command-line

    import ctypes
    import subprocess
    import _subprocess
    from ctypes import byref, windll, c_char_p, c_wchar_p, c_void_p, \
         Structure, sizeof, c_wchar, WinError
    from ctypes.wintypes import BYTE, WORD, LPWSTR, BOOL, DWORD, LPVOID, \
         HANDLE

    ##
    ## Types
    ##

    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    LPCTSTR = c_char_p
    LPTSTR = c_wchar_p
    LPSECURITY_ATTRIBUTES = c_void_p
    LPBYTE = ctypes.POINTER(BYTE)

    class STARTUPINFOW(Structure):
        _fields_ = [
            ("cb",              DWORD),  ("lpReserved",    LPWSTR),
            ("lpDesktop",       LPWSTR), ("lpTitle",       LPWSTR),
            ("dwX",             DWORD),  ("dwY",           DWORD),
            ("dwXSize",         DWORD),  ("dwYSize",       DWORD),
            ("dwXCountChars",   DWORD),  ("dwYCountChars", DWORD),
            ("dwFillAtrribute", DWORD),  ("dwFlags",       DWORD),
            ("wShowWindow",     WORD),   ("cbReserved2",   WORD),
            ("lpReserved2",     LPBYTE), ("hStdInput",     HANDLE),
            ("hStdOutput",      HANDLE), ("hStdError",     HANDLE),
        ]

    LPSTARTUPINFOW = ctypes.POINTER(STARTUPINFOW)

    class PROCESS_INFORMATION(Structure):
        _fields_ = [
            ("hProcess",         HANDLE), ("hThread",          HANDLE),
            ("dwProcessId",      DWORD),  ("dwThreadId",       DWORD),
        ]

    LPPROCESS_INFORMATION = ctypes.POINTER(PROCESS_INFORMATION)

    class DUMMY_HANDLE(ctypes.c_void_p):

        def __init__(self, *a, **kw):
            super(DUMMY_HANDLE, self).__init__(*a, **kw)
            self.closed = False

        def Close(self):
            if not self.closed:
                windll.kernel32.CloseHandle(self)
                self.closed = True

        def __int__(self):
            return self.value

    CreateProcessW = windll.kernel32.CreateProcessW
    CreateProcessW.argtypes = [
        LPCTSTR, LPTSTR, LPSECURITY_ATTRIBUTES,
        LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID, LPCTSTR,
        LPSTARTUPINFOW, LPPROCESS_INFORMATION,
    ]
    CreateProcessW.restype = BOOL

    ##
    ## Patched functions/classes
    ##

    def CreateProcess(executable, args, _p_attr, _t_attr,
                      inherit_handles, creation_flags, env, cwd,
                      startup_info):
        """Create a process supporting unicode executable and args for win32

        Python implementation of CreateProcess using CreateProcessW for Win32

        """

        si = STARTUPINFOW(
            dwFlags=startup_info.dwFlags,
            wShowWindow=startup_info.wShowWindow,
            cb=sizeof(STARTUPINFOW),
            ## XXXvlab: not sure of the casting here to ints.
            hStdInput=int(startup_info.hStdInput),
            hStdOutput=int(startup_info.hStdOutput),
            hStdError=int(startup_info.hStdError),
        )

        wenv = None
        if env is not None:
            ## LPCWSTR seems to be c_wchar_p, so let's say CWSTR is c_wchar
            env = (unicode("").join([
                unicode("%s=%s\0") % (k, v)
                for k, v in env.items()])) + unicode("\0")
            wenv = (c_wchar * len(env))()
            wenv.value = env

        pi = PROCESS_INFORMATION()
        creation_flags |= CREATE_UNICODE_ENVIRONMENT

        if CreateProcessW(executable, args, None, None,
                          inherit_handles, creation_flags,
                          wenv, cwd, byref(si), byref(pi)):
            return (DUMMY_HANDLE(pi.hProcess), DUMMY_HANDLE(pi.hThread),
                    pi.dwProcessId, pi.dwThreadId)
        raise WinError()

    class Popen(subprocess.Popen):
        """This superseeds Popen and corrects a bug in cPython 2.7 implem"""

        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell, to_close,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Code from part of _execute_child from Python 2.7 (9fbb65e)

            There are only 2 little changes concerning the construction of
            the the final string in shell mode: we preempt the creation of
            the command string when shell is True, because original function
            will try to encode unicode args which we want to avoid to be able to
            sending it as-is to ``CreateProcess``.

            """
            if not isinstance(args, subprocess.types.StringTypes):
                args = subprocess.list2cmdline(args)

            if startupinfo is None:
                startupinfo = subprocess.STARTUPINFO()
            if shell:
                startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = _subprocess.SW_HIDE
                comspec = os.environ.get("COMSPEC", unicode("cmd.exe"))
                args = unicode('{} /c "{}"').format(comspec, args)
                if (_subprocess.GetVersion() >= 0x80000000 or
                        os.path.basename(comspec).lower() == "command.com"):
                    w9xpopen = self._find_w9xpopen()
                    args = unicode('"%s" %s') % (w9xpopen, args)
                    creationflags |= _subprocess.CREATE_NEW_CONSOLE

            super(Popen, self)._execute_child(
                args, executable,
                preexec_fn, close_fds, cwd, env, universal_newlines,
                startupinfo, creationflags, False, to_close, p2cread,
                p2cwrite, c2pread, c2pwrite, errread, errwrite)

    _subprocess.CreateProcess = CreateProcess
    from subprocess import PIPE
else:
    from subprocess import Popen, PIPE


class Phile(object):
    """File like API to read fields separated by any delimiters

    It'll take care of file decoding to unicode.

    This is an adaptor on a file object.

        >>> if PY3:
        ...     from io import BytesIO
        ...     def File(s):
        ...         _obj = BytesIO()
        ...         _obj.write(s.encode(_preferred_encoding))
        ...         _obj.seek(0)
        ...         return _obj
        ... else:
        ...     from cStringIO import StringIO as File

        >>> f = Phile(File("a-b-c-d"))

    Read provides an iterator:

        >>> def show(l):
        ...     print(", ".join(l))
        >>> show(f.read(delimiter="-"))
        a, b, c, d

    You can change the buffersize loaded into memory before outputing
    your changes. It should not change the iterator output:

        >>> f = Phile(File("é-à-ü-d"), buffersize=3)
        >>> len(list(f.read(delimiter="-")))
        4

        >>> f = Phile(File("foo-bang-yummy"), buffersize=3)
        >>> show(f.read(delimiter="-"))
        foo, bang, yummy

        >>> f = Phile(File("foo-bang-yummy"), buffersize=1)
        >>> show(f.read(delimiter="-"))
        foo, bang, yummy

    Empty file is considered one empty field::

        >>> f = Phile(File(""))
        >>> len(list(f.read(delimiter="-")))
        1

    """

    def __init__(self, filename, buffersize=4096, encoding=_preferred_encoding):
        self._file = filename
        self._buffersize = buffersize
        self._encoding = encoding

    def read(self, delimiter="\n"):
        buf = ""
        if PY3:
            delimiter = delimiter.encode(_preferred_encoding)
            buf = buf.encode(_preferred_encoding)
        while True:
            chunk = self._file.read(self._buffersize)
            if not chunk:
                yield buf.decode(self._encoding)
                return
            records = chunk.split(delimiter)
            records[0] = buf + records[0]
            for record in records[:-1]:
                yield record.decode(self._encoding)
            buf = records[-1]

    def write(self, buf):
        if PY3:
            buf = buf.encode(self._encoding)
        return self._file.write(buf)

    def close(self):
        return self._file.close()


class Proc(Popen):

    def __init__(self, command, env=None, encoding=_preferred_encoding):
        super(Proc, self).__init__(
            command, stdin=PIPE, stdout=PIPE, stderr=PIPE,
            close_fds=ON_POSIX, env=env,
            universal_newlines=False)

        self.stdin = Phile(self.stdin, encoding=encoding)
        self.stdout = Phile(self.stdout, encoding=encoding)
        self.stderr = Phile(self.stderr, encoding=encoding)


USAGE = """\
Usage:

    %(exname)s (-h|--help)
    %(exname)s [[-r|--regex REGEX] ...] DOCSHTEST_FILE
""" % {"exname": EXNAME}


HELP = """\

%(exname)s - parse file and run shell doctests

%(usage)s

Options:

    -r REGEX, --regex REGEX
              Will apply this regex to the lines to be executed. You
              can have more than one patterns by re-using this options
              as many times as wanted. Regexps will be applied one by one
              in the same order than they are provided on the command line.


Examples:

     ## run tests but replace executable on-the-fly for coverage support
     docshtest README.rst -r '/\\bdocshtest\\b/coverage run docshtest.py/'

""" % {"exname": EXNAME, "usage": USAGE}


## command line quoting
cmd_line_quote = (lambda e: e.replace('\\', '\\\\')) if WIN32 else (lambda e: e)


##
## Helpers coming from othe projects
##


## XXXvlab: code comes from kids.txt.diff
def udiff(a, b, fa="", fb=""):
    if not a.endswith("\n"):
        a += "\n"
    if not b.endswith("\n"):
        b += "\n"
    return "".join(
        difflib.unified_diff(
            a.splitlines(1), b.splitlines(1),
            fa, fb))


## XXXvlab: code comes from ``kids.sh``
ON_POSIX = 'posix' in sys.builtin_module_names

__ENV__ = {}


## XXXvlab: code comes from ``kids.txt``
## Note that a quite equivalent function was added to textwrap in python 3.3
def indent(text, prefix="  ", first=None):
    if first is not None:
        first_line = text.split("\n")[0]
        rest = '\n'.join(text.split("\n")[1:])
        return '\n'.join([first + first_line,
                          indent(rest, prefix=prefix)])
    return '\n'.join([prefix + line
                      for line in text.split('\n')])


## XXXvlab: consider for inclusion in ``kids.sh``
def cmd_iter(cmd):
    """Asynchrone subprocess driver

    returns an iterator that yields events of the life of the
    process.

    """

    def thread_enqueue(label, f, q):
        t = threading.Thread(target=enqueue_output, args=(label, f, q))
        t.daemon = True  ## thread dies with the program
        t.start()
        return t

    def enqueue_output(label, out, queue):
        prev_line = None
        for line in out.read():
            if prev_line is not None:
                queue.put((label, "%s\n" % prev_line))
            prev_line = line
            # print("%s: %r" % (label, line))
        # print("END of %s" % (label, ))
        if prev_line:
            queue.put((label, prev_line))
        out.close()

    proc = Proc(cmd)
    proc.stdin.close()
    q = Queue()
    t1 = thread_enqueue("out", proc.stdout, q)
    t2 = thread_enqueue("err", proc.stderr, q)
    running = True
    while True:
        try:
            yield q.get(True, 0.001)
        except Empty:
            if not running:
                break
            proc.poll()
            running = proc.returncode is None or \
                      any(t.is_alive() for t in (t1, t2))

    # print("%s: %r" % ("errlvl", proc.returncode))
    yield "errorlevel", proc.returncode


## XXXvlab: consider for inclusion in ``kids.txt``
def chomp(s):
    if len(s):
        lines = s.splitlines(True)
        last = lines.pop()
        return ''.join(lines + last.splitlines())
    else:
        return ''


def get_docshtest_blocks(lines):
    """Returns an iterator of shelltest blocks from an iterator of lines"""

    block = []
    consecutive_empty = 0
    for line_nb, line in enumerate(lines):
        is_empty_line = not line.strip()
        if not is_empty_line:
            if not line.startswith("    "):
                if block:
                    yield block[:-consecutive_empty] \
                          if consecutive_empty else block
                    block = []
                continue
            else:
                line = line[4:]
        if line.startswith("$ ") or block:
            if line.startswith("$ "):
                line = line[2:]
                if block:
                    yield block[:-consecutive_empty] \
                          if consecutive_empty else block
                    block = []
            if is_empty_line:
                consecutive_empty += 1
            else:
                consecutive_empty = 0
            block.append((line_nb + 1, line))
    if block:
        yield block[:-consecutive_empty] \
              if consecutive_empty else block


def bash_iter(cmd, syntax_check=False):
    cmd_seq = ["bash", ]
    if syntax_check:
        cmd_seq.append("-n")
    if WIN32:
        ## Encoding on windows command line is complicated, and
        ## it seems bash doesn't know how to handle this complexity
        ## as :
        ##   bash -c "echo é"   ## bash: $'echo \303\251': command not found
        ##   bash -c "echo ok"  ## ok
        with tempfile.TemporaryFile() as tf:
            tf.write(cmd.encode("utf-8"))
            tf.flush()
            cmd_seq.append(tf.name)
            for ev, value in cmd_iter(cmd_seq):
                yield ev, value
    else:
        cmd_seq.extend(["-c", cmd])
        for ev, value in cmd_iter(cmd_seq):
            yield ev, value


def valid_syntax(command):
    """Check if shell command if complete"""

    for ev, value in bash_iter(command, syntax_check=True):
        if ev == "err":
            if value.endswith("syntax error: unexpected end of file"):
                return False
            if "unexpected EOF while looking for matching" in value:
                return False
            if "here-document at line" in value:
                return False
    return value == 0


class UnmatchedLine(Exception):

    def __init__(self, *args):
        self.args = args


class Ignored(Exception):

    def __init__(self, *args):
        self.args = args


def run_and_check(command, expected_output):  ## noqa: C901
    global __ENV__
    meta_commands = list(get_meta_commands(command))
    for meta_command in meta_commands:
        if meta_command[0] == "ignore-if":
            if meta_command[1] in __ENV__:
                raise Ignored(*meta_command)
        if meta_command[0] == "ignore-if-not":
            if meta_command[1] not in __ENV__:
                raise Ignored(*meta_command)

    expected_output = expected_output.replace("<BLANKLINE>\n", "\n")
    orig_expected_output = expected_output
    output = ""
    diff = False
    for ev, value in bash_iter(command):
        if ev in ("err", "out"):
            if WIN32:
                value = value.replace("\r\n", "\n")
            output += value
            if not diff and expected_output.startswith(value):
                expected_output = expected_output[len(value):]
            else:
                diff = True
    if not diff and len(chomp(expected_output)):
        diff = True

    for meta_command in meta_commands:
        if meta_command[0] == "if-success-set":
            if not diff:
                __ENV__[meta_command[1]] = 1
                raise Ignored(*meta_command)
            else:
                raise Ignored(*meta_command)
    if diff:
        raise UnmatchedLine(output, orig_expected_output)
    return value == 0


def format_failed_test(message, command, output, expected):
    formatted = []
    formatted.append("command:\n%s" % indent(command, "| "))
    formatted.append("expected:\n%s" % indent(expected, "| ").strip())
    formatted.append("output:\n%s" % indent(output, "| ").strip())
    if len(expected.splitlines() + output.splitlines()) > 10:
        formatted.append(
            "diff:\n%s"
            % udiff(expected, output, "expected", "output").strip())

    formatted = '\n'.join(formatted)

    return "%s\n%s" % (message, indent(formatted, prefix="  "))


def apply_regex(patterns, s):
    for p in patterns:
        s = re.sub(p[0], p[1], s)
    return s


META_COMMAND_REGEX = '##? docshtest: (?P<cmd>.*)$'


def get_meta_commands(command):
    for m in re.finditer(META_COMMAND_REGEX, command):
        raw_cmd = m.groupdict()["cmd"]
        cmd = raw_cmd.strip()
        cmd = re.sub(' +', ' ', cmd)
        yield cmd.split(' ')


def shtest_runner(lines, regex_patterns):
    def _lines(start_line_nb, stop_line_nb):
        return (("lines %9s" % ("%s-%s" % (start_line_nb, stop_line_nb)))
                if start_line_nb != stop_line_nb else
                ("line %10s" % start_line_nb))

    for block_nb, block in enumerate(get_docshtest_blocks(lines)):
        lines = iter(block)
        command_block = ""
        start_line_nb = None
        stop_line_nb = None
        for line_nb, line in lines:
            start_line_nb = start_line_nb or line_nb
            command_block += line
            if valid_syntax(apply_regex(regex_patterns,
                                        command_block)):
                stop_line_nb = line_nb
                break
        else:
            raise ValueError("Invalid Block:\n%s"
                             % (indent(command_block, "   | ")))
        command_block = command_block.rstrip("\n\r")
        command_block = apply_regex(regex_patterns, command_block)
        try:
            run_and_check(command_block, "".join(line for _, line in lines))
        except UnmatchedLine as e:
            safe_print(format_failed_test(
                "#%04d - failure (%15s):"
                % (block_nb + 1, _lines(start_line_nb, stop_line_nb)),
                command_block,
                e.args[0],
                e.args[1]))
            exit(1)
        except Ignored as e:
            print("#%04d - ignored (%15s): %s"
                  % (block_nb + 1,
                     _lines(start_line_nb, stop_line_nb),
                     " ".join(e.args)))
        else:
            print("#%04d - success (%15s)"
                  % (block_nb + 1, _lines(start_line_nb, stop_line_nb)))
        sys.stdout.flush()


def split_quote(s, split_char='/', quote='\\'):
    r"""Split args separated by char, possibily quoted with quote char


        >>> tuple(split_quote('/pattern/replace/'))
        ('', 'pattern', 'replace', '')

        >>> tuple(split_quote('/pat\/tern/replace/'))
        ('', 'pat/tern', 'replace', '')

        >>> tuple(split_quote('/pat\/ter\n/replace/'))
        ('', 'pat/ter\n', 'replace', '')

    """

    buf = ""
    parse_str = iter(s)
    for char in parse_str:
        if char == split_char:
            yield buf
            buf = ""
            continue
        if char == quote:
            char = next(parse_str)
            if char != split_char:
                buf += quote
        buf += char
    yield buf


def safe_print(content):
    if not PY3:
        if isinstance(content, unicode):
            content = content.encode(_preferred_encoding)

    print(content, end='')
    sys.stdout.flush()


def main(args):
    pattern = None
    if any(arg in args for arg in ["-h", "--help"]):
        print(HELP)
        exit(0)

    patterns = []
    for arg in ["-r", "--regex"]:
        while arg in args:
            idx = args.index(arg)
            pattern = args[idx + 1]
            del args[idx + 1]
            del args[idx]
            if re.match('^[a-zA-Z0-9]$', pattern[0]):
                print("Error: regex %s should start with a delimiter char, "
                      "not an alphanumerical char." % pattern)
                print(USAGE)
                exit(1)
            parts = tuple(split_quote(pattern, split_char=pattern[0]))
            if not (parts[0] == parts[-1] == ''):
                print("Error: regex should start and"
                      "end with a delimiter char.")
                exit(1)
            parts = parts[1:-1]
            if len(parts) > 2:
                print("Error: Found too many delimiter char.")
                exit(1)
            patterns.append(parts)

    if len(args) == 0:
        print("Error: please provide a rst filename as argument."
              " (use '--help' option to get usage info)")
        exit(1)
    filename = args[0]
    if not os.path.exists(filename):
        print("Error: file %r not found." % filename)
        exit(1)
    shtest_runner(open(filename, encoding=_preferred_encoding),
                  regex_patterns=patterns)


def entrypoint():
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    entrypoint()
