#!/bin/bash

# Step 1: Install system dependencies via apt-get
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev \
                        python3-dev python3-pip i2c-tools gpsd gpsd-clients \
                        python3-gps python3-libgpiod libportaudio2 \
                        libportaudiocpp0 portaudio19-dev

# Check if the system dependencies were installed successfully
if [ $? -ne 0 ]; then
  echo "Error: Failed to install system dependencies. Exiting."
  exit 1
fi
echo "System dependencies installed successfully."

# Step 2: Create and activate a virtual environment with --system-site-packages
echo "Creating virtual environment..."
python3 -m venv --system-site-packages venv

if [ $? -ne 0 ]; then
  echo "Error: Failed to create virtual environment. Exiting."
  exit 1
fi

# Activate the virtual environment
source venv/bin/activate

if [ $? -ne 0 ]; then
  echo "Error: Failed to activate virtual environment. Exiting."
  exit 1
fi

echo "Virtual environment created and activated."

# Step 3: Install Python packages from requirements.txt one by one and log failures
FAILED_PACKAGES=()

echo "Installing Python packages from requirements.txt..."

while read requirement; do
  if ! pip install "$requirement"; then
    echo "Failed to install $requirement, skipping..."
    FAILED_PACKAGES+=("$requirement")
  fi
done < requirements.txt

# Step 4: Report failed installations (if any)
if [ ${#FAILED_PACKAGES[@]} -eq 0 ]; then
  echo "All packages installed successfully."
else
  echo "The following packages failed to install:"
  for pkg in "${FAILED_PACKAGES[@]}"; do
    echo "- $pkg"
  done
  echo "You may need to find alternatives or manually troubleshoot these packages."
fi

# Step 5: Deactivate the virtual environment
deactivate

echo "Setup complete."
