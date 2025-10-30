"""Tests for the pylogger module."""

import importlib
from unittest.mock import MagicMock, patch

import pytest

from template_agent.utils.pylogger import _discover_app_loggers


class TestDiscoverAppLoggers:
    """Test cases for _discover_app_loggers function."""

    def setup_method(self):
        """Reset cache before each test."""
        # Reset the cache by accessing the module-level variable
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

    def test_discover_loggers_for_real_package(self):
        """Test discovering loggers for the actual template_agent package."""
        # Reset cache
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

        # Discover loggers
        logger_names = _discover_app_loggers("template_agent")

        # Should always include root package
        assert "template_agent" in logger_names

        # Should find some submodules
        assert len(logger_names) > 1

        # Should find src and utils subpackages
        assert any("template_agent.src" in name for name in logger_names)
        assert any("template_agent.utils" in name for name in logger_names)

    def test_caching_behavior(self):
        """Test that results are cached after first call."""
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

        # First call
        first_result = _discover_app_loggers("template_agent")

        # Cache should be populated
        assert pylogger_module._DISCOVERED_LOGGERS_CACHE is not None
        assert pylogger_module._DISCOVERED_LOGGERS_CACHE == first_result

        # Second call should return cached result
        second_result = _discover_app_loggers("template_agent")

        # Should return the same object (not just equal, but same reference)
        assert second_result is first_result

    def test_fallback_for_nonexistent_package(self):
        """Test fallback behavior when package cannot be imported."""
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

        # Try to discover loggers for a nonexistent package
        logger_names = _discover_app_loggers("nonexistent_package")

        # Should include root package name
        assert "nonexistent_package" in logger_names

        # Should attempt to add common patterns
        # (they won't actually be added since they don't exist)
        # But the function should complete without errors

    @patch("importlib.import_module")
    def test_fallback_patterns_added_if_importable(self, mock_import):
        """Test that fallback patterns are added if they can be imported."""
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

        # Make the root package import fail, but allow submodules to succeed
        def side_effect(name):
            if name == "test_package":
                raise ImportError("Package not found")
            elif name in [
                "test_package.src",
                "test_package.src.core",
                "test_package.utils",
            ]:
                # Return a mock module for successful imports
                return MagicMock()
            else:
                raise ImportError(f"Module {name} not found")

        mock_import.side_effect = side_effect

        logger_names = _discover_app_loggers("test_package")

        # Should include root package
        assert "test_package" in logger_names

        # Should include the fallback patterns that were successfully imported
        assert "test_package.src" in logger_names
        assert "test_package.src.core" in logger_names
        assert "test_package.utils" in logger_names

    @patch("importlib.import_module")
    def test_package_without_path_attribute(self, mock_import):
        """Test handling of module without __path__ attribute."""
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

        # Create a mock module without __path__ (like a simple module, not a package)
        mock_module = MagicMock()
        del mock_module.__path__  # Remove __path__ attribute

        mock_import.return_value = mock_module

        logger_names = _discover_app_loggers("simple_module")

        # Should only return the root package name
        assert logger_names == ["simple_module"]

    @patch("importlib.import_module")
    @patch("pkgutil.walk_packages")
    def test_walk_packages_discovery(self, mock_walk, mock_import):
        """Test that submodules are discovered using pkgutil.walk_packages."""
        import template_agent.utils.pylogger as pylogger_module

        pylogger_module._DISCOVERED_LOGGERS_CACHE = None

        # Create a mock package with __path__
        mock_package = MagicMock()
        mock_package.__path__ = ["/fake/path"]

        mock_import.return_value = mock_package

        # Mock walk_packages to return some fake submodules
        mock_walk.return_value = [
            (None, "test_pkg.module1", False),
            (None, "test_pkg.module2", False),
            (None, "test_pkg.subpkg", True),
            (None, "test_pkg.subpkg.module3", False),
        ]

        logger_names = _discover_app_loggers("test_pkg")

        # Should include root package
        assert "test_pkg" in logger_names

        # Should include all discovered modules
        assert "test_pkg.module1" in logger_names
        assert "test_pkg.module2" in logger_names
        assert "test_pkg.subpkg" in logger_names
        assert "test_pkg.subpkg.module3" in logger_names

        # Verify walk_packages was called with correct arguments
        mock_walk.assert_called_once_with(mock_package.__path__, prefix="test_pkg.")
