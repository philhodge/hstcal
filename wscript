import os, platform, shutil, sys

import Configure
import Options
import Scripting
import Task
import Utils
from TaskGen import extension

APPNAME = 'hstcal'
VERSION = '0.1'

top = '.'
out = 'build.' + platform.platform()

# A list of subdirectories to recurse into
SUBDIRS = [
    'applib',
    'cfitsio',
    'cvos',
    'hstio',
    'include',
    'pkg',
    'tables',
    ]

@extension('.f')
def process_fortran(self, node):
    o_node = node.change_ext('.o')
    self.create_task('fortran', [node], [o_node])
    self.add_obj_file(o_node.file())

# Have 'waf dist' create tar.gz files, rather than tar.bz2 files
Scripting.g_gz = 'gz'

option_parser = None
def set_options(opt):
    global option_parser
    
    opt.tool_options('compiler_cc')

    # Store the option_parser so we can use it to parse options from a
    # file
    option_parser = opt.parser
    
def configure(conf):
    import Options

    # Read in options from a file.  The file is just a set of
    # commandline arguments in the same syntax.  May be spread across
    # multiple lines.
    if os.path.exists('build.cfg'):
        fd = open('build.cfg', 'r')
        for line in fd.readlines():
            tokens = line.split()
            options, args = option_parser.parse_args(tokens)
            for key, val in options.__dict__.items():
                if Options.options.__dict__.get(key) is None:
                    Options.options.__dict__[key] = val
        fd.close()
    
    # Check for the existence of a C compiler
    conf.check_tool('compiler_cc')

    # NOTE: All of the variables in conf.env are defined for use by
    # wscript files in subdirectories.
    
    # Set the location of the hstcal include directory
    conf.env.INCLUDEDIR = os.path.join(
        os.path.abspath(conf.srcdir), 'include') # the hstcal include directory

    # A list of the local (hstcal) libraries that are typically linked
    # with the executables
    conf.env.LOCAL_LIBS = ['applib', 'xtables', 'hstio', 'cvos']

    # A list of external libraries that are typically linked with the
    # executables
    conf.env.EXTERNAL_LIBS = ['m']
    if sys.platform.startswith('sunos'):
            conf.env.EXTERNAL_LIBS += ['socket', 'nsl']

    # A list of paths in which to search for external libraries
    conf.env.LIBPATH = []
            
    # Find a suitable Fortran compiler
    for compiler in ('f77', 'gfortran'):
        try:
            conf.find_program(compiler, mandatory=True)
            conf.env.FORTRAN_COMPILER = compiler
            break
        except Configure.ConfigurationError:
            pass
    if conf.env.FORTRAN_COMPILER == []:
        raise Configure.ConfigurationError(
            "No Fortran compiler found.")

    conf.recurse('cfitsio')
    
def build(bld):
    # Add support for simple Fortran files.  This isn't a complete Fortran
    # solution, but it meets the simple .f -> .o mapping we use here.
    Task.simple_task_type(
        'fortran',
        bld.env.FORTRAN_COMPILER + ' -c ${SRC} -o ${TGT}',
        color='GREEN',
        ext_out='.o',
        ext_in='.f')

    # Recurse into all of the libraries
    for library in SUBDIRS:
        bld.recurse(library)
    bld.add_post_fun(post_build)
    
def post_build(bld):
    # WAF has its own way of dealing with build products.  We want to
    # emulate the old stsdas way of creating a flat directory full of
    # .a and .e files.
    src_root = bld.srcnode.abspath(bld.env)
    dst_root = os.path.join(
        bld.srcnode.abspath(),
        'bin.' + platform.platform())
    
    if not os.path.exists(dst_root):
        os.mkdir(dst_root)
        
    for root, dirs, files in os.walk(src_root):
        for file in files:
            base, ext = os.path.splitext(file)
            if ext in ('.e', '.a'):
                src_path = os.path.join(root, file)
                dst_path = os.path.join(dst_root, file)
                shutil.copy(src_path, dst_path)
                
def clean(ctx):
    bin_root = 'bin.' + platform.platform()
    if os.path.exists(bin_root):
        shutil.rmtree(bin_root)
    # CFITSIO is built using its own standard Makefile
    Utils.cmd_output('cd cfitsio; make clean; cd ..')
    Scripting.clean(ctx)
