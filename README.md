# conda-anaconda-tos

[![Conda Version](https://img.shields.io/conda/vn/main/conda-anaconda-tos.svg)](https://anaconda.org/main/conda-anaconda-tos)
[![License](https://img.shields.io/github/license/anaconda/conda-anaconda-tos.svg)](LICENSE)

A conda plugin for handling Terms of Service (ToS) acceptance in commercial software repositories, providing auditable consent management and GDPR compliance.

## What is conda-anaconda-tos?

The `conda-anaconda-tos` plugin enables conda to automatically detect and manage Terms of Service acceptance when accessing commercial repositories. It provides auditable records of user consent, handles ToS updates transparently, and ensures compliance with legal requirements for commercial software distribution.

This plugin solves the critical need for verifiable Anaconda ToS acceptance in enterprise environments while maintaining a smooth user experience for conda package installation.

## Installation

### Into `base` Environment (Recommended)

The plugin must be installed in the base environment to function properly with all conda operations:

```bash
# From Anaconda's "main" channel
conda install --name=base conda-anaconda-tos
```

> [!NOTE]
> With the plugin installed into a non-`base` environment, use `$CONDA_PREFIX/bin/conda` instead of `conda` for the usage instructions below.

## Usage

### Basic Commands

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
Terms of Service have not been accepted for the following channels. Please accept or remove them before proceeding:
• https://repo.anaconda.com/pkgs/main
• https://repo.anaconda.com/pkgs/msys2
• https://repo.anaconda.com/pkgs/r

To accept a channel's Terms of Service, run the following and replace `CHANNEL` with the channel name/URL:
    ‣ conda tos accept --override-channels --channel CHANNEL

To remove channels with rejected Terms of Service, run the following and replace `CHANNEL` with the channel name/URL:
    ‣ conda config --remove channels CHANNEL
```

### Auto Acceptance

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

### Automated Deployments and CI/CD Pipelines

For automated deployments and CI/CD pipelines, the plugin automatically detects CI and Jupyter environments to adjust its behavior accordingly:

```bash
# CI environment detection (automatically detected in many CI systems)
export CI=true

# Jupyter environment (automatically detected)
export JPY_SESSION_NAME=session
export JPY_PARENT_PID=1234
```

#### Using with Docker in CI/CD Systems

When using Anaconda's Docker images in continuous integration systems, the `CI` environment variable might not be automatically passed to the container, which can lead to unexpected ToS prompts during your CI/CD workflows.

##### GitHub Actions Behavior

In GitHub Actions, the `CI` environment variable is handled differently depending on how you use containers:

- **Automatically available**: When using the `container:` directive at the job level, GitHub Actions automatically injects the `CI=true` environment variable:

  ```yaml
  jobs:
    build:
      runs-on: ubuntu-latest
      container:
        image: continuumio/anaconda3
      steps:
        - run: echo "CI is $CI"    # prints "CI is true"
        - run: conda install some-package  # ToS will be auto-accepted
  ```

- **Not automatically available**: When running Docker commands within steps, you need to explicitly pass the `CI` environment variable:

  ```yaml
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - run: docker run continuumio/anaconda3 echo "CI is $CI"  # CI will be empty
  ```

For cases where the `CI` environment variable isn't automatically available, there are two ways to handle ToS acceptance:

1. **Pass the CI environment variable to Docker**:

   ```bash
   # Using Docker CLI
   docker run -e CI=true continuumio/anaconda3 conda install some-package
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
             docker run -e CI=true continuumio/anaconda3 conda install some-package
   ```

2. **Explicitly accept ToS in your Docker command**:

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
7. **Environment Detection**: Automatically adjusts behavior in CI and Jupyter environments

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

### Why do I need this plugin?

This plugin is required to access commercial repositories that have Terms of Service requirements. Without it, you won't be able to install packages from these repositories, as conda will block access until the ToS is accepted.

### Where are the acceptance records stored?

Acceptance records are stored locally in your conda configuration directory, typically at `~/.conda/tos/` on Unix-like systems or `%USERPROFILE%\.conda\tos\` on Windows. These records include timestamps and version information for auditing purposes.

### How do I know if my ToS acceptance is still valid?

Run `conda tos` to see the status of all Terms of Service. This will show which channels have accepted ToS and when they were last accepted.

### Can I use this plugin in automated CI/CD pipelines?

Yes, the plugin is designed to work in non-interactive environments. Use the `--accept-tos` flag with conda commands, set the `CONDA_AUTO_ACCEPT_TOS=yes` environment variable, or configure `auto_accept_tos: true` in your `.condarc` file.

### What happens if I reject the Terms of Service?

If you reject the ToS, you won't be able to access the repository. The plugin will prevent conda from downloading packages from that repository until you accept the ToS or remove the repository from your channels.

### How often will I need to accept the Terms of Service?

You only need to accept the ToS once per version. If the repository updates its ToS, you'll be prompted to accept the new version the next time you try to access it.

### Can I view the full Terms of Service text?

Yes, run `conda tos view --channel=CHANNEL_URL` to see the full text of the Terms of Service for a specific channel.

### How do I accept ToS for multiple channels at once?

Use `conda tos accept` to accept Terms of Service for all channels that require it.

### Is my personal information shared when I accept the ToS?

No, the plugin uses anonymous tokens rather than personal identifiers. Only the acceptance record with timestamp is stored locally and transmitted to the repository.

### How do I troubleshoot ToS-related issues?

If you encounter issues, first try `conda tos clean --all` to clear the cache and acceptance records, then reinstall the plugin with `conda install --name base --force-reinstall conda-anaconda-tos`.

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
