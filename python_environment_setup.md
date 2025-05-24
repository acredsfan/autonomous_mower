# Python Environment Setup for Mower Application on Raspberry Pi

This document guides you through setting up the correct Python environment on your Raspberry Pi to run the mower application.

## 1. Python Version Requirement

The mower application requires **Python 3.10 or newer**.

To check your installed Python 3 version, open a terminal and run:
```bash
python3 --version
```
If your version is older than 3.10, you may need to upgrade your Raspberry Pi OS or install a newer Python version separately (which is beyond the scope of this guide). Most recent Raspberry Pi OS versions (Bookworm and later) come with Python 3.10+.

## 2. Setting Up a Virtual Environment

Using a Python virtual environment is highly recommended. It isolates the project's dependencies from the system-wide Python packages, preventing conflicts and ensuring a clean, reproducible environment.

### Install `python3-venv`
If the `venv` module is not already installed (it usually is with standard Python installations), you can install it using:
```bash
sudo apt-get update
sudo apt-get install python3-venv -y
```

### Create and Activate the Virtual Environment
1.  Navigate to your project directory (e.g., where you cloned the mower application repository).
    ```bash
    # cd /path/to/your/mower_project
    ```
2.  Create a virtual environment. It's common to name it `venv` or something descriptive like `mower_env`:
    ```bash
    python3 -m venv mower_env
    ```
    This will create a directory named `mower_env` (or your chosen name) in your current location.

3.  Activate the virtual environment:
    ```bash
    source mower_env/bin/activate
    ```
    Once activated, your terminal prompt will usually change to show the name of the virtual environment (e.g., `(mower_env) user@raspberrypi:~ $`). All `pip` installs and Python commands will now operate within this isolated environment.

### Deactivate the Virtual Environment
When you're done working in the virtual environment, you can deactivate it by simply typing:
```bash
deactivate
```
Your prompt will return to normal.

## 3. Installing Python Dependencies

With the virtual environment activated, you can install all the required Python packages. These are listed in the `requirements.txt` file provided with the mower application.

1.  Ensure your virtual environment is activated (`source mower_env/bin/activate`).
2.  Make sure the `requirements.txt` file is in your current directory. If you are in the root of the project repository, it should be there.
3.  Install the dependencies using `pip`:
    ```bash
    pip install -r requirements.txt
    ```
    This command will download and install all the packages specified in the file. This process might take some time, especially on a Raspberry Pi, as some packages may need to be downloaded or even compiled.

## 4. Important Note on Build Tools

Some Python packages, especially those with C extensions, may need to be compiled from source during installation via `pip`. This compilation process requires certain system-level build tools.

*   **Required Tools:** Ensure you have `build-essential`, `python3-dev`, and other necessary development libraries installed on your Raspberry Pi.
*   **Refer to System Setup:** The `rpi_system_dependencies.sh` script (or the corresponding setup guide `raspberry_pi_system_dependencies.md`) contains commands to install these essential build tools. Please ensure you have run that script or installed those packages.
*   **Troubleshooting `pip` Errors:** If `pip install -r requirements.txt` fails for a specific package, carefully examine the error messages. Often, the output will indicate missing system libraries or tools (e.g., `unable to find cc`, `missing header file X.h`). You might need to install additional `-dev` packages using `sudo apt-get install <package-name>-dev`.

## Conclusion

By following these steps, you will have a dedicated Python environment for the mower application, ensuring that all dependencies are correctly installed and managed. Remember to activate the virtual environment (`source mower_env/bin/activate`) each time you work on the project.I have created the `python_environment_setup.md` document as requested.

It includes:
1.  **Python Version:** Confirmation of Python 3.10+ requirement and the command `python3 --version`.
2.  **Virtual Environment Setup:** Explanation of benefits, command to install `python3-venv`, and step-by-step commands for creating (`python3 -m venv mower_env`), activating (`source mower_env/bin/activate`), and deactivating (`deactivate`) a virtual environment.
3.  **Installing Dependencies:** Command `pip install -r requirements.txt` for use within the activated environment, with a note about the `requirements.txt` file location.
4.  **Build Tools Reminder:** A section emphasizing the need for build tools like `python3-dev` and `build-essential`, referring to the previously created `rpi_system_dependencies.sh` script, and advice on checking pip error logs.

The document is formatted in markdown for clarity and ease of use.
