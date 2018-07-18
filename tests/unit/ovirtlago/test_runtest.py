from collections import namedtuple
import pytest
from mock import MagicMock, patch

from lago.plugins.vm import (ExtractPathError, ExtractPathNoPathError)

from ovirtlago import (testlib, prefix)

DummyTest = namedtuple('DummyTest', ['id'])


@pytest.fixture
def mock_prefix():
    return MagicMock(spec=prefix.OvirtPrefix, name='mock_prefix')


@pytest.fixture
def dummy_test():
    return DummyTest(id=lambda: 123)


@pytest.mark.parametrize('exc', [ExtractPathError, ExtractPathNoPathError])
@patch('ovirtlago.testlib.LOGGER')
def test_log_collection_should_ignore_extract_path_error(
    mock_logger, mock_prefix, dummy_test, exc
):
    exc_instance = exc()
    mock_prefix.collect_artifacts.side_effect = exc_instance
    log_collector = testlib.LogCollectorPlugin(mock_prefix)
    log_collector._addFault(dummy_test, None)

    mock_prefix.collect_artifacts.assert_called_once()
    mock_logger.debug.assert_called_with(exc_instance, exc_info=True)
