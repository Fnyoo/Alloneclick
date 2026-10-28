import pytest

from serverkit import osinfo
from serverkit.runner import Runner, validate_package

UBUNTU = 'PRETTY_NAME="Ubuntu 24.04.1 LTS"\nID=ubuntu\nVERSION_ID="24.04"\nVERSION_CODENAME=noble\n'
DEBIAN = 'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\nID=debian\nVERSION_ID="12"\n'
MINT = 'ID=linuxmint\nVERSION_ID="22"\nID_LIKE="ubuntu debian"\n'


def test_supported():
    assert osinfo.parse(UBUNTU).supported
    assert osinfo.parse(DEBIAN).supported


def test_unsupported():
    assert not osinfo.parse(MINT).supported
    assert not osinfo.parse('ID=ubuntu\nVERSION_ID="20.04"\n').supported


def test_validate_package():
    assert validate_package("bind9-utils")
    for bad in ["nginx; rm -rf /", "$(id)", "-y", "A B"]:
        with pytest.raises(ValueError):
            validate_package(bad)


def test_dry_run_does_not_execute():
    r = Runner(dry_run=True).run(["false"])
    assert r.dry and r.ok


def test_runner_rejects_string_command():
    with pytest.raises(TypeError):
        Runner().run("ls -l")
