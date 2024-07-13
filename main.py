import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, simpledialog, BooleanVar, Checkbutton
import json
import logging
import requests
import socket
import subprocess
import threading
import time
import re

class OllamaGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Ollama LLM Python Interface")
        self.master.geometry("1000x600")

        self.ollama_url = "http://localhost:11434"
        logging.basicConfig(level=logging.DEBUG)

        self.models = self.get_available_models()
        self.selected_model = tk.StringVar(value=self.models[0] if self.models else "")
        
        self.is_processing = False
        self.stop_requested = False
        self.code_blocks = []
        self.code_block_vars = []

        self.night_mode = False
        self.create_widgets()
        self.apply_theme()

    def get_available_models(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            response.raise_for_status()
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        except Exception as e:
            logging.error(f"Failed to fetch models: {str(e)}")
            return ["deepseek-coder-v2:latest", "llama2", "mistral", "vicuna"]

    def create_widgets(self):
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_rowconfigure(2, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        model_frame = ttk.Frame(self.master)
        model_frame.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

        ttk.Label(model_frame, text="Select Model:").pack(side="left")
        model_combobox = ttk.Combobox(model_frame, textvariable=self.selected_model, values=self.models)
        model_combobox.pack(side="left", padx=5)

        self.night_mode_button = ttk.Button(model_frame, text="🌙", command=self.toggle_night_mode)
        self.night_mode_button.pack(side="right")

        row1 = ttk.Frame(self.master)
        row1.grid(row=1, column=0, columnspan=2, pady=10, padx=10, sticky="nsew")
        row1.grid_rowconfigure(0, weight=1)
        row1.grid_columnconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(row1, wrap=tk.WORD)
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.config(state='disabled')

        self.progress_bar = ttk.Progressbar(row1, orient="horizontal", length=200, mode="indeterminate")
        self.progress_bar.grid(row=1, column=0, pady=5, sticky="ew")

        row2 = ttk.Frame(self.master)
        row2.grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="nsew")
        row2.grid_columnconfigure(0, weight=7)
        row2.grid_columnconfigure(1, weight=3)
        row2.grid_rowconfigure(0, weight=1)

        col1 = ttk.Frame(row2)
        col1.grid(row=0, column=0, sticky="nsew")
        col1.grid_rowconfigure(0, weight=1)
        col1.grid_columnconfigure(0, weight=1)

        self.user_input = tk.Text(col1, wrap=tk.WORD)
        self.user_input.grid(row=0, column=0, sticky="nsew")

        button_frame = ttk.Frame(col1)
        button_frame.grid(row=1, column=0, sticky="ew")

        self.send_button = ttk.Button(button_frame, text="Send", command=self.send_message)
        self.send_button.pack(side="left", expand=True)

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_request, state="disabled")
        self.stop_button.pack(side="left", expand=True)

        col2 = ttk.Frame(row2, width=200)
        col2.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        col2.grid_propagate(False)

        self.response_info = ttk.Label(col2, text="Response Info:", justify="left")
        self.response_info.pack(anchor="w")

        self.start_time_var = tk.StringVar()
        self.end_time_var = tk.StringVar()
        self.response_length_var = tk.StringVar()

        ttk.Label(col2, textvariable=self.start_time_var, justify="left").pack(anchor="w")
        ttk.Label(col2, textvariable=self.end_time_var, justify="left").pack(anchor="w")
        ttk.Label(col2, textvariable=self.response_length_var, justify="left").pack(anchor="w")

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

    def toggle_night_mode(self):
        self.night_mode = not self.night_mode
        self.apply_theme()

    def apply_theme(self):
        if self.night_mode:
            self.master.configure(bg='#2b2b2b')
            fg_color = 'white'
            bg_color = '#2b2b2b'
            text_bg_color = '#3c3f41'
            self.night_mode_button.configure(text="☀️")
        else:
            self.master.configure(bg='#f0f0f0')
            fg_color = 'black'
            bg_color = '#f0f0f0'
            text_bg_color = 'white'
            self.night_mode_button.configure(text="🌙")

        style = ttk.Style()
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=bg_color, foreground=fg_color)
        style.configure('TCombobox', fieldbackground=text_bg_color, background=bg_color, foreground=fg_color)

        self.chat_display.configure(bg=text_bg_color, fg=fg_color)
        self.user_input.configure(bg=text_bg_color, fg=fg_color)
        self.status_bar.configure(background=bg_color, foreground=fg_color)

        for widget in self.master.winfo_children():
            if isinstance(widget, ttk.Frame):
                widget.configure(style='TFrame')
            elif isinstance(widget, ttk.Label):
                widget.configure(style='TLabel')
            elif isinstance(widget, ttk.Button):
                widget.configure(style='TButton')
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style='TCombobox')

    def send_message(self):
        user_message = self.user_input.get("1.0", tk.END).strip()
        if not user_message or self.is_processing:
            return

        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"You: {user_message}\n\n")
        self.user_input.delete("1.0", tk.END)

        self.progress_bar.start()
        self.status_var.set("Processing request...")
        self.is_processing = True
        self.stop_requested = False
        self.send_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self.start_time = time.time()
        self.start_time_var.set(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.end_time_var.set("End Time: Processing...")
        self.response_length_var.set("Response Length: 0 characters")
        
        threading.Thread(target=self.process_message, args=(user_message,), daemon=True).start()

    def stop_request(self):
        self.stop_requested = True

    def process_message(self, user_message):
        model = self.selected_model.get()
        
        try:
            logging.info(f"Resolving localhost: {socket.gethostbyname('localhost')}")
        except socket.gaierror as e:
            logging.error(f"Error resolving localhost: {e}")
            self.master.after(0, self.update_chat, f"Error: Unable to resolve localhost. {str(e)}")
            return

        try:
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            if ":11434" not in result.stdout:
                logging.error("Port 11434 is not open")
                self.master.after(0, self.update_chat, "Error: Port 11434 is not open. Please ensure Ollama is running.")
                return
        except subprocess.CalledProcessError as e:
            logging.error(f"Error checking port: {e}")
            self.master.after(0, self.update_chat, f"Error: Unable to check if port 11434 is open. {str(e)}")
            return

        try:
            logging.info(f"Sending request to Ollama API: {self.ollama_url}/api/generate")
            headers = {"Content-Type": "application/json"}
            data = {
                "model": model,
                "prompt": user_message,
                "stream": True
            }
            logging.debug(f"Request data: {json.dumps(data)}")
            
            full_response = ""
            with requests.post(f"{self.ollama_url}/api/generate", headers=headers, json=data, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if self.stop_requested:
                        logging.info("Request stopped by user")
                        break
                    if line:
                        json_response = json.loads(line)
                        if 'response' in json_response:
                            chunk = json_response['response']
                            full_response += chunk
                            self.master.after(0, self.update_chat, chunk)
                            self.master.after(0, self.update_response_info, len(full_response))
                        if json_response.get('done', False):
                            break

            if not self.stop_requested:
                self.master.after(0, self.process_code_blocks, full_response)

        except requests.RequestException as e:
            logging.error(f"Error connecting to Ollama: {str(e)}")
            self.master.after(0, self.update_chat, f"Error connecting to Ollama: {str(e)}\nPlease check if Ollama is running and accessible.")
        except json.JSONDecodeError:
            logging.error("Received invalid JSON response from Ollama")
            self.master.after(0, self.update_chat, "Error: Received invalid response from Ollama. The response was not in the expected JSON format.")
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            self.master.after(0, self.update_chat, f"Unexpected error occurred: {str(e)}")
        finally:
            self.master.after(0, self.finish_processing)

    def update_chat(self, ai_response, widget=None):
        self.chat_display.config(state='normal')
        if widget:
            self.chat_display.window_create(tk.END, window=widget)
        else:
            self.chat_display.insert(tk.END, ai_response)
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def update_response_info(self, length):
        self.response_length_var.set(f"Response Length: {length} characters")

    def finish_processing(self):
        self.is_processing = False
        self.stop_requested = False
        self.progress_bar.stop()
        self.status_var.set("Ready")
        self.send_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.config(state='disabled')
        
        end_time = time.time()
        self.end_time_var.set(f"End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        duration = end_time - self.start_time
        self.response_info.config(text=f"Response Info:\nDuration: {duration:.2f} seconds")

    def process_code_blocks(self, response):
        self.code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        self.code_block_vars = []
        self.code_block_filenames = []
        
        for i, code_block in enumerate(self.code_blocks, 1):
            var = BooleanVar()
            self.code_block_vars.append(var)
            
            # Extract suggested filename
            filename = self.extract_filename(response, code_block)
            self.code_block_filenames.append(filename)
            
            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, f"\nCode Block {i} ({filename}):\n")
            self.chat_display.insert(tk.END, code_block)
            self.chat_display.insert(tk.END, "\n")
            
            checkbox = Checkbutton(self.chat_display, text=f"Save Code Block {i}", variable=var)
            self.chat_display.window_create(tk.END, window=checkbox)
            self.chat_display.insert(tk.END, "\n\n")
            self.chat_display.config(state='disabled')
        
        if self.code_blocks:
            save_button = ttk.Button(self.chat_display, text="Save Selected Code Blocks", command=self.save_selected_code_blocks)
            self.chat_display.config(state='normal')
            self.chat_display.window_create(tk.END, window=save_button)
            self.chat_display.insert(tk.END, "\n\n")
            self.chat_display.config(state='disabled')

    def extract_filename(self, response, code_block):
        # Look for filename suggestions in various formats
        patterns = [
            r'\*\*([\w.-]+)\*\*\s*```',  # **filename.ext** ```
            r'#{1,6}\s*(?:\d+\.)?\s*.*?`([\w.-]+)`',  # ### N. Description in `filename.ext`
            r'(?:^|\n)([\w.-]+):\s*```',  # filename.ext: ```
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                return match.group(1)
        
        # Check for filename at the top of the code block
        first_line = code_block.strip().split('\n')[0]
        if first_line.startswith('#'):
            filename_match = re.search(r'#\s*([\w.-]+)', first_line)
            if filename_match:
                return filename_match.group(1)
        
        # If no filename is found, try to extract the first class or function name
        class_match = re.search(r'class\s+(\w+)', code_block)
        func_match = re.search(r'def\s+(\w+)', code_block)
        
        if class_match:
            return f"{class_match.group(1)}.py"
        elif func_match:
            return f"{func_match.group(1)}.py"
        
        # If all else fails, use a generic name
        return f"code_block_{len(self.code_blocks)}.py"

    def save_selected_code_blocks(self):
        for i, (var, code_block, filename) in enumerate(zip(self.code_block_vars, self.code_blocks, self.code_block_filenames), 1):
            if var.get():
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".py",
                    filetypes=[("Python files", "*.py"), ("All files", "*.*")],
                    initialfile=filename
                )
                if file_path:
                    with open(file_path, 'w') as file:
                        file.write(code_block.strip())
                    self.update_chat(f"\nCode block {i} saved to {file_path}\n")
                else:
                    self.update_chat(f"\nSave cancelled for code block {i}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaGUI(root)
    root.mainloop()
