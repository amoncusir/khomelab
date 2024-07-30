"""
Metal hosts workers on Ubuntu 22.04 LC
"""

import argparse
import secrets
from pathlib import Path
from typing import List, Tuple

from passlib.hash import sha512_crypt

from metal.cloud_init.inflate_iso import generate_iso, generate_multi_iso
from runner.template.jinja_template import JinjaTemplate
from runner.action_metadata import action
from runner.context import Context
from utils.data_util import json_from


def build_parameters(args: List[str]):
    parser = argparse.ArgumentParser(description='Inflate ISO script', add_help=False)
    parser.add_argument('iso', type=str, help='Path of ISO file')

    if 'help' in args:
        parser.print_help()
        exit(0)

    return parser.parse_args(args)


def build_unix_pwd(pwd: str = None) -> str:
    if pwd is None:
        pwd = secrets.token_hex(32)

    return sha512_crypt.hash(pwd, rounds=500000)


def build_user_data(context: Context, hosts_path) -> List[Tuple[str, str]]:
    fb = context.get_file_builder()
    j2: JinjaTemplate = context.get_plugin('jinja')
    hosts = json_from(context.path / hosts_path)

    user_data_paths = []

    for host in hosts:
        name = host['name']
        host['password'] = build_unix_pwd(name)
        host['ssh_client']['password'] = build_unix_pwd()
        path = fb.file_from_template(f'user-data.{name}', 'user-data.yml.j2', j2.callback_render_to(), host)
        user_data_paths.append((name, str(path)))

    return user_data_paths


@action()
def single_iso(context: Context):
    root_mod = context.root_module
    mod = context.current_module
    args = context.args
    params = build_parameters(args)

    iso_path = Path(params.iso)

    if not iso_path.is_file():
        raise FileNotFoundError(iso_path)

    grub_cfg = mod.build_path('grub.cfg')
    xorriso_cli = mod.build_path('xorriso-cli.json')
    meta_data = mod.build_path('meta-data')

    userdata_files = build_user_data(context, 'hosts.json')

    for name, user_data in userdata_files:
        iso_output = root_mod.build_path(f'ubuntu22_04.autoinstall.{name}.iso')
        generate_iso(mod, iso_path, iso_output, meta_data, user_data, grub_cfg, xorriso_cli)
        print(f'Generate iso for host {name}')


@action()
def multi_iso(context: Context):
    root_mod = context.root_module
    mod = context.current_module
    args = context.args
    params = build_parameters(args)

    iso_path = Path(params.iso)

    if not iso_path.is_file():
        raise FileNotFoundError(iso_path)

    grub_cfg_template = 'grub.cfg.j2'
    xorriso_cli = mod.build_path('xorriso-cli.json')
    meta_data = mod.build_path('meta-data')
    iso_output = root_mod.build_path(f'ubuntu22_04.multi_autoinstall.iso')

    userdata_files = build_user_data(context, 'hosts.json')

    generate_multi_iso(mod, iso_path, iso_output, meta_data, userdata_files, grub_cfg_template, xorriso_cli)
