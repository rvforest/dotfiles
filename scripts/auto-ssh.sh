# .bash_profile

# --- Configure your target server details ---
TARGET_USER="your_username_on_server2"  # Replace with your username on the second server
TARGET_HOST="server2_address"      # Replace with the IP or hostname of the second server
# ---------------------------------------------

# Check if the shell is interactive and a login shell
if [ -n "$PS1" ] && [ -n "$BASH_VERSION" ] && shopt -q login_shell; then
    # Attempt to connect via SSH
    ssh "$TARGET_USER@$TARGET_HOST"

    # Check the exit status of the SSH command
    # An exit status of 0 usually indicates success.
    # A non-zero exit status (e.g., 255) indicates an error or failure.
    if [ $? -ne 0 ]; then
        echo "SSH connection to $TARGET_HOST failed. Staying in the local shell."
        # You can add further actions here if needed upon failed connection.
    fi
fi
