import subprocess
from pathlib import Path
from typing import List

from runner.module import Module
from utils.data_util import json_from


def process_cmd(args: list, cwd=None) -> str:
    print(args)
    return subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd).communicate()[0].rstrip().decode('utf-8')


def xorriso(xorriso_args, output_iso, iso_expanded, cwd):
    process_cmd(['xorriso'] + xorriso_args + ['-o', output_iso, iso_expanded], cwd=cwd)


def unzip_iso(iso_path: str | Path, temp_dir: str | Path, to_rel_dir: str | Path):
    process_cmd(['7z', '-y', 'x', iso_path, f'-o{to_rel_dir}'], cwd=temp_dir)


def generate_iso(mod: Module, iso_path, output_iso, metadata_path, userdata_path, grub_cnf_path, xorriso_cli_path):
    fb = mod.get_file_builder()

    with fb.tmp_dir() as tmp:
        unzip_iso(iso_path, tmp.path, 'iso')
        tmp.mkdir('iso/server')

        tmp.move('iso/[BOOT]', 'boot')
        tmp.copy(grub_cnf_path, 'iso', 'grub.cfg')
        tmp.copy(metadata_path, 'iso/server', 'meta-data')
        tmp.copy(userdata_path, 'iso/server', 'user-data')

        xorriso_args: List[str] = json_from(xorriso_cli_path)

        xorriso(xorriso_args, output_iso, './iso', cwd=tmp.path)


def generate_multi_iso(mod: Module,
                       iso_path,
                       output_iso,
                       metadata_path,
                       user_data_paths,
                       grub_cnf_template,
                       xorriso_cli_path
                       ):

    fb = mod.get_file_builder()
    j2 = mod.jinja

    with fb.tmp_dir() as tmp:
        unzip_iso(iso_path, tmp.path, 'iso')

        tmp.move('iso/[BOOT]', 'boot')

        entries = [name for name, path in user_data_paths]
        j2.render_to(tmp.path / 'iso' / 'grub.cfg', grub_cnf_template, {'menu_entries': entries})

        for name, userdata_path in user_data_paths:
            folder = tmp.mkdir(f'iso/hosts/{name}')
            tmp.copy(userdata_path, folder, 'user-data')
            tmp.copy(metadata_path, folder, 'meta-data')

        xorriso_args: List[str] = json_from(xorriso_cli_path)

        xorriso(xorriso_args, output_iso, './iso', cwd=tmp.path)
