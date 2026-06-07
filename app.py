import base64
import os
from datetime import date, timedelta

from flask import Flask, render_template, abort, send_from_directory, Response, request

from data import BIO, PROJECTS, CONTACT, TOOLS

app = Flask(__name__)


@app.route("/")
def index():
    resume_exists = os.path.exists(
        os.path.join(app.static_folder, "files", "resume.pdf")
    )
    return render_template("index.html", bio=BIO, projects=PROJECTS,
                           contact=CONTACT, tools=TOOLS, resume=resume_exists)


def _tool(slug):
    """Look up a tool's project-profile metadata by slug."""
    return next((t for t in TOOLS if t["slug"] == slug), None)


@app.route("/password")
def password_page():
    """Privacy-respecting password strength analyzer. Analysis runs in the browser."""
    return render_template("password.html", bio=BIO, contact=CONTACT,
                           tool=_tool("password-strength"))


@app.route("/projects/<slug>")
def project_detail(slug):
    project = next((p for p in PROJECTS if p["slug"] == slug), None)
    if project is None:
        abort(404)
    # Only show the screenshot if the image file actually exists; otherwise the
    # template falls back to a clean placeholder instead of a broken-image icon.
    has_image = bool(project.get("image")) and os.path.exists(
        os.path.join(app.static_folder, project["image"])
    )
    return render_template("project.html", project=project, bio=BIO,
                           contact=CONTACT, has_image=has_image)


@app.route("/favicon.ico")
def favicon():
    path = os.path.join(app.static_folder, "favicon.ico")
    if os.path.exists(path):
        return send_from_directory(app.static_folder, "favicon.ico")
    return Response(status=204)


@app.route("/resume")
def resume():
    files_dir = os.path.join(app.static_folder, "files")
    path = os.path.join(files_dir, "resume.pdf")
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(files_dir, "resume.pdf")


@app.route("/backtest", methods=["GET", "POST"])
def backtest_page():
    """Interactive MA-crossover backtester. Powered by backtest.py."""
    today = date.today()
    defaults = {
        "ticker": "AAPL",
        "start": (today - timedelta(days=365 * 4)).isoformat(),
        "end": today.isoformat(),
        "capital": "10000",
        "short": "20",
        "long": "50",
    }

    if request.method != "POST":
        return render_template(
            "backtest.html",
            bio=BIO, contact=CONTACT, tool=_tool("backtester"),
            form=defaults, result=None, chart=None, error=None,
        )

    form = {k: (request.form.get(k) or defaults[k]).strip() for k in defaults}

    import backtest  # imported lazily so a missing yfinance never breaks the home page
    error = None
    result_dict = None
    chart_b64 = None

    # Validate the numeric fields first, with messages a human can read.
    capital = short_w = long_w = None
    try:
        capital = float(form["capital"])
    except ValueError:
        error = "Starting capital must be a number, like 10000."
    if error is None:
        try:
            short_w = int(form["short"])
            long_w = int(form["long"])
        except ValueError:
            error = "The moving-average windows must be whole numbers, like 20 and 50."

    # Run the backtest. backtest.run() raises ValueError with friendly messages
    # for bad tickers, empty data, or window problems.
    if error is None:
        try:
            result = backtest.run(
                form["ticker"], form["start"], form["end"],
                capital, short_window=short_w, long_window=long_w,
            )
            result_dict = result.to_dict()
            theme = (request.form.get("theme") or "dark").lower()
            if theme not in ("light", "dark"):
                theme = "dark"
            png = backtest.render_chart_png(result, theme=theme)
            chart_b64 = base64.b64encode(png).decode("ascii")
        except ValueError as e:
            error = str(e)
        except Exception:
            app.logger.exception("Backtest failed for %s", form)
            error = "Something went wrong running that backtest. Try different inputs."

    return render_template(
        "backtest.html",
        bio=BIO, contact=CONTACT, tool=_tool("backtester"),
        form=form, result=result_dict, chart=chart_b64, error=error,
    )


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", bio=BIO, contact=CONTACT), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
