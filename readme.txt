Flask: is a Python web framework (runs a web server)
Pip: installs flask and is a package manager for python so it can also uninstall packages

App.py: Python backend file (starts the web server, shows the site when someone visits or dopes anything, handles AI summary)

Templates: holds the HTML pages (index.html is the main page)

Static: Flask uses this folder to find never-changing files
	- style.css** controls the style of the page
	- script.js** can run JavaScript logic
	- These handle the look and behavior of the webpage

Requirements.txt: lists all Python packages the project needs

Lib and Scripts: part of the Python virtual environment
	- Keeps project dependencies separate from other Flask projects I might have
	- Installs Flask and pip for this project

### How it works:
- You run `py app.py` (Flask starts a local server)
- You go to `http://127.0.0.1:5000` in Edge (loads the website)
- You paste your notes and click "Summarize" (index.html sends the text to `/summarize`)
- Flask catches that in `app.py` and sends it to the Hugging Face API using `requests`
- Hugging Face returns a summary
- Flask sends back a JSON response
- Your HTML page displays the summary!

- IPv4: 192.168.4.253
- on phone put: http://192.168.4.253:5000

run in the cmd
- cd "C:\Users\wgodd\OneDrive\Documents\Willis Times"
- venv\Scripts\activate
- py app.py

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass