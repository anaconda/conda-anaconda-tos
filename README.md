# conda-anaconda-tos

[![Conda Version](https://img.shields.io/conda/vn/main/conda-anaconda-tos.svg)](https://anaconda.org/main/conda-anaconda-tos)
[![License](https://img.shields.io/github/license/anaconda/conda-anaconda-tos.svg)](LICENSE)

A conda plugin for handling Terms of Service (ToS) acceptance in commercial software repositories, providing auditable consent management and GDPR compliance.

## What is conda-anaconda-tos?

The `conda-anaconda-tos` plugin enables conda to automatically detect and manage Terms of Service acceptance when accessing commercial repositories. It provides auditable records of user consent, handles ToS updates transparently, and ensures compliance with legal requirements for commercial software distribution.

This plugin solves the critical need for verifiable Anaconda ToS acceptance in enterprise environments while maintaining a smooth user experience for conda package installation.

## Installation

The plugin must be installed in the base environment to function properly with all conda operations:

```bash
# From Anaconda's "main" channel
conda install --name=base conda-anaconda-tos
```

> [!NOTE]
> With the plugin installed into a non-`base` environment, use `$CONDA_PREFIX/bin/conda` instead of `conda` for the usage instructions below.

## Usage

### Basic Commands

| Basic Commands |
|----------------|
| ![Basic Commands Demo](demos/conda_tos.gif) |

```bash
conda tos --help

# see the status of all Terms of Service
conda tos

# conda command intercepted with Terms of Service checks
conda create --name=scratch

# clear cache & acceptance/rejection files
conda tos clean --all

# other commands for managing Terms of Service
conda tos view    # Display full Terms of Service text
conda tos accept  # Accept Terms of Service
conda tos reject  # Reject Terms of Service
conda tos interactive  # Interactive ToS management
```

### Interactive ToS Acceptance

When accessing a commercial repository for the first time or after ToS updates, you'll see an interactive prompt:

```text
Do you accept the Terms of Service (ToS) for https://repo.anaconda.com/pkgs/main? [(a)ccept/(r)eject/(v)iew]:
Do you accept the Terms of Service (ToS) for https://repo.anaconda.com/pkgs/msys2? [(a)ccept/(r)eject/(v)iew]:
Do you accept the Terms of Service (ToS) for https://repo.anaconda.com/pkgs/r? [(a)ccept/(r)eject/(v)iew]:
```

| Interactive Accept | Interactive Reject |
|--------------------|--------------------|
| ![Interactive Accept Demo](demos/interactive_accept.gif) | ![Interactive Reject Demo](demos/interactive_reject.gif) |

## Auto Acceptance

Configure ToS auto acceptance in your `.condarc` file

```yaml
plugins:
  auto_accept_tos: true
```

Or use the command-line flag (conda >= 25.5.0):

```bash
conda config --set plugins.auto_accept_tos yes
```

Or set the environment variable:

```bash
export CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes
```

## Jupyter Environments

In Jupyter notebook environments, interactive prompts are disabled. Users must explicitly accept or reject Terms of Service by running:

## CI/CD Environments

In CI/CD environments (detected via `CI=true`), the plugin will automatically accept Terms of Service and print a warning message. This ensures automated builds don't get blocked waiting for user input.

### Using with Docker in CI/CD Systems

When using Anaconda's Docker images in continuous integration systems, the `CI` environment variable might not be automatically passed to the container, which can lead to unexpected ToS prompts during your CI/CD workflows.

### GitHub Actions Behavior

In GitHub Actions, the `CI` environment variable is not sufficiently detected automatically.

We recommend passing the `CONDA_PLUGINS_AUTO_ACCEPT_TOS` environment variable to Docker or explicitly accepting the ToS by running `conda tos accept`:

- **Pass the `CONDA_PLUGINS_AUTO_ACCEPT_TOS` environment variable to Docker**:

   ```bash
   # Using Docker CLI
   docker run -e CONDA_PLUGINS_AUTO_ACCEPT_TOS=true continuumio/anaconda3 conda install some-package
   ```

   In GitHub Actions workflow:

   ```yaml
   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Run in Docker
           run: |
             docker run -e CONDA_PLUGINS_AUTO_ACCEPT_TOS=true continuumio/anaconda3 conda install some-package
   ```

- **Explicitly accept ToS in your Docker command**:

   ```bash
   # Using Docker CLI
   docker run continuumio/anaconda3 bash -c "conda tos accept && conda install some-package"
   ```

   In GitHub Actions workflow with Docker container action:

   ```yaml
   jobs:
     build:
       runs-on: ubuntu-latest
       container:
         image: continuumio/anaconda3
       steps:
         - uses: actions/checkout@v3
         - name: Accept ToS and install packages
           run: |
             conda tos accept
             conda install some-package
   ```

> [!NOTE]
> Service containers and composite actions in GitHub Actions also inherit the runner's environment, including the `CI` variable. However, manually invoked Docker commands within steps do not automatically inherit these variables.

## How It Works

The plugin operates transparently during normal conda operations:

1. **Detection**: Automatically detects ToS requirements when accessing commercial repositories
2. **Version Tracking**: Monitors ToS versions and prompts for re-acceptance when terms change
3. **Local Storage**: Maintains secure local records of acceptance with timestamps
4. **Minimal Impact**: Checks for updates during explicit conda commands with configurable cache timeout
5. **Compliance**: Provides GDPR-compliant consent management with data minimization
6. **HTTP Headers**: Uses the `Anaconda-ToS-Accept` header to transmit acceptance tokens to repositories
7. **Environment Detection**: Automatically adjusts behavior in CI/CD and Jupyter environments

## Privacy and Compliance

This plugin implements privacy-by-design principles:

- **Data Minimization**: Collects only necessary acceptance proof
- **User Rights**: Supports GDPR rights including consent withdrawal
- **Audit Trail**: Provides verifiable logs for compliance requirements
- **Anonymous Tokens**: Uses tokens rather than personal identifiers

For privacy inquiries or to exercise your data rights, contact the repository administrator.

## Troubleshooting

### ToS Prompt Appears Repeatedly

This typically occurs when:

- The ToS has been updated
- Local acceptance records are corrupted
- Plugin is not installed in base environment

Solution:

```bash
conda install --name base --force-reinstall conda-anaconda-tos
```

## Testing

### Development Environment Setup

For development and testing, set up a dedicated environment:

```bash
git clone https://github.com/anaconda/conda-anaconda-tos.git
cd conda-anaconda-tos
conda create --name=cat-dev --file=tests/requirements.txt
conda activate cat-dev
(cat-dev) pip install -e .
```

### Running Tests

```bash
# Activate the development environment
conda activate cat-dev

# Install test dependencies
(cat-dev) conda install --file=tests/requirements-ci.txt

# Run tests with coverage
(cat-dev) pytest --cov=conda_anaconda_tos
```

### Testing Canary Builds

To test the latest development version ("canary"):

```bash
conda install --name=base distribution-plugins/label/dev::conda-anaconda-tos
```

### Testing with Local Server

To test with a local server, use `tests/http_test_server.py` and the `--channel` option:

> [!NOTE]
> The port is random and just an example.

```bash
# Run conda tos with a custom channel
(cat-dev) $CONDA_PREFIX/bin/conda tos --channel=http://127.0.0.1:53095/
```

#### A Sample Channel without Terms of Service

```bash
# Activate the development environment
conda activate cat-dev

# Run the test server without ToS
(cat-dev) python tests/http_test_server.py
Serving HTTP at http://127.0.0.1:54115...
Press Enter or Ctrl-C to exit.
```

#### A Sample Channel with Terms of Service

```bash
# Activate the development environment
conda activate cat-dev

# Run the test server with ToS enabled
(cat-dev) python tests/http_test_server.py --tos
Serving HTTP at http://127.0.0.1:54115...
Current ToS version: 2024-11-22 10:54:57 CST
Press Enter to increment ToS version, Ctrl-C to exit.
```

> [!NOTE]
> The sample channel with a ToS offers the option to increment the ToS version to mock a ToS version update.

## Frequently Asked Questions

<details>
<summary><h3>Why do I need this plugin?</h3></summary>

This plugin is a helpful tool for managing Terms of Service requirements for commercial repositories. It provides a streamlined way to be informed about and manage ToS acceptance for channels, but is not strictly required for accessing these repositories.

</details>

<details>
<summary><h3>Where are the acceptance records stored?</h3></summary>

Acceptance records are stored locally, and the location depends on the options you choose when accepting the ToS. When using `conda tos accept`, you can specify one of these storage options:

| Option              | Description                  | Unix/Linux Path                | Windows Path                    |
|---------------------|------------------------------|--------------------------------|---------------------------------|
| `--user` (default)  | User directory               | `~/.conda/tos`                 | `%USERPROFILE%\.conda\tos\`     |
| `--system`          | Conda installation directory | `$CONDA_ROOT/conda-meta/tos`   | `%CONDA_ROOT%\conda-meta\tos`   |
| `--site`            | System-wide location         | `/etc/conda/tos`               | `C:/ProgramData/conda/tos`      |
| `--env`             | Current conda environment    | `$CONDA_PREFIX/conda-meta/tos` | `%CONDA_PREFIX%\conda-meta\tos` |
| `--tos-root PATH`   | Custom location              | User-specified path            | User-specified path             |

When checking for ToS acceptance, the plugin searches all these locations (and a few more) in a specific order, so acceptance in any location will be recognized. The records include timestamps and version information for auditing purposes.

</details>

<details>
<summary><h3>How do I know if my ToS acceptance is still valid?</h3></summary>

Run `conda tos` to see the status of all Terms of Service. This will show which channels have accepted ToS and when they were last accepted.

</details>

<details>
<summary><h3>Can I use this plugin in automated CI/CD pipelines?</h3></summary>

Yes, the plugin is designed to work in non-interactive environments. The plugin will automatically try to detect CI/CD environments (see [CI/CD Environments](#cicd-environments) section for details). You can also explicitly set the `CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes` environment variable or configure `auto_accept_tos: true` in your `.condarc` file.

</details>

<details>
<summary><h3>What happens if I reject the Terms of Service?</h3></summary>

If you reject the ToS, you won't be able to access the repository. The plugin will prevent conda from downloading packages from that repository until you accept the ToS or remove the repository from your channels.

</details>

<details>
<summary><h3>How often will I need to accept the Terms of Service?</h3></summary>

You only need to accept the ToS once per version. If the repository updates its ToS, you'll be prompted to accept the new version the next time you try to access it.

</details>

<details>
<summary><h3>Can I view the full Terms of Service text?</h3></summary>

Yes, run `conda tos view --channel=CHANNEL_URL` to see the full text of the Terms of Service for a specific channel.

</details>

<details>
<summary><h3>How do I accept ToS for multiple channels at once?</h3></summary>

Use `conda tos accept` to accept Terms of Service for all channels that require it.

</details>

<details>
<summary><h3>Is my personal information shared when I accept the ToS?</h3></summary>

No, the plugin uses anonymous tokens rather than personal identifiers. Only the acceptance record with timestamp is stored locally and transmitted to the repository.

</details>

<details>
<summary><h3>How do I troubleshoot ToS-related issues?</h3></summary>

If you encounter issues, first try `conda tos clean --all` to clear the cache and acceptance records, then reinstall the plugin with `conda install --name base --force-reinstall conda-anaconda-tos`.

</details>

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

- File bug reports and feature requests
- Open pull requests to resolve issues
- Review open pull requests
- Report any typos or improvements for documentation
- Engage in discussions and add new ideas

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [conda](https://github.com/conda/conda) - The package management system
- [conda-plugin-template](https://github.com/conda/conda-plugin-template) - Template for creating conda plugins
- [conda-incubator/plugins](https://github.com/conda-incubator/conda-plugins) - Collection of conda plugins
