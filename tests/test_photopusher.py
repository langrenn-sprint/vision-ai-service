"""Unit test cases for the generateSpecification module."""
import json
import os

from click.testing import CliRunner
from deepdiff import DeepDiff
import pytest
from pytest_mock import MockFixture

from sprint_photopusher.photopusher import cli, convert_csv_to_json, FileSystemMonitor


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


def fake_loop_action() -> None:
    """Fake loop action."""
    raise KeyboardInterrupt


def test_FileSystemMonitor_with_url_arguments_succeds(runner: CliRunner) -> None:
    """Should not raise any Exceptions."""
    url = "http://example.com"
    try:
        monitor = FileSystemMonitor(url, os.getcwd())
        monitor.start(loop_action=fake_loop_action)
    except Exception:
        pytest.fail("Unexpected Exception")


def test_cli_with_url_arguments_and_directory_succeds(runner: CliRunner) -> None:
    """Should not raise any Exceptions."""
    directory = "directory_to_be_monitored"
    url = "http://example.com"

    with runner.isolated_filesystem():
        os.makedirs(directory)

        try:
            monitor = FileSystemMonitor(url, directory)
            monitor.start(loop_action=fake_loop_action)
        except Exception:
            pytest.fail("Unexpected Exception")


def test_convert_Kjoreplan_to_json() -> None:
    """Should return correct json-representation."""
    kjoreplan_json = convert_csv_to_json("tests/files/Kjoreplan.csv", "kjoreplan")

    with open("./tests/files/Kjoreplan.json") as json_file:
        correct_json = json.load(json_file)

    ddiff = DeepDiff(json.loads(kjoreplan_json), correct_json, ignore_order=True)
    assert ddiff == {}


def test_convert_Klasser_to_json() -> None:
    """Should return correct json-representation."""
    klasser_json = convert_csv_to_json("tests/files/Klasser.csv", "klasser")

    with open("./tests/files/Klasser.json") as json_file:
        correct_json = json.load(json_file)

    ddiff = DeepDiff(json.loads(klasser_json), correct_json, ignore_order=True)
    assert ddiff == {}


def test_convert_Resultat_to_json() -> None:
    """Should return correct json-representation of list."""
    start_json = convert_csv_to_json("tests/files/G14Resultatliste.csv", "resultat")

    with open("./tests/files/G14Resultatliste.json") as json_file:
        correct_json = json.load(json_file)

    ddiff = DeepDiff(json.loads(start_json), correct_json, ignore_order=True)
    assert ddiff == {}


def test_convert_ResultatHeat_to_json() -> None:
    """Should return correct json-representation of list."""
    start_json = convert_csv_to_json("tests/files/G14KvartRes.csv", "resultat_heat")

    with open("./tests/files/G14KvartRes.json") as json_file:
        correct_json = json.load(json_file)

    ddiff = DeepDiff(json.loads(start_json), correct_json, ignore_order=True)
    if ddiff != {}:
        print(json.dumps(ddiff, indent=4, sort_keys=True))
    assert ddiff == {}


def test_convert_Start_to_json() -> None:
    """Should return correct json-representation of startlist."""
    start_json = convert_csv_to_json("tests/files/G11KvartStart.csv", "start")

    with open("./tests/files/G11KvartStart.json") as json_file:
        correct_json = json.load(json_file)

    ddiff = DeepDiff(json.loads(start_json), correct_json, ignore_order=True)
    # if ddiff != {}:
    #     print(json.dumps(ddiff, indent=4, sort_keys=True))
    assert ddiff == {}


def test_convert_Deltakere_to_json() -> None:
    """Should return correct json-representation of deltakerliste."""
    deltakere_json = convert_csv_to_json("tests/files/Deltakere.csv", "deltakere")

    with open("./tests/files/Deltakere.json") as json_file:
        correct_json = json.load(json_file)

    ddiff = DeepDiff(json.loads(deltakere_json), correct_json, ignore_order=True)
    if ddiff != {}:
        print(json.dumps(ddiff, indent=4, sort_keys=True))
    assert ddiff == {}


# --- Bad cases ---
def test_cli_no_arguments_fails(runner: CliRunner) -> None:
    """Should return exit_code 2."""
    runner = CliRunner()

    result = runner.invoke(cli)
    assert "Error: Missing argument 'URL'" in result.output
    assert result.exit_code == 2


def test_cli_option_directory_does_not_exist(
    mocker: MockFixture, runner: CliRunner
) -> None:
    """Should return exit_code 0."""
    runner = CliRunner()

    result = runner.invoke(cli, ["-d does_not_exist"])
    assert "does not exist" in result.output
    assert result.exit_code == 2
