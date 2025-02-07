# MUPOL MPC Solution :articulated_lorry: :closed_lock_with_key:

## Overview :telescope:

This library forms the second component of the MUPOL MPC demonstrator, namely, the MPC solver itself.
In a nutshell, given a problem instance generated with the MUPOL plaintext library (hence a map with orders and trucks at given locations, where orders need to be brought to other locations with a given priority), the MPC solver will find a solution by making use of MPC, and hence by preserving the confidentiality of the trucks and orders information.

## Installation :wrench:

### Dependency management

Installation and dependencies are managed by [Poetry](https://python-poetry.org/), which can be installed with `pipx install poetry`.

### Internal (AIT-hosted) dependencies

Furthermore, this project uses [MUPOL plaintext](https://git-service.ait.ac.at/sct-crypto/mupol/mupol-python-plaintext), a Python package hosted on the internal AIT Gitlab.
In order to install this dependency, you will need access to the repository, and you will need some API authentication.
We give instructions here on how to use and set up a personal access token; other means (like relying on the system SSH agent) should also be possible, but have not been tested yet for this particular repository.

Create a personal access token in your Gitlab profile; scope `read_api` should be sufficient, in case of problems you can try with `api`.
Then, after having cloned this repository, run from the following command inside your root folder:

```shell
poetry config http-basic.mupol-plaintext <your e-mail address> <your access token>
```

At this point, you should be able to install dependencies with `poetry install`.

## Content :clipboard:

The library files are contained in the `mupol/mpc` folder;
they primarily consists of the `solver.py` file (containing the main class to solve a MUPOL problem instance with MPC) and of the `input_uploader.py` file (that "uploads" MUPOL objects to the MPyC framework).
The `utils` folder contains files for arguments handling and logging, and some MPyC utility functions.

The necessary configuration files can be found in the `config` folder.

Finally, the root folder contain an example wrapper `example.py`, that will generatae a MUPOL problem instance and solve it, and a `profiler.py` for benchmarking.


## Example usage :checkered_flag:

After install, run `poetry run python3 example.py`.
If you want to fully simulate several parties (e.g., 3) with separate processes, use the corresponding MPyC syntax, i.e., `poetry run python3 example.py -M 3`.
