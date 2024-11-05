# anaconda-conda-tos

Conda subcommand to view, accept, and interact with a channel's Terms of Service (ToS).

## Installation

```bash
$ git clone https://github.com/anaconda/anaconda-conda-tos.git
$ cd anaconda-conda-tos
$ conda create --name=conda-tos --file=tests/requirements.txt
$ conda activate conda-tos
(conda-tos) $ pip install [-e] .
```

## Usage

```bash
$ conda activate conda-tos
(conda-tos) $ $CONDA_PREFIX/bin/conda tos --help
(conda-tos) $ $CONDA_PREFIX/bin/conda tos
(conda-tos) $ $CONDA_PREFIX/bin/conda tos --view
(conda-tos) $ $CONDA_PREFIX/bin/conda tos --accept
(conda-tos) $ $CONDA_PREFIX/bin/conda tos --reject
```

To test with a local server use `tests/http_test_server.py` (see below) and use the `--channel` option.

> [!NOTE]
> The port is random and just an example.

```bash
(conda-tos) $ $CONDA_PREFIX/bin/conda tos --channel=http://127.0.0.1:53095/
```


#### A sample channel without a ToS

```bash
$ conda activate conda-tos
(conda-tos) $ python tests/http_test_server.py --sample
Serving HTTP on 127.0.0.1 port 53095 (http://127.0.0.1:53095/) ...
Press Enter to exit
```

#### A sample channel with a ToS

```bash
$ conda activate conda-tos
(conda-tos) $ python tests/http_test_server.py --tos
Serving HTTP on 127.0.0.1 port 53095 (http://127.0.0.1:53095/) ...
Press Enter to exit
```

## Development

```bash
$ conda activate conda-tos
(conda-tos) $ conda install --file=tests/requirements-ci.txt
(conda-tos) $ pytest --cov=anaconda_conda_tos
```
