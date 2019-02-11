=========
docshtest
=========

.. image:: http://img.shields.io/travis/vaab/docshtest/master.svg?style=flat
   :target: https://travis-ci.org/0k/sunit
   :alt: Travis CI build status


Doctest for Shell - Quick, Slim and Dirty


Feature
=======

- Quick way to write doctest in shell

- Slim because it has no dependencies to other project, one file, in python

- Doctest feeling

- You can mix python tests ans shell tests

- only checks standard output (although, you can tailor your test
  commands to output what is meaningful to standard output.)


Current Status
==============

This is an early alpha code.

Major concerns and shortcomings:

- end of blocks and final "\n" are not tested correctly
- tests execution in current directory with possible consequences.
- no support of checking errlvl
- no support of proper mixed err and stdout content
- limited to ``bash`` testing
- rough detection of doctest blocks relying on bash error output. Not
  sure this is very solid.

Minor concerns, but would be better without:

- fail on first error hard-written.
- hard-written support of "<BLANKLINE>"

Possible evolution:

- profiling
- support of python file (by extracting docs before)
- integration in nosetests ? is it possible ?
- colorize output ?
- move to standalone full fledged program ?
- coverage integration ?


Installation
============

No installation method provided yet, just copy the file in your path.


Usage
=====


QuickStart
----------

``docshtest`` is a ``doctest`` for shell command. This means it allows
you to integrate in your documentation some examples of shell code and
their expected output that will be actually checkable.

First please notice that these documentation lines you are reading are
stored in a ``README.rst`` file that will contain very soon some
examples of how to run ``docshtest`` and what outcome to expect.

The very first example that comes to mind is to run ``docshtest`` on
this very documentation::

    ./docshtest README.rst

But doing so would generate a infinite loop ! So you can check that
yourself, and that's done in the CI procedures.

Let's introduce you the basics of writing your own testable documentation...

So this is how it works::

    $ cat <<EOF > mydoc.rst   ## First test file

    This is standard RST, we can include runnable test blocks::

        $ echo 'hello world'
        hello world

    EOF

Note that indentation is required, as well as the ``$ `` (dollar sign
followed by a space) before the command to be executed. Please refer
to the following section to understand how ``docshtest`` figures out
the end of your shell code and the start of the output.

The output starts after the end of your command, indented also, and
will be matched with the actual command output. If there is a mismatch
the test will fail, and ``docshtest`` will cancel any remaining tests.
If it matches, next test block will be executed.

To run our test:

     $ ./docshtest mydoc.rst


Multiline Commands
------------------

Multiline commands are detected with a very simple, but dirty method,
``docshtest`` will simply provide the exact code, starting with only
the first line to the shell interpreter, if the shell interpreter
complains, it'll try again by adding the next line to the output.

This allows to document/test multi-line shell codes like:

    $ cat <<EOF > mydoc.rst   ## First test file

    Multiline commands::

        $ for a in \$(seq 1 3); do
            echo "foo$a"
          done
        foo1
        foo2
        foo3

    EOF
    $ ./docshtest mydoc.rst

Please note that the extra indentation for the body of the ``for`` loop or
the ``done`` is unnecessary, but is recommended for reading::

    $ cat <<EOF > mydoc.rst   ## First test file

    Multiline commands::

        $ for a in \$(seq 1 3); do
          echo "foo$a"
        done
        foo1
        foo2
        foo3

    EOF
    $ ./docshtest mydoc.rst



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
         docshtest README.rst -r '/\bshyaml\b/coverage run shyaml.py/'
    <BLANKLINE>
    <BLANKLINE>


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

Copyright (c) 2012-2019 Valentin Lab.

Licensed under the `BSD License`_.

.. _BSD License: http://raw.github.com/0k/sunit/master/LICENSE
