import asyncio
import logging

from pathlib import Path
from subprocess import check_output
from os import getenv
from getpass import getpass
from typing import List, AsyncGenerator, Generator
from functools import cache

import pandas as pd
import yaml
from pydantic import BaseModel
from openai import OpenAI, AsyncOpenAI, APIStatusError
from tenacity import retry, wait_random_exponential, stop_after_attempt


logger = logging.getLogger(__name__)


def _fetch_settings(file_path="../config/settings.yml"):
    settings_yaml = Path(file_path).read_text(encoding="utf-8")
    return yaml.safe_load(settings_yaml)


def _get_api_key() -> str:
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


def _get_api_baseurl() -> str:
    return _fetch_settings()['base_url']
    

@cache
def _get_ai_client() -> OpenAI:
    return OpenAI(
        api_key=_get_api_key(),
        base_url=_get_api_baseurl()
    )


@cache
def _get_ai_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=_get_api_key(),
        base_url=_get_api_baseurl()
    )


def file_to_df(file_path: str) -> pd.DataFrame:
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


def read_prompt(prompt_name: str) -> str:
    return Path(f"../prompts/{prompt_name}.md").read_text(encoding="utf-8")


def extract(model: str, system_prompt: str, extractor: type[BaseModel], record_content: str): 
    client = _get_ai_client()
    # TODO: add retry with backoff for 5xx server errors
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": record_content},
        ],
        # TODO: handle validation error for returned results (Invalid JSON)
        text_format=extractor,
        # TODO: add tool to handle assignFAST API calls with caching
    )
    return response.output_parsed


def extract_multi(model: str, system_prompt: str, extractor: type[BaseModel], record_contents: List[str]) -> Generator: 
    for content in record_contents:
        yield extract(model, system_prompt, extractor, content)


@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(5)
)
async def extract_async(model: str, system_prompt: str, extractor: type[BaseModel], record_content: str): 
    client = _get_ai_async_client()
    logger.debug(f"Using model: {model}")
    try:
        response = await client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": record_content},
            ],
            text_format=extractor,
            # TODO: add tool to handle assignFAST API calls with caching
        )
    except APIStatusError as e:
        logger.error(f"API Error {e.status_code}: Request ID {e.request_id}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    
    logger.info(f"Tokens used: {response.usage.total_tokens}")
    return response.output_parsed


async def extract_multi_async(model: str, system_prompt: str, extractor: type[BaseModel], record_contents: List[str]) -> AsyncGenerator: 
    coroutines = [
        extract_async(model, system_prompt, extractor, content)
        for content in record_contents
    ]
    return await asyncio.gather(*coroutines)