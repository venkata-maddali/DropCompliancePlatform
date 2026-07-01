import os
from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv

from drop_compliance_tool.database import init_db
from drop_compliance_tool.workflow import get_config, run_cycle

load_dotenv()

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
  <head><meta charset=\"utf-8\"><title>DROP Compliance Dashboard</title></head>
  <body>
    <h1>DROP Compliance Dashboard</h1>
    <form method=\"post\" action=\"/run\">
      <label>Cycle date <input name=\"cycle_date\" value=\"{{ today }}\" /></label><br/>
      <button type=\"submit\">Run cycle</button>
    </form>
    <pre>{{ status }}</pre>
  </body>
</html>
"""


@app.get('/')
def index():
    return render_template_string(HTML_TEMPLATE, today=os.getenv('RUN_CYCLE_DATE', ''), status='Ready')


@app.post('/run')
def run_now():
    cycle_date = request.form.get('cycle_date') or None
    config = get_config()
    run_id, output_path = run_cycle(
        cycle_date,
        config['output_dir'],
        config['base_url'],
        config['api_key'],
        config['timeout'],
        config['download_endpoint'],
        config['upload_endpoint'],
        config['hash_mode'],
        config['update_existing_records'],
    )
    return jsonify({'status': 'success', 'run_id': run_id, 'output_path': str(output_path)})


@app.post('/init-db')
def init_db_endpoint():
    init_db()
    return jsonify({'status': 'success', 'message': 'Database initialized'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('WEB_PORT', '5000')))
