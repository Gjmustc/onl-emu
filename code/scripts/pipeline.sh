#!/bin/bash
# Step 1: Set network configurations
echo "Step 1: Setting network configurations..."
bash set_network_configs.sh
if [ $? -ne 0 ]; then
    echo "Failed to set network configurations."
    exit 1
fi

# Step 2: Prepare directories
echo "Step 2: Preparing directories..."
bash preparedirs.sh
if [ $? -ne 0 ]; then
    echo "Failed to prepare directories."
    exit 1
fi

# Step 3: Transmit data
echo "Step 3: Transmitting data..."
bash transmit.sh
if [ $? -ne 0 ]; then
    echo "Failed to transmit data."
    exit 1
fi

# Step 4: Post-process logs
echo "Step 4: Post-processing logs..."
bash postprocess.sh
if [ $? -ne 0 ]; then
    echo "Failed to post-process logs."
    exit 1
fi

echo "Pipeline executed successfully."