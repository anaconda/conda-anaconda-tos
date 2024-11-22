# conda-anaconda-tos

Conda subcommand to view, accept, and interact with a channel's Terms of Service (ToS).

## Installation

### Into `base` environment

```bash
$ conda install --name=base distribution-plugins/label/dev::conda-anaconda-tos
```


### Into a new environment (for development & testing)

```bash
$ git clone https://github.com/anaconda/conda-anaconda-tos.git
$ cd conda-anaconda-tos
$ conda create --name=conda-tos --file=tests/requirements.txt
$ conda activate conda-tos
(conda-tos) $ pip install -e .
```

> [!NOTE]
> With the plugin installed into a non-`base` environment use `$CONDA_PREFIX/bin/conda` in stead of `conda` for the usage instructions below.

## Usage

```bash
$ conda tos --help

# see the status of all Terms of Service
$ conda tos

# conda command intercepted with Terms of Service checks
$ conda create --name=scratch

# clear cache & acceptance/rejection files
$ conda tos clean --all

# other commands for managing Terms of Service
$ conda tos view
$ conda tos accept
$ conda tos reject
$ conda tos interactive
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
(conda-tos) $ python tests/http_test_server.py
Serving HTTP at http://127.0.0.1:54115...
Press Enter or Ctrl-C to exit.
```

#### A sample channel with a ToS

```bash
$ conda activate conda-tos
(conda-tos) $ python tests/http_test_server.py --tos
Serving HTTP at http://127.0.0.1:54115...
Current ToS version: 2024-11-22 10:54:57 CST
Press Enter to increment ToS version, Ctrl-C to exit.
```

> [!NOTE]
> The sample channel with a ToS offers the option to increment the ToS version to mock a ToS version update.

## Testing

```bash
$ conda activate conda-tos
(conda-tos) $ conda install --file=tests/requirements-ci.txt
(conda-tos) $ pytest --cov=conda_anaconda_tos
```
