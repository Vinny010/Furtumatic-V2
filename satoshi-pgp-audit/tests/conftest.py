import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KEY_PATH = ROOT / "data" / "keys" / "satoshi_5EC948A1.asc"
SATOSHI_FPR = "DE4EFCA3E1AB9E41CE96CECB18C09E865EC948A1"


def _find_src(name):
    env = os.environ.get(name)
    if env and Path(env).exists():
        return Path(env)
    return None


@pytest.fixture(scope="session")
def key_path():
    if not KEY_PATH.exists():
        pytest.skip("pinned key file not present")
    return KEY_PATH


@pytest.fixture(scope="session")
def keyblock(key_path):
    from spa.openpgp import dearmor, parse_keyblock
    return parse_keyblock(dearmor(key_path.read_text())[0].body)


@pytest.fixture(scope="session")
def gnupg_src():
    p = _find_src("SPA_GNUPG_SRC") or (ROOT / "data" / "gnupg-src" / "gnupg")
    if not (p / "cipher" / "random.c").exists():
        pytest.skip("GnuPG 1.4.7 source not available (run: make setup)")
    return p


@pytest.fixture(scope="session")
def gnupg_src_1421():
    p = _find_src("SPA_GNUPG_SRC_1421") or (ROOT / "data" / "gnupg-src" / "gnupg-1.4.21")
    if not (p / "cipher" / "random.c").exists():
        pytest.skip("GnuPG 1.4.21 source not available (run: make setup)")
    return p


@pytest.fixture(scope="session")
def gpg147():
    from spa.lab.harvest import find_gpg
    found = find_gpg()
    if "historical" not in found:
        pytest.skip("GnuPG 1.4.7 binary not available (run: make native-gnupg147)")
    return found["historical"]
