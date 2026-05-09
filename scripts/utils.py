from pathlib import Path
from subprocess import check_output
from os import getenv
from getpass import getpass
from typing import List
from functools import cache

import pandas as pd
import yaml
from pydantic import BaseModel
from openai import OpenAI


def _fetch_settings(file_path="../config/settings.yml"):
    settings_yaml = Path(file_path).read_text(encoding="utf-8")
    return yaml.safe_load(settings_yaml)


def _get_api_key():
    auth_settings = _fetch_settings()['token_auth']
    match auth_settings:
        case {'cmd': _}:
            cmd = auth_settings['cmd']
            return check_output(cmd, text=True).strip()
        case {'env': _}:
            env = auth_settings['env']
            return getenv(env)
        case 'prompt':
            return getpass("Enter API Key")


def _get_api_baseurl():
    return _fetch_settings()['base_url']
    

@cache
def _get_ai_client():
    return OpenAI(
        api_key=_get_api_key(),
        base_url=_get_api_baseurl()
    )


def file_to_df(file_path):
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(file)
    match file.suffix.lower():
        case ".csv":
            return pd.read_csv(file)
        case ".xlsx":
            return pd.read_excel(file)
        case _:
            raise Exception("File type not supported")


def read_prompt(prompt_name):
    return Path(f"../prompts/{prompt_name}.md").read_text(encoding="utf-8")


def extract(model: str, system_prompt: str, extractor: type[BaseModel], record_content: str): 
    client = _get_ai_client()
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": record_content},
        ],
        text_format=extractor,
    )
    return response.output_parsed


def extract_multi(model: str, system_prompt: str, extractor: type[BaseModel], record_contents: List[str]): 
    for content in record_contents:
        yield extract(model, system_prompt, extractor, content)