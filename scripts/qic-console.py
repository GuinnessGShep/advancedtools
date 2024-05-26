import gradio as gr
from modules import script_callbacks, shared
from modules.ui_components import ResizeHandleRow
import subprocess

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

        terminal_emulator = TerminalEmulator()

        terminal_style = "background-color: black; color: white; font-family: monospace; font-size: 14px; padding: 10px; height: 400px; overflow-y: scroll; margin: 0;"
        input_style = "color: white; font-family: monospace; background-color: transparent; border: none; outline: none; width: 100%; margin: 0;"
        
        terminal_content = "<pre style='{}' id='terminal-content'>{}</pre><input type='text' id='input-field' style='{}'>".format(terminal_style, terminal_emulator.terminal_output, input_style)
        
        js_code = """
        var terminal = document.getElementById('terminal-content');
        var input = document.getElementById('input-field');

        input.focus();

        input.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                var command = input.value.trim();
                input.value = "";
                terminal.innerHTML += "<div><span style='color: #00FF00;'>$ </span>" + command + "</div>";
                
                fetch("/execute_command", {
                    method: "POST",
                    body: JSON.stringify({ command: command }),
                    headers: { "Content-Type": "application/json" }
                })
                .then(response => response.text())
                .then(output => {
                    terminal.innerHTML += "<pre>" + output + "</pre>";
                    terminal.scrollTop = terminal.scrollHeight;
                    input.focus();
                });
            } else if (event.key === "ArrowUp") {
                fetch("/navigate_command_history", {
                    method: "POST",
                    body: JSON.stringify({ direction: "up" }),
                    headers: { "Content-Type": "application/json" }
                })
                .then(response => response.text())
                .then(command => {
                    input.value = command;
                    input.setSelectionRange(input.value.length, input.value.length);
                });
            } else if (event.key === "ArrowDown") {
                fetch("/navigate_command_history", {
                    method: "POST",
                    body: JSON.stringify({ direction: "down" }),
                    headers: { "Content-Type": "application/json" }
                })
                .then(response => response.text())
                .then(command => {
                    input.value = command;
                    input.setSelectionRange(input.value.length, input.value.length);
                });
            }
        });
        """

        terminal_ui = gr.Interface(terminal_emulator.execute_command, gr.inputs.Textbox(lines=1, label=""), "html", show_input=False, allow_flag=True, title="Emulated Terminal")
        terminal_ui.launch(share=False, debug=True, inline=False, live=True, auth=None, auth_message=None, layout=None, examples=None, server_port=None, websocket_max_message_size=None, auth_function=None, ssl_certfile=None, ssl_keyfile=None, verbose=False, show_input=True, flag_is_defined=True, analytics_enabled=False, include_internal=True, blocking=False, width=None, height=None, theme=None, template=None, template_filepath=None, customize=None, **kwargs)

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
