=========
docshtest
=========

.. image:: https://img.shields.io/pypi/v/docshtest.svg
    :target: https://pypi.python.org/pypi/docshtest

.. image:: https://img.shields.io/travis/vaab/docshtest/master.svg?style=flat
   :target: https://travis-ci.org/vaab/docshtest/
   :alt: Travis CI build status

.. image:: https://img.shields.io/appveyor/ci/vaab/docshtest.svg
   :target: https://ci.appveyor.com/project/vaab/docshtest/branch/master
   :alt: Appveyor CI build status

.. image:: http://img.shields.io/codecov/c/github/vaab/docshtest.svg?style=flat
   :target: https://codecov.io/gh/vaab/docshtest/
   :alt: Test coverage


Doctest for Shell - Quick, Slim and Dirty


Feature
=======

- Quick way to write doctest in shell

- Works on Windows, Linux, Python 2.7, Python 3.5+

- Slim because it has no dependencies to other project, one file, in python

- Doctest feeling

- You can mix python tests ans shell tests

- only checks standard output (although, you can tailor your test
  commands to output what is meaningful to standard output.)


Current Status
==============

This is an early alpha code.

Major concerns and shortcomings:

- end of blocks and final ``\n`` are not tested correctly
- tests execution in current directory with possible consequences.
- no support of checking error level
- no support of proper mixed standard error and standard output content
- limited to ``bash`` testing (needs ``bash -n`` equivalent)
- rough detection of ``doctests`` command blocks is relying on ``bash
  -n`` error output. Not sure this is very solid.

Minor concerns, but would be better without:

- fail on first error hard-written.
- hard-written support of ``<BLANKLINE>``

Possible evolution:

- profiling
- support of python file (by extracting docs before)
- integration in nosetests ? is it possible ?
- colorize output ?
- coverage integration ?


Installation
============

You don't need to download the GIT version of the code as ``docshtest`` is
available on the PyPI. So you should be able to run::

    pip install docshtest

If you have downloaded the GIT sources, then you could add install
the current version via traditional::

    python setup.py install

And if you don't have the GIT sources but would like to get the latest
master or branch from github, you could also::

    pip install git+https://github.com/vaab/docshtest

Or even select a specific revision (branch/tag/commit)::

    pip install git+https://github.com/vaab/docshtest@master


Usage
=====


QuickStart
----------

``docshtest`` is a ``doctest`` for shell command. This means it allows
you to integrate in your documentation some examples of shell code and
their expected output that will be actually verifiable.

First please notice that these documentation lines you are reading are
stored in a ``README.rst`` file that will contain very soon some
examples of how to run ``docshtest`` and what outcome to expect.

The very first example that comes to mind is to run ``docshtest`` on
this very documentation::

    docshtest README.rst

You can check that yourself, and that's done in the CI procedures.

Let's introduce you the basics of writing your own testable
documentation...

So this is how it works::

    $ cat <<'EOF' > mydoc.rst   ## First test file

    This is standard RST, we can include runnable test blocks::

        $ echo 'hello world'
        hello world

    EOF

Note that indentation is required, as well as the ``"$ "`` (dollar sign
followed by a space) before the command to be executed. Please refer
to the following section to understand how ``docshtest`` figures out
the end of your shell code and the start of the output.

The output starts after the end of your command, indented also, and
will be matched with the actual command output. If there is a mismatch
the test will fail, and ``docshtest`` will cancel any remaining tests.
If it matches, next test block will be executed.

To run our test::

    $ ./docshtest mydoc.rst
    #0001 - success (line          4)


Multiline Commands
------------------

Multiline commands are detected with a very simple, but dirty method,
``docshtest`` will simply provide the exact code, starting with only
the first line to the shell interpreter, if the shell interpreter
complains, it'll try again by adding the next line to the output.

This allows to document/test multi-line shell codes like::

    $ cat <<EOF > mydoc.rst   ## First test file

    Multiline commands::

        $ for a in \$(seq 1 3); do
            echo "foo\$a"
          done
        foo1
        foo2
        foo3

    EOF
    $ ./docshtest mydoc.rst
    #0001 - success (lines       4-6)

Please note that the extra indentation for the body of the ``for`` loop or
the ``done`` is unnecessary, but is recommended for reading::

    $ cat <<EOF > mydoc.rst   ## First test file

    Multiline commands::

        $ for a in \$(seq 1 3); do
          echo "foo\$a"
        done
        foo1
        foo2
        foo3

    EOF
    $ ./docshtest mydoc.rst
    #0001 - success (lines       4-6)


Failing test will display both expected output and current output::

    $ cat <<EOF > mydoc.rst   ## First test file

    Multiline commands::

        $ for a in \$(seq 1 3); do
          echo "foo\$a"
        done
        foo1
        foo4
        foo3

    EOF
    $ ./docshtest mydoc.rst
    #0001 - failure (lines       4-6):
      command:
      | for a in $(seq 1 3); do
      |   echo "foo$a"
      | done
      expected:
      | foo1
      | foo4
      | foo3
      |
      output:
      | foo1
      | foo2
      | foo3
      |

But note that if these outputs are bigger, a standard unified diff will be
printed::

    $ cat <<EOF > mydoc.rst   ## First test file

    Multiline commands::

        $ for a in \$(seq 1 6); do
          echo "foo\$a"
        done
        foo1
        foo3
        foo4
        foo5
        foo6

    EOF
    $ ./docshtest mydoc.rst
    #0001 - failure (lines       4-6):
      command:
      | for a in $(seq 1 6); do
      |   echo "foo$a"
      | done
      expected:
      | foo1
      | foo3
      | foo4
      | foo5
      | foo6
      |
      output:
      | foo1
      | foo2
      | foo3
      | foo4
      | foo5
      | foo6
      |
      diff:
      --- expected
      +++ output
      @@ -1,4 +1,5 @@
       foo1
      +foo2
       foo3
       foo4
       foo5


Tinkering all executed code
---------------------------

You can transform all executed code before execution thanks to
``--regex REGEX`` (or ``-r REGEX``) option::

    $ cat <<'EOF' > mydoc.rst   ## First test file

    Our tested command is 'foo'

        $ foo 'hello world'
        hello world

    EOF
    $ ./docshtest -r '#\bfoo\b#echo#' mydoc.rst
    #0001 - success (line          4)


Conditional Tests
-----------------

You might want to have conditional tests, that are triggered only
on if specific test succeeds. This feature uses ``meta`` commands
that are specified as shell comments in the given block::

    $ cat <<'EOF' > mydoc.rst

    Our tested command is 'foo'

        $ echo $ENVVAR       ## docshtest: if-success-set VAR_WAS_SET
        0
        $ echo 'var is set'  ## docshtest: ignore-if VAR_WAS_SET
        SHOULDFAIL
        $ echo 'var is not set'  ## docshtest: ignore-if-not VAR_WAS_SET
        SHOULDFAIL

    EOF
    $ ENVVAR=0 ./docshtest mydoc.rst
    #0001 - ignored (line          4): if-success-set VAR_WAS_SET
    #0002 - ignored (line          6): ignore-if VAR_WAS_SET
    #0003 - failure (line          8):
      command:
      | echo 'var is not set'  ## docshtest: ignore-if-not VAR_WAS_SET
      expected:
      | SHOULDFAIL
      |
      output:
      | var is not set
      |


Encoding
--------

``docshtest`` will assume everything is "UTF-8"::

    $ cat <<'EOF' > mydoc.rst

    Our tested command is 'foo'

        $ echo "éà"
        éà
        $ echo "é"
        e

    EOF

    $ ./docshtest mydoc.rst
    #0001 - success (line          4)
    #0002 - failure (line          6):
      command:
      | echo "é"
      expected:
      | e
      |
      output:
      | é
      |


Command line
------------

``docshtest`` supports the common GNU standard ``--help`` options::

    $ ./docshtest --help

    docshtest - parse file and run shell doctests

    Usage:

        docshtest (-h|--help)
        docshtest [[-r|--regex REGEX] ...] DOCSHTEST_FILE


    Options:

        -r REGEX, --regex REGEX
                  Will apply this regex to the lines to be executed. You
                  can have more than one patterns by re-using this options
                  as many times as wanted. Regexps will be applied one by one
                  in the same order than they are provided on the command line.


    Examples:

         ## run tests but replace executable on-the-fly for coverage support
         docshtest README.rst -r '/\bdocshtest\b/coverage run docshtest.py/'
    <BLANKLINE>
    <BLANKLINE>

First argument is necessary::

    $ ./docshtest
    Error: please provide a rst filename as argument. (use '--help' option to get usage info)

And of course it should be the path of a file::

    $ ./docshtest notexistent
    Error: file 'notexistent' not found.


Contributing
============

Any suggestion or issue is welcome. Push request are very welcome,
please check out the guidelines.


Push Request Guidelines
-----------------------

You can send any code. I'll look at it and will integrate it myself in
the code base and leave you as the author. This process can take time and
it'll take less time if you follow the following guidelines:

- Try to stick to 80 columns wide.
- separate your commits per smallest concern.
- each commit should pass the tests (to allow easy bisect)
- each functionality/bugfix commit should contain the code, tests,
  and doc.
- prior minor commit with typographic or code cosmetic changes are
  very welcome. These should be tagged in their commit summary with
  ``!minor``.
- the commit message should follow gitchangelog rules (check the git
  log to get examples)
- if the commit fixes an issue or finished the implementation of a
  feature, please mention it in the summary.

If you have some questions about guidelines which is not answered here,
please check the current ``git log``, you might find previous commit that
would show you how to deal with your issue.


License
=======

Copyright (c) 2012-2020 Valentin Lab.

Licensed under the `BSD License`_.

.. _BSD License: http://raw.github.com/0k/sunit/master/LICENSE
