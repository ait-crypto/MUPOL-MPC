# MUPOL MPC Solution for the Collaborative Freighter Delivery Problem :articulated_lorry: :closed_lock_with_key:

## Overview :telescope:

This library forms the second component of the MUPOL MPC demonstrator, namely, the MPC solver itself.
In a nutshell, given a problem instance generated with the MUPOL plaintext library (hence a map with orders and trucks at given locations, where orders need to be brought to other locations with a given priority), the MPC solver will find a solution by making use of MPC, and hence by preserving the confidentiality of the trucks and orders information.

## Installation :wrench:

### Dependency management

Installation and dependencies are managed by [Poetry](https://python-poetry.org/), which can be installed with `pipx install poetry`.

### Internal dependencies

Furthermore, this project uses [MUPOL plaintext](https://github.com/ait-crypto/MUPOL-Plaintext).
The project code is currently not provided in a Python package, hence it is up to the user to create such a package and add it to the Python virtual environment.

## Content :clipboard:

The library files are contained in the `mupol/mpc` folder;
they primarily consists of the `solver.py` file (containing the main class to solve a MUPOL problem instance with MPC) and of the `input_uploader.py` file (that "uploads" MUPOL objects to the MPyC framework).
The `utils` folder contains files for arguments handling and logging, and some MPyC utility functions.

The necessary configuration files can be found in the `config` folder.

Finally, the root folder contain an example wrapper `example.py`, that will generatae a MUPOL problem instance and solve it, and a `profiler.py` for benchmarking.


## Example usage :checkered_flag:

After install, run `poetry run python3 example.py`.
If you want to fully simulate several parties (e.g., 3) with separate processes, use the corresponding MPyC syntax, i.e., `poetry run python3 example.py -M 3`.


## Credits

This project was partially funded by the Austrian Research Promotiion Agency (FFG) with the "Digitale Technolgien" funding frame under grant agreement no. 902669 (MUPOL).

Authors: Gabriele Spini and Stephan Krenn, AIT.
