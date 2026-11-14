from flask import (
    render_template,
    request,
    redirect,
    send_from_directory,
    url_for,
    Blueprint,
)
from consts import *
from service.sanitizer import *
from service.auth import auth
from service import filemanager, reports

app = Blueprint("app", __name__)


@app.route("/")
@auth.login_required
def main_route():
    profile = request.args.get("profile")
    taskList = filemanager.get_profile_or_default(profile)
    return render_template(
        "main.html",
        rev_info        = filemanager.get_commit_hash(),
        content         = taskList.get_file_str(),
        css             = reports.parse_css(taskList.lines),
        report          = reports.get_report(taskList.lines),
        scroll          = request.args["scroll"] if "scroll" in request.args else 0,
        last_update     = taskList.last_write.timestamp(),
        current_profile = taskList.name,
        profiles        = filemanager.get_profiles()
    )


@app.route("/submit", methods=["POST"])
@auth.login_required
def submit():
    scroll = request.form["scrollPos"]
    search = request.form["content"]
    profile = request.form["profile"] # to make sure we're not overriding anything
                                      # profile is mandatory
    submission_last_update = float(request.form["last_update"])
    is_api_call = request.form.get("api") == "true"
    task_list = filemanager.get_profile(profile)
    try:
        refresh_working_copy = task_list.write_file(search, submission_last_update)
    except filemanager.FileConflict:
        return ("""<div style="max-width: 800px; margin-left: auto; margin-right: auto;">
                        <h1>⚠️ Conflicts detected!</h1>
                        <p>This save action will override content not shown because
                        it was submitted by another device/session!</p>
                        <p>To see the new version in the server, open the app in
                        another tab/browser and go back on this one</p>
                    </div>""", 409)
    except filemanager.FileContentTooBig:
        return ("Size of the file is too big, please change the FILE_MAX_LINES value",
                500)
    except filemanager.CalendarNotificationFailure as exc:
        return (str(exc), 500)

    if is_api_call:
        response = {"last_write": task_list.last_write.timestamp()}
        if refresh_working_copy:
            response["refresh_working_copy"] = True
            response["content"] = task_list.get_file_str()
        return response, 200

    return redirect(url_for("app.main_route", scroll=scroll, profile=profile))


@app.route("/cleanup", methods=["get"])
def do_cleanup():
    #note: you should block this endpoint in the reverse-proxy config to only
    #      allow local access

    code = request.args.get("code")
    if code == DAILY_CLEANUP_TRIGGER_CODE:
        filemanager.do_backup()
        reports.do_task_day_cleanup(list(filemanager.profiles.values()))
        return "OK", 200
    return "Nop", 401


@app.route("/board")
@auth.login_required
def board():
    profile = request.args.get("profile")
    task_list = filemanager.get_profile_or_default(profile)
    todo_list, done_list, deferred_list, wip_list = reports.get_board(task_list.lines)

    return render_template(
        "board.html",
        todo_list=todo_list,
        done_list=done_list,
        deferred_list=deferred_list,
        wip_list=wip_list,
        css= reports.parse_css(task_list.lines),
    )


@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")


@app.route("/commit")
@auth.login_required
def commit():
    profile = request.args.get("profile")
    filemanager.do_backup()
    return redirect(url_for("app.main_route", profile=profile))
