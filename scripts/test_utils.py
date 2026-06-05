import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from extractors import OclcFast, SubjectHeadings
from openai import APIStatusError


SAMPLE_FAST_RESULTS = {
    "Bridges": {"heading": "Bridges", "fast_id": "fst00838671", "marc_tag": "150"},
}


PARSED_CANDIDATES = {
    "topical": ["Bridges", "Suspension bridges"],
    "geographic": ["San Francisco"],
    "chronological": ["1930-1939"],
    "form_genre": ["Photographs"],
}


def _make_chat_response(message_content, total_tokens=50):
    mock_message = MagicMock()
    mock_message.content = message_content

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock = MagicMock()
    mock.choices = [mock_choice]
    mock.usage.total_tokens = total_tokens
    return mock


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


@patch("utils.read_prompt")
@patch("utils._get_ai_client")
@patch("utils.resolve_candidates")
def test_extract_full_pipeline(mock_resolve, mock_get_client, mock_read_prompt, parsed_result):
    mock_read_prompt.return_value = "Extract candidates"
    mock_resolve.return_value = SAMPLE_FAST_RESULTS
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    phase1_resp = _make_chat_response(message_content=json.dumps(PARSED_CANDIDATES), total_tokens=30)
    phase3_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), total_tokens=60)
    mock_client.chat.completions.create.side_effect = [phase1_resp, phase3_resp]

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    assert mock_client.chat.completions.create.call_count == 2
    mock_resolve.assert_called_once_with(PARSED_CANDIDATES)


@patch("utils.read_prompt")
@patch("utils._get_ai_client")
@patch("utils.resolve_candidates")
def test_extract_empty_fast_results(mock_resolve, mock_get_client, mock_read_prompt, parsed_result):
    mock_read_prompt.return_value = "Extract candidates"
    mock_resolve.return_value = {}
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    phase1_resp = _make_chat_response(message_content=json.dumps(PARSED_CANDIDATES), total_tokens=30)
    phase3_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), total_tokens=60)
    mock_client.chat.completions.create.side_effect = [phase1_resp, phase3_resp]

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    mock_resolve.assert_called_once_with(PARSED_CANDIDATES)


@patch("utils.read_prompt")
@patch("utils._get_ai_client")
def test_extract_malformed_candidates(mock_get_client, mock_read_prompt):
    mock_read_prompt.return_value = "Extract candidates"
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    phase1_resp = _make_chat_response(message_content="not json at all", total_tokens=10)
    mock_client.chat.completions.create.return_value = phase1_resp

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result is None


@patch("utils.read_prompt")
@patch("utils._get_ai_client")
@patch("utils.resolve_candidates")
def test_extract_bad_phase3_json(mock_resolve, mock_get_client, mock_read_prompt):
    mock_read_prompt.return_value = "Extract candidates"
    mock_resolve.return_value = SAMPLE_FAST_RESULTS
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    phase1_resp = _make_chat_response(message_content=json.dumps(PARSED_CANDIDATES), total_tokens=30)
    phase3_resp = _make_chat_response(message_content="not json", total_tokens=60)
    mock_client.chat.completions.create.side_effect = [phase1_resp, phase3_resp]

    from utils import extract
    result = extract("gpt-4o", "system prompt", OclcFast, "record content")

    assert result is None


# === extract_async ===


@patch("utils.read_prompt")
@patch("utils._get_ai_async_client")
@patch("utils.resolve_candidates")
@pytest.mark.asyncio
async def test_extract_async_full_pipeline(mock_resolve, mock_get_client, mock_read_prompt, parsed_result):
    mock_read_prompt.return_value = "Extract candidates"
    mock_resolve.return_value = SAMPLE_FAST_RESULTS
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    phase1_resp = _make_chat_response(message_content=json.dumps(PARSED_CANDIDATES), total_tokens=30)
    phase3_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), total_tokens=60)
    mock_client.chat.completions.create.side_effect = [phase1_resp, phase3_resp]

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result
    assert mock_client.chat.completions.create.await_count == 2
    mock_resolve.assert_called_once_with(PARSED_CANDIDATES)


@patch("utils.read_prompt")
@patch("utils._get_ai_async_client")
@patch("utils.resolve_candidates")
@pytest.mark.asyncio
async def test_extract_async_empty_fast_results(mock_resolve, mock_get_client, mock_read_prompt, parsed_result):
    mock_read_prompt.return_value = "Extract candidates"
    mock_resolve.return_value = {}
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    phase1_resp = _make_chat_response(message_content=json.dumps(PARSED_CANDIDATES), total_tokens=30)
    phase3_resp = _make_chat_response(message_content=parsed_result.model_dump_json(), total_tokens=60)
    mock_client.chat.completions.create.side_effect = [phase1_resp, phase3_resp]

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result == parsed_result


@patch("utils.read_prompt")
@patch("utils._get_ai_async_client")
@patch("utils.resolve_candidates")
@pytest.mark.asyncio
async def test_extract_async_api_error(mock_resolve, mock_get_client, mock_read_prompt):
    mock_read_prompt.return_value = "Extract candidates"
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


@patch("utils.read_prompt")
@patch("utils._get_ai_async_client")
@patch("utils.resolve_candidates")
@pytest.mark.asyncio
async def test_extract_async_malformed_candidates(mock_resolve, mock_get_client, mock_read_prompt):
    mock_read_prompt.return_value = "Extract candidates"
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    phase1_resp = _make_chat_response(message_content="bad json", total_tokens=10)
    mock_client.chat.completions.create.return_value = phase1_resp

    from utils import extract_async
    result = await extract_async("gpt-4o", "system prompt", OclcFast, "record content")

    assert result is None
