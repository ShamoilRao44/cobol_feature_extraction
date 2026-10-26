import os

from flask import Flask, render_template, request, send_file

from stages.stage1_inventory.inventory import build_inventory, write_inventory

app = Flask(__name__)
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the inventory page."""
    if request.method == "GET":
        return render_template("index.html", folder_path="", inventory=None, error=None)

    submitted_path = request.form.get("folder_path", "")
    folder_path = submitted_path.strip().strip('"')

    try:
        inventory = build_inventory(folder_path)
    except ValueError as error:
        return render_template(
            "index.html",
            folder_path=submitted_path,
            inventory=None,
            error=str(error),
        )

    write_inventory(inventory, WORKSPACE_DIR)
    return render_template(
        "index.html",
        folder_path=submitted_path,
        inventory=inventory,
        error=None,
    )


@app.route("/inventory.json", methods=["GET"])
def download_inventory():
    """Return the generated inventory JSON file."""
    inventory_path = os.path.join(WORKSPACE_DIR, "inventory.json")
    if not os.path.isfile(inventory_path):
        return "No inventory yet", 404
    return send_file(inventory_path)


if __name__ == "__main__":
    app.run(debug=True)
