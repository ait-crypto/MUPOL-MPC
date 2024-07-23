"""Contains the MUPOL MPC argument handler class
"""

import argparse
from typing import Any

from mupol.plaintext.args_handler import ArgsHandler


class MPCArgsHandler(ArgsHandler):
    """MUPOL MPC argument handler"""

    def __init__(self, args: Any) -> None:
        """Constructor method.

        :param args: the arguments (duh)
        """
        self._parser = argparse.ArgumentParser(description="Plaintext and MPC parser")
        self._args = args
        self.args: Any = None
        self._init_parser()
        super()._setup_parser()

        self._parser.set_defaults(**self._config["MPC solver parameters"])
        self._parser.set_defaults(**self._config["MPC parameters"])
        self._parser.set_defaults(**self._config["Logger parameters"])
        self.args = self._parser.parse_args(self._args)

    def _init_parser(self) -> None:
        """Add arguments to parser and pars them."""
        self._parser.add_argument(
            "--dummy-node", type=int, help="ID of dummy node for MPC computation"
        )
        self._parser.add_argument(
            "--dummy-freighter-id",
            type=int,
            help="ID of dummy freighter for MPC computation",
        )
        self._parser.add_argument(
            "--bit-length-sectypes",
            type=int,
            help="Maximum bit length of values to be secret-shared",
        )
        self._parser.add_argument(
            "--logger-config",
            type=str,
            help="Location of logger config",
        )
        self.args = self._parser.parse_known_args(self._args)
