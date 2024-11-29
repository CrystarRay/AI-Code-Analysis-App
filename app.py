from flask import Flask, render_template, request, redirect, url_for, flash
import os
import requests
import json
import re
from markupsafe import escape  # Use to safely escape HTML content

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For flash messages

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Supported file extensions for code files
CODE_FILE_EXTENSIONS = {'.py', '.js', '.java', '.cpp', '.c', '.cs', '.rb', '.html', '.css'}


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            prompt = request.form.get('prompt')
            if not prompt:
                flash('Please enter a prompt')
                return redirect(request.url)

            prompt = "\n\n" + prompt
            file = request.files.get('file')

            # Check if a file is provided and if its extension is recognized
            file_content = ""
            if file and file.filename != '':
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext in CODE_FILE_EXTENSIONS:
                    # Save the uploaded file
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                    file.save(file_path)
                    flash('File successfully uploaded and prompt received')

                    # Read the file content
                    with open(file_path, 'r') as f:
                        file_content = f.read()
                else:
                    flash('Uploaded file is not a recognized code file type')
                    return redirect(request.url)

            # Integrate with ARLIAI API for analyzing the prompt (and file if provided)
            ARLIAI_API_KEY = "98989670-0b90-4a38-92af-5512757ecb7f"
            url = "https://api.arliai.com/v1/completions"

            # Create the payload for the ARLIAI API request
            complete_prompt = prompt + file_content
            payload = json.dumps({
                "model": "Meta-Llama-3.1-70B-Instruct",
                "prompt": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>" + complete_prompt + "<|eot_id|><|start_header_id|>user<|end_header_id|>\n\nHello there!<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                "repetition_penalty": 1.1,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_tokens": 1024
            })

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {ARLIAI_API_KEY}"
            }

            response = requests.post(url, headers=headers, data=payload, timeout=60)
            response.raise_for_status()

            # Extract response data
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                full_response = response_data['choices'][0].get('text', '').replace('\\n', '\n')

                # Escape the HTML content to prevent rendering issues
                full_response = escape(full_response)

                # Replace triple backticks with <pre><code> for code blocks
                full_response = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', full_response, flags=re.DOTALL)

                # Replace inline code with <code> for inline formatting
                full_response = re.sub(r'`([^`]+)`', r'<code>\1</code>', full_response)
                print(full_response)

            else:
                full_response = "No valid response from the AI model."

            # Render the response from the AI in the template
            return render_template('index.html', response=full_response)
        except requests.exceptions.RequestException as e:
            flash(f"An error occurred while connecting to the AI service: {str(e)}")
            return redirect(request.url)
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}")
            return redirect(request.url)

    return render_template('index.html')


@app.after_request
def cleanup(response):
    # Remove all files in the uploads/ directory after sending the response
    upload_folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove the file or symlink
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
    return response


if __name__ == '__main__':
    app.run(debug=True)
