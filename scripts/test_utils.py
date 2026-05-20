import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from extractors import OclcFast, SubjectHeadings
from openai import APIStatusError


SAMPLE_FAST_RESULT = [
    {"auth": "Bridges", "idroot": "fst00838671", "tag": 150, "type": "auth"},
]


def _make_chat_response(message_content, tool_calls=None, total_tokens=50):
    mock_message = MagicMock()
    mock_message.content = message_content
    mock_message.tool_calls = tool_calls

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock = MagicMock()
    mock.choices = [mock_choice]
    mock.usage.total_tokens = total_tokens
    return mock


def _make_tool_call(name="assignFast", arguments=None, call_id="call_1"):
    if arguments is None:
        arguments = '{"query": "bridges", "queryIndex": "suggest50", "rows": 5}'
    mock_function = MagicMock()
    mock_function.name = name
    mock_function.arguments = arguments

    item = MagicMock()
    item.id = call_id
    item.type = "function"
    item.function = mock_function
    return item


@pytest.fixture
def parsed_result():
    return OclcFast(
        item_title="Test item",
        subject_headings=[
            SubjectHeadings(heading="Bridges", fast_uri="http://id.worldcat.org/fast/838737", marc_tag="650", facet="Topical"),
        ],
        marc_encoding='650 \\7 $a Bridges $2 fast $0 (OCoLC)fst00838737',
    )


# === extract (sync) ===


@patch("utils._get_ai_client")
def test_extract_direct_parse(mock_get_client, parsed_result):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    direct_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None)
    mock_client.chat.completions.create.return_value = direct_resp

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    mock_client.chat.completions.create.assert_called_once()


@patch("utils._get_ai_client")
@patch("utils.assignFast")
def test_extract_single_tool_call(mock_assign_fast, mock_get_client, parsed_result):
    mock_assign_fast.return_value = SAMPLE_FAST_RESULT
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    tool_call = _make_tool_call()
    tool_resp = _make_chat_response(message_content=None, tool_calls=[tool_call], total_tokens=20)
    final_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None, total_tokens=60)
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    assert mock_client.chat.completions.create.call_count == 2
    mock_assign_fast.assert_called_once_with(query="bridges", queryIndex="suggest50", rows=5)


@patch("utils._get_ai_client")
@patch("utils.assignFast")
def test_extract_parallel_tool_calls(mock_assign_fast, mock_get_client, parsed_result):
    mock_assign_fast.return_value = SAMPLE_FAST_RESULT
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    t1 = _make_tool_call(arguments='{"query": "bridges"}', call_id="call_1")
    t2 = _make_tool_call(arguments='{"query": "design"}', call_id="call_2")
    tool_resp = _make_chat_response(message_content=None, tool_calls=[t1, t2], total_tokens=30)
    final_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None, total_tokens=80)
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    assert mock_client.chat.completions.create.call_count == 2
    assert mock_assign_fast.call_count == 2


@patch("utils._get_ai_client")
@patch("utils.assignFast")
def test_extract_empty_tool_args(mock_assign_fast, mock_get_client, parsed_result):
    mock_assign_fast.return_value = SAMPLE_FAST_RESULT
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    tool_call = _make_tool_call(arguments="{}", call_id="call_1")
    tool_resp = _make_chat_response(message_content=None, tool_calls=[tool_call])
    final_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None)
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    mock_assign_fast.assert_called_once_with()


# === extract_async ===


@patch("utils._get_ai_async_client")
@pytest.mark.asyncio
async def test_extract_async_direct_parse(mock_get_client, parsed_result):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    direct_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None)
    mock_client.chat.completions.create.return_value = direct_resp

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    mock_client.chat.completions.create.assert_awaited_once()


@patch("utils._get_ai_async_client")
@patch("utils.assignFast")
@pytest.mark.asyncio
async def test_extract_async_tool_call(mock_assign_fast, mock_get_client, parsed_result):
    mock_assign_fast.return_value = SAMPLE_FAST_RESULT
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    tool_call = _make_tool_call()
    tool_resp = _make_chat_response(message_content=None, tool_calls=[tool_call], total_tokens=20)
    final_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None, total_tokens=60)
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    assert mock_client.chat.completions.create.await_count == 2
    mock_assign_fast.assert_called_once_with(query="bridges", queryIndex="suggest50", rows=5)


@patch("utils._get_ai_async_client")
@patch("utils.assignFast")
@pytest.mark.asyncio
async def test_extract_async_api_error(mock_assign_fast, mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()
    mock_client.chat.completions.create.side_effect = APIStatusError(
        message="API Error",
        response=MagicMock(status_code=500),
        body={"error": "server error"},
    )

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result is None


@patch("utils._get_ai_async_client")
@patch("utils.assignFast")
@pytest.mark.asyncio
async def test_extract_async_generic_exception(mock_assign_fast, mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()
    mock_client.chat.completions.create.side_effect = ValueError("unexpected error")

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result is None


@patch("utils._get_ai_async_client")
@patch("utils.assignFast")
@pytest.mark.asyncio
async def test_extract_async_tool_returns_empty(mock_assign_fast, mock_get_client, parsed_result):
    mock_assign_fast.return_value = []
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    tool_call = _make_tool_call()
    tool_resp = _make_chat_response(message_content=None, tool_calls=[tool_call], total_tokens=20)
    final_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), tool_calls=None, total_tokens=60)
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    assert mock_client.chat.completions.create.await_count == 2
