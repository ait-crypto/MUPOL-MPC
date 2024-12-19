# MUPOL MPC Solution for the Collaborative Freighter Delivery Problem :articulated_lorry: :closed_lock_with_key:

## Installation :wrench:

### Dependency management

Installation and dependencies are managed by [Poetry](https://python-poetry.org/), which can be installed with `pipx install poetry`.

### Internal dependencies

Furthermore, this project uses [MUPOL plaintext](https://github.com/ait-crypto/MUPOL-Plaintext).
The project code is currently not provided in a Python package, hence it is up to the user to create such a package and add it to the Python virtual environment.


## Example usage :checkered_flag:

After install, run `poetry run python3 example.py`.
If you want to fully simulate several parties (e.g., 3) with separate processes, use the corresponding MPyC syntax, i.e., `poetry run python3 example.py -M 3`.


## Credits

This project was partially funded by the Austrian Research Promotiion Agency (FFG) with the "Digitale Technolgien" funding frame under grant agreement no. 902669 (MUPOL).

Authors: Gabriele Spini and Stephan Krenn, AIT.
