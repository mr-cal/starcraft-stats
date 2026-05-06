"""Tests for Config model and CraftApplicationBranch."""

import pytest
from starcraft_stats.application import CraftApplicationBranch
from starcraft_stats.config import Config


class TestCraftApplicationBranch:
    def test_str_returns_name_slash_branch(self):
        branch = CraftApplicationBranch(
            name="snapcraft", branch="main", owner="canonical"
        )
        assert str(branch) == "snapcraft/main"

    def test_str_with_non_main_branch(self):
        branch = CraftApplicationBranch(
            name="charmcraft", branch="hotfix/4.1", owner="canonical"
        )
        assert str(branch) == "charmcraft/hotfix/4.1"


class TestConfig:
    def test_load_all_fields_from_toml(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_bytes(
            b'craft-libraries = ["craft-cli", "craft-parts"]\n'
            b'craft-projects = ["snapcraft"]\n'
            b'craft-applications = ["snapcraft"]\n'
            b"refresh-interval-days = 14\n"
            b'launchpad-projects = ["snapcraft"]\n'
            b'maintainers = ["mr-cal", "lengau"]\n'
        )
        config = Config.from_toml_file(config_file)

        assert config.craft_libraries == ["craft-cli", "craft-parts"]
        assert config.craft_projects == ["snapcraft"]
        assert config.craft_applications == ["snapcraft"]
        assert config.refresh_interval_days == 14
        assert config.launchpad_projects == ["snapcraft"]
        assert config.maintainers == ["mr-cal", "lengau"]

    def test_maintainers_defaults_to_empty(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_bytes(
            b"craft-libraries = []\ncraft-projects = []\ncraft-applications = []\n"
        )
        config = Config.from_toml_file(config_file)

        assert config.maintainers == []

    def test_launchpad_projects_defaults_to_empty(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_bytes(
            b"craft-libraries = []\ncraft-projects = []\ncraft-applications = []\n"
        )
        config = Config.from_toml_file(config_file)

        assert config.launchpad_projects == []

    def test_refresh_interval_defaults_to_7(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_bytes(
            b"craft-libraries = []\ncraft-projects = []\ncraft-applications = []\n"
        )
        config = Config.from_toml_file(config_file)

        assert config.refresh_interval_days == 7

    def test_missing_required_field_raises(self, tmp_path):
        config_file = tmp_path / "config.toml"
        # craft-projects is missing
        config_file.write_bytes(b"craft-libraries = []\ncraft-applications = []\n")

        with pytest.raises(Exception, match="craft-projects"):
            Config.from_toml_file(config_file)
