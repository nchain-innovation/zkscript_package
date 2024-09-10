import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--save-to-json",
        action="store",
        nargs="?",
        const="scripts_json",
        help="Save lock/unlock scripts to JSON files in the specified directory",
    )


@pytest.fixture
def save_to_json_folder(request):
    return request.config.getoption("--save-to-json")
