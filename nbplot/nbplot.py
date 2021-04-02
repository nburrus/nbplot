#!/usr/bin/env python3

# This file is part of nbplot. See LICENSE for details.

import logging
from logging import debug, info, warning, error, critical

import base64
from collections import namedtuple
from datetime import datetime
import io
import os
from pathlib import Path
import re
import shutil
import string
import sys
from types import SimpleNamespace
import webbrowser

# To parse/write notebooks
import nbformat

# To launch or reuse a server.
from notebook.utils import exists, url_path_join, url_escape
from notebook import notebookapp
from traitlets.config import Config

from .delim import guess_delimiter
from .utils import ask_confirmation, StringTemplateWithDot, LoggingLevelContext

here_path = Path(__file__).parent

# A template is a metadata dict and a list of cells.
Template = namedtuple('Template', ['metadata', 'cells'])

# Data associated to an input file or stdin. Will be used to
# replace variables in templates.
Input = namedtuple('Input', ['pretty_name', 'rel_path', 'abs_path_or_io', 'guessed_sep'])

# Global variables shared across all functions.
shared = SimpleNamespace(
    # Dict of templates, indexed by name
    templates={},  # dict[str,Template]

    # Default config, will get overwritten
    config={
        'jupyter_notebook_working_directory': Path().home(),
        'generated_plots_directory': Path().home() / 'nbplots',
    },

    inputs=[]  # list[Input]
)

def parse_command_line():
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Command-line utility to quickly plot files in a Jupyter notebook.')

    parser.add_argument("files_to_plot", nargs="+", type=Path,
                        help="Files to plot. Use '-' for stdin.")

    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output ipynb file. If unspecified, a filename with the date will be generated.")

    parser.add_argument("--verbose", "-v", action='store_true',
                        help="Show more logging.")

    parser.add_argument("--debug", action='store_true',
                        help="Show even more logging.")

    parser.add_argument("--generate-only", "-g", action='store_true',
                        help="Only generate the notebook, don't open it.")

    parser.add_argument("--template", "-t", type=str, default=None,
                        help="Force a specific template (e,g: pandas or numpy)")

    args = parser.parse_args()
    return args

def load_notebook(nbpath):
    """Parse a template or config notebook"""
    nb = nbformat.read(nbpath, as_version=4)
    for cell in nb.cells:
        first_line = cell_first_line(cell)
        if first_line == '# [[nbplot]] template':
            return load_template(nb, nbpath)
        elif first_line == '# [[nbplot]] config':
            return load_config(nb, nbpath)
    warning(f"Ignoring notebook {nbpath}, did not find any [[nbplot]] metadata")

def load_template(nb, nbpath):
    """Parse a template notebook and save it in the shared.templates"""
    template_metadata = {}
    template_cells = []
    template_name = None

    # First find the special cell with [[nbplot]] template and
    # evaluate the metadata, looking for the name. Cells before
    # that special cell will just be ignored.
    first_cell_index_to_parse = 0
    for i, cell in enumerate(nb.cells):
        first_line = cell_first_line(cell)
        if first_line != '# [[nbplot]] template':
            continue

        cell_locals = {}
        exec(cell.source, {}, cell_locals)
        if 'template_metadata' not in cell_locals:
            error(f"Could not find the template_metadata dict in {nbpath}")
            sys.exit(1)
        template_metadata.update(cell_locals['template_metadata'])

        if 'name' not in template_metadata:
            error(f"Could not find a name field in the template_metadata of {nbpath}")
            sys.exit(1)

        template_name = template_metadata['name']
        first_cell_index_to_parse = i + 1
        break

    debug(f'Found {template_name}')

    # Now just add the remaining cells to the template dict.
    for cell in nb.cells[first_cell_index_to_parse:]:
        first_line = cell_first_line(cell)
        if first_line != '# [[nbplot]] ignore':
            template_cells.append(cell)

    shared.templates[template_name] = Template(metadata=template_metadata, cells=template_cells)

def load_config(nb, nbpath):
    """Load a configuration notebook, evaluating the [[nbplot]] config cell."""
    for cell in nb.cells:
        first_line = cell_first_line(cell)
        if first_line != '# [[nbplot]] config':
            continue

        cell_locals = {}
        exec(cell.source, {'inputs': shared.inputs}, cell_locals)
        if 'config' in cell_locals:
            shared.config.update(cell_locals['config'])
            debug('Found config dictionary')
            plots_dir = Path(shared.config['generated_plots_directory'])
            notebook_dir = Path(shared.config['jupyter_notebook_working_directory'])
            try:
                plots_dir.relative_to(notebook_dir)
            except Exception:
                error(f"Configuration error, the generated_plots_directory `{plots_dir}' must be a subdirectory of the jupyter_notebook_working_directory `{notebook_dir}'.")
                sys.exit(1)

def cell_first_line(cell):
    """Return the first line of a cell source"""
    return cell.source.partition('\n')[0] if len(cell.source) > 0 else ''

def load_source_code_from_notebooks(args):
    """Load all the notebooks from the templates/ directory and from the user .nbplot folder"""

    # First load the code content from the system templates
    for nbpath in sorted((here_path / 'templates').glob('*.ipynb')):
        debug(f'Loading {nbpath}...')
        load_notebook(nbpath)

    # Next overwrite the cells also defined in the config notebook.
    # If the user has no config we'll generate one.
    user_templates_path = Path().home() / '.nbplot'
    if not user_templates_path.exists():
        os.makedirs(user_templates_path)

    user_config_path = user_templates_path / 'config.ipynb'
    if not user_config_path.exists():
        try:
            info(f"Generating a config file in {user_config_path}")
            shutil.copy(here_path / 'nbplot-user-config.ipynb', user_config_path)
        except Exception as e:
            error(f"could not create {user_config_path}.")

    for nbpath in sorted(user_templates_path.glob('*.ipynb')):
        info(f'Loading {nbpath}...')
        load_notebook(nbpath)

def transform_input_source(args, globally_replaced_source):
    """Parse special for loops in a template source cell and replace special variables"""

    processed_source = ""

    in_foreach = False
    lines_in_foreach = ""
    for line in io.StringIO(globally_replaced_source):
        if line.rstrip() == '# [[nbplot]] for i,input in enumerate(inputs)':
            if in_foreach:
                error("Parse error in {nbpath}: endfor missing")
                sys.exit(1)
            in_foreach = True
            lines_in_foreach = ""
        elif line.rstrip() == '# [[nbplot]] endfor':
            in_foreach = False
            for i, input in enumerate(shared.inputs):
                # Add a new line between files.
                if i > 0:
                    processed_source += '\n'

                processed_source += StringTemplateWithDot(lines_in_foreach).safe_substitute({
                    'root_path': Path.cwd(),
                    'input.pretty_name': input.pretty_name,
                    'input.rel_path': input.rel_path,
                    'input.abs_path_or_io': input.abs_path_or_io,
                    'input.guessed_sep': input.guessed_sep,
                    'i': i
                })
        elif in_foreach:
            lines_in_foreach += line
        else:
            processed_source += line

    return processed_source

def generate_notebook(args, template_name):
    """Generate the output notebook using the chosen template"""
    output_cells = []
    if template_name not in shared.templates:
        error(f"Could not find the template {template_name}")
        sys.exit(1)

    template = shared.templates[template_name]

    for input_cell in template.cells:
        globally_replaced_source = StringTemplateWithDot(input_cell.source).safe_substitute(
            root_path=Path.cwd()
        )
        output_source = transform_input_source(args, globally_replaced_source)
        output_cell = input_cell.copy()
        output_cell.source = output_source
        output_cells.append(output_cell)

    return nbformat.v4.new_notebook(cells=output_cells, metadata={
        'language_info': {
            'file_extension': '.py',
            'mimetype': 'text/x-python',
            'name': 'python',
            'version': "3",
        }
    })

def find_running_server_with_same_working_dir(nb_working_dir: Path):
    # If the server does not have the same working dir then the relative
    # paths won't work. So we need to find one that has the right one.
    for si in notebookapp.list_running_servers():
        if Path(si['notebook_dir']) == nb_working_dir:
            return si
    return None

# This is copied/adapted from https://github.com/takluyver/nbopen
def open_notebook(args, nb_file: Path):
    """Open a generated notebook in the browsed, launching or reusing a notebook server"""
    nb_working_dir = shared.config['jupyter_notebook_working_directory']
    running_server = find_running_server_with_same_working_dir(nb_working_dir)
    if running_server:
        print(f"Opening the notebook with the existing server at {running_server['url']}")
        rel_path = nb_file.resolve().relative_to(nb_working_dir)
        if os.sep != '/':
            rel_path = rel_path.replace(os.sep, '/')
        url = url_path_join(running_server['url'], 'notebooks', url_escape(str(rel_path)))
        na = notebookapp.NotebookApp.instance()
        na.load_config_file()
        browser = webbrowser.get(na.browser or None)
        browser.open(url, new=2)
    else:
        # (imported from nbopen)
        # Hack: we want to override these settings if they're in the config file.
        # The application class allows 'command line' config to override config
        # loaded afterwards from the config file. So by specifying config, we
        # can use this mechanism.
        cfg = Config()
        cfg.NotebookApp.file_to_run = str(nb_file.resolve())
        cfg.NotebookApp.notebook_dir = str(nb_working_dir)
        cfg.NotebookApp.open_browser = True
        print("Starting a new notebook server")
        notebookapp.launch_new_instance(config=cfg,
                                        argv=[],  # Avoid it seeing our own argv
                                        )

def get_output_notebook_filepath(args):
    if args.output:
        output_file = Path(args.output)
    else:
        ipynb_dir = shared.config['generated_plots_directory']
        if not ipynb_dir.exists():
            os.makedirs(ipynb_dir)
        first_file_stem = args.files_to_plot[0].stem
        if first_file_stem == '-':
            first_file_stem = 'stdin'
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = ipynb_dir / f'nbplot-{date_str}-{first_file_stem}.ipynb'
    return output_file

def fill_inputs(args):
    for f in args.files_to_plot:
        if str(f) == '-':
            content = sys.stdin.buffer.read()
            b64_content = base64.b64encode(content)
            abs_path_or_io = f'io.BytesIO(b64decode({b64_content}))'
            delim = guess_delimiter(io.StringIO(content.decode('utf-8')))
            input = Input(pretty_name='stdin', rel_path=Path('stdin'), abs_path_or_io=abs_path_or_io, guessed_sep=delim)
            shared.inputs.append(input)
        else:
            if not f.exists():
                critical(f"`{f}' does not exist.")
                sys.exit(1)
            delim = guess_delimiter(open(f, 'r'))
            pretty_name = str(f)
            pretty_name = '...' + pretty_name[-32:] if len(pretty_name) > 32 else pretty_name
            # Make sure to include the quote as this string is meant to be used as code.
            abs_path_or_io = '"' + str(f.resolve()) + '"'
            input = Input(pretty_name=pretty_name, rel_path=f, abs_path_or_io=abs_path_or_io, guessed_sep=delim)
            shared.inputs.append(input)

def main():
    args = parse_command_line()

    log_level = logging.WARNING
    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')

    fill_inputs(args)

    load_source_code_from_notebooks(args)

    template = shared.config['default_template']
    if args.template:
        template = args.template
    print(f'Chosen template: {template}')

    nb = generate_notebook(args, template)

    output_nb = get_output_notebook_filepath(args)
    print(f'{output_nb} successfully generated.')
    nbformat.write(nb, output_nb)

    if args.generate_only or not ask_confirmation("Open the notebook in the browser"):
        sys.exit(0)

    # It's very verbose by default, make it more quiet.
    with LoggingLevelContext(logging.ERROR if not args.debug else logging.WARNING):
        open_notebook(args, output_nb)

if __name__ == '__main__':
    main()
