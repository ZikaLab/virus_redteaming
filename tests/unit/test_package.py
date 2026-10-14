from virus_redteaming import __version__


def test_package_version_is_semver_shaped() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
