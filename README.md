# MUPOL MPC Solution :articulated_lorry: :closed_lock_with_key:

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


## Example usage :checkered_flag:

After install, run `poetry run python3 example.py`.
Currently, it is not possible to direclty suppress the log output of MPyC;
you can filter that out by piping the above command into grep, e.g. `poetry run python3 examply.py | grep "MUPOL"`.
