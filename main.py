from flask import Flask, render_template, request, redirect, send_from_directory, url_for
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime, timedelta
import subprocess
import json
import html
import os
from consts import *
from sanitizer import *


app = Flask(__name__)

auth = HTTPBasicAuth()

assert USERNAME!="" and PASSWORD!="", "Username and password must be configured"
users = {
    USERNAME: generate_password_hash(PASSWORD)
}

@auth.verify_password
def verify_password(username:dict[str,str], password):
    if username in users and \
            check_password_hash(users[username], password):
        return username

if not os.path.exists(FILE_PATH): os.makedirs(FILE_PATH)
if not os.path.exists(FILE_PATH+"/"+FILE_NAME):
    f = open(FILE_PATH+"/"+FILE_NAME, 'a+')
    f.write("Type something here...")
    f.close()


read_file = open(FILE_PATH+"/"+FILE_NAME, 'r')
lines = read_file.readlines()
read_file.close()


def parse_css(lines:list[str]) -> str:
    css_line = ":root{}" # distinguish between bad-parsing and no custom css provided
    for line in lines:
        if "<style>" in line and "</style>" in line:
            css_line = sanitize_css(line)
    return css_line


def do_backup():
    print("starting backup")

    if(not ENABLE_GIT): return

    # check if the data directory has its own git repository so that it doesn't
    # commit the file to the source code repo
    if(not os.path.exists(FILE_PATH+"/.git")): raise Exception("This is not a git repository")

    subprocess.run(['git -C '+FILE_PATH+' add todo.txt && git -C '+FILE_PATH+' commit -m "{}"'
                    .format(datetime.now().strftime("%d-%m-%Y-%H-%M"))] ,shell=True)
    if len(list(filter(None, subprocess.run(["git remote"],shell=True,capture_output=True)
                       .stdout.decode('UTF-8').split('\n')))) > 0:
        subprocess.run(['git -C '+FILE_PATH+' push'], shell=True)
    print("done")


def do_task_day_cleanup(lines:list[str]):
    twoDaysAgo = getToday((datetime.now()-timedelta(days=2)).weekday())
    for i in range(len(lines)):
        if lines[i][0] != "#":
            if "@"+twoDaysAgo in lines[i]:
                if "[x]" in lines[i]:
                    lines[i] = lines[i].replace("@"+twoDaysAgo, "").rstrip()+"\n"
                else:
                    lines[i] = lines[i].replace("@"+twoDaysAgo, "#overdue").rstrip()+"\n"

    write_file = open(FILE_PATH+"/"+FILE_NAME, mode="w")
    write_file.writelines(lines)
    write_file.close()


def getToday(date):
    if PORTUGUESE_LANG:
        return ('segunda','terca','quarta','quinta','sexta','sabado','domingo')[date]
    else: return ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')[date]


def getNextTask(index, lines):
    return "" #FIXME: Temporary fix -- does not allow for description to be presented
    if(index+1 >= len(lines)-1) or \
      ("#" in lines[index+1]) or \
      ("[" in lines[index+2]) or \
      (lines[index+1]=="\n"):
        return ""

    if(index+2 >= len(lines)-1) or \
      ("#" in lines[index+2]) or \
      ("[" in lines[index+2]) or \
      (lines[index+2]=="\n"):
        return lines[index+1]

    return lines[index+1][0:-1]+" (...)\n"


def getCurrentProjectTpl(index, lines, noSubtask=False):
    if("-----" in lines[index]):
        return tuple()
    if(len(lines[index])>=3 and lines[index][0]=="#" and lines[index][1]==">"):
        if(len(lines[index])>=3 and lines[index][2]==">" and not noSubtask):
            # subtask
            return (lines[index], ) + getCurrentProjectTpl(index-1, lines, True)
        if(not lines[index][2]==">"):
            return (lines[index], )
    if(index==0):
        return tuple()
    return getCurrentProjectTpl(index-1, lines, noSubtask)


def getCurrentProject(index, lines) -> str:
    proj_tupl = getCurrentProjectTpl(index, lines)
    if(len(proj_tupl) == 0):
        return ""
    elif(len(proj_tupl) == 1):
        return "<span class=\"reportProj\">{}</span>".format(proj_tupl[0].replace("#>", "").lstrip().rstrip())
    elif(len(proj_tupl)==2):
        return "<span class=\"reportProj\">{}<span class=\"reportSubProj\">{}</span></span>".format(
            proj_tupl[1].replace("#>", "").lstrip().rstrip(), 
            proj_tupl[0].replace("#>>", "").lstrip().rstrip())
    else:
        raise Exception("Error")


def check_sub_tasks(lines, counter):
    assert len(lines) > counter, "Counter too big"
    assert counter >= 0, "Counter cannot be negative"

    return_str = ""
    leading_spaces = len(lines[counter]) - len(lines[counter].lstrip(' '))
    counter += 1 # not the current line

    while(counter < len(lines)-1):
        # First we must determine the stride
        if len(lines[counter]) < leading_spaces+4: break
        if lines[counter][:4] != ' '*leading_spaces + '    ': break
        if "[ ]" in lines[counter] or "[w]" in lines[counter] or "[/]" in lines[counter]:
            task = re.sub(r'@(\S+)', r'<span style="color: CornflowerBlue">@\1</span>' ,lines[counter])
            task = re.sub(r'#(\S+)', r'<span style="color: DarkGreen" class="cm-tag-\1">#\1</span>' ,task)
            return_str += task
        elif "[x]" in lines[counter]:
            split_list = lines[counter].split("[x]")
            return_str += split_list[0] + "[x]" + "<del>"+''.join(split_list[1:])+"</del>"
        else:
            # end of tasks
            break
        counter+=1

    return return_str


def parse_list(lines:list[str]):
    new_lines = list()
    new_lines.append('<pre style="font-size: 18px">\n')

    today = getToday(datetime.now().weekday())
    tomorrow = getToday((datetime.now()+timedelta(days=1)).weekday())
    beforeToday = getToday((datetime.now()-timedelta(days=1)).weekday())

    report_string_today=""
    report_string_tomorrow=""
    report_string_before=""
    task_today_done_counter=0
    task_today_counter=0

    headings = list()
    counter = 0

    for line in lines:
        if "<script" in line:
            pass
        if "<style>" in line:
            new_lines += [line]
        elif line[0] == "#":
            if(line[1] == ">"):
                headings += [line[:-1]]
            # comments we just pass it
            new_lines += ["<span style=\"color: gray\">"+line[:-1]+"</span>\n"]
        elif line == "\n":
            new_lines += [line]
        else:
            if line[0] == "[" and line[2] == "]" or line[0:3] == "   ":
                # \todo line
                task = re.sub(r'@(\S+)', r'<span style="color: CornflowerBlue">@\1</span>' ,line)
                task = re.sub(r'#(\S+)', r'<span style="color: DarkGreen" class="cm-tag-\1">#\1</span>' ,task)

                if "[x]" in line or "[/]" in line:
                    if line[0] == " ":
                        spacesToAdd=0
                        for i in task.split(" "):
                            if i != "":
                                break
                            spacesToAdd += 1
                        new_lines += [(" "*spacesToAdd)+task[spacesToAdd+0:spacesToAdd+3]+"<del>"+task[spacesToAdd+3:]+"</del>"]
                    else:
                        new_lines += [task[0:3]+"<del>"+task[3:].rstrip()+"</del>"]
                else:
                    new_lines += [task]


                if "@"+today in new_lines[-1]:
                    if "[x]" in new_lines[-1] or "[/]" in new_lines[-1]:
                        task_today_done_counter+=1
                        report_string_today += new_lines[-1].lstrip().rstrip()\
                            .replace("cm-tag","cm-tag-disabled")\
                            .replace("color: DarkGreen","color: unset")\
                            .replace("color: CornflowerBlue", "color: unset")\
                            + getNextTask(counter, lines)\
                            + getCurrentProject(counter, lines)\
                            + "\n"

                        # Vou verificar que temos sub-tarefas em baixo
                        if((lin := check_sub_tasks(lines, counter)) != ""):
                            report_string_today += lin.rstrip() + "\n";
                    else:
                        report_string_today += new_lines[-1].lstrip().rstrip()\
                            + getNextTask(counter, lines) \
                            + getCurrentProject(counter, lines) \
                            + "\n"
                        if((lin := check_sub_tasks(lines, counter)) != ""):
                            report_string_today += lin.rstrip() + "\n";
                    task_today_counter+=1
                elif "@"+tomorrow in new_lines[-1]:
                    report_string_tomorrow += new_lines[-1].lstrip().rstrip()\
                        + getNextTask(counter, lines)\
                        + getCurrentProject(counter, lines)\
                        + "\n"
                    if((lin := check_sub_tasks(lines, counter)) != ""):
                            report_string_tomorrow += lin.rstrip() + "\n";
                elif "@"+beforeToday in new_lines[-1]:
                    if (not "[x]" in new_lines[-1]) and (not "[/]" in new_lines[-1]):
                        report_string_before += new_lines[-1].lstrip().rstrip()\
                            + getNextTask(counter, lines)\
                            + getCurrentProject(counter, lines)\
                            + "\n"
                        if((lin := check_sub_tasks(lines, counter)) != ""):
                            report_string_before += lin.rstrip() + "\n";
        counter+=1
    report_string="<div class=\"container\"><div class=\"report\" style=\"display: inline-block; background-color: antiquewhite;border: 1.5px solid gray;padding: 10px;border-radius: 5px;\"><span style=\"color: gray\"># REPORT ({})</span>\n"\
        .format(datetime.now().strftime("%d/%m/%Y"))
    if(report_string_before != ""):
        # DUE BEFORE
        if PORTUGUESE_LANG:
            report_string+="<span style=\"color: gray\"># Tarefas a serem feitas até ontem</span>\n"
        else: report_string+="<span style=\"color: gray\"># Tasks due yesterday</span>\n"
        report_string+=report_string_before+"\n"
    if(report_string_today != ""):
        # DUE TODAY
        if PORTUGUESE_LANG:
            report_string+="<span style=\"color: gray\"># Tarefas a serem feitas até hoje ({}/{})</span>\n".format(task_today_done_counter,task_today_counter)
        else: report_string+="<span style=\"color: gray\"># Tasks due today ({}/{})</span>\n".format(task_today_done_counter,task_today_counter)
        report_string+=report_string_today+"\n"
    if(report_string_tomorrow != ""):
        # DUE TOMORROW
        if PORTUGUESE_LANG:
            report_string+="<span style=\"color: gray\"># Tarefas a serem feitas até amanha</span>\n"
        else: report_string+="<span style=\"color: gray\"># Tasks due tomorrow</span>\n"
        report_string+=report_string_tomorrow

    if report_string_before=="" and report_string_today=="" and report_string_tomorrow=="":
        # adds an SVG icon
        report_string+="<div class=\"noTasks\" style=\"text-align: center; margin-top: 25px;\"><svg style=\"\" xmlns=\"http://www.w3.org/2000/svg\" width=\"50\" height=\"50\" fill=\"currentColor\" class=\"bi bi-cup-hot\" viewBox=\"0 0 16 16\"><path fill-rule=\"evenodd\" d=\"M.5 6a.5.5 0 0 0-.488.608l1.652 7.434A2.5 2.5 0 0 0 4.104 16h5.792a2.5 2.5 0 0 0 2.44-1.958l.131-.59a3 3 0 0 0 1.3-5.854l.221-.99A.5.5 0 0 0 13.5 6zM13 12.5a2 2 0 0 1-.316-.025l.867-3.898A2.001 2.001 0 0 1 13 12.5M2.64 13.825 1.123 7h11.754l-1.517 6.825A1.5 1.5 0 0 1 9.896 15H4.104a1.5 1.5 0 0 1-1.464-1.175\"/><path d=\"m4.4.8-.003.004-.014.019a4 4 0 0 0-.204.31 2 2 0 0 0-.141.267c-.026.06-.034.092-.037.103v.004a.6.6 0 0 0 .091.248c.075.133.178.272.308.445l.01.012c.118.158.26.347.37.543.112.2.22.455.22.745 0 .188-.065.368-.119.494a3 3 0 0 1-.202.388 5 5 0 0 1-.253.382l-.018.025-.005.008-.002.002A.5.5 0 0 1 3.6 4.2l.003-.004.014-.019a4 4 0 0 0 .204-.31 2 2 0 0 0 .141-.267c.026-.06.034-.092.037-.103a.6.6 0 0 0-.09-.252A4 4 0 0 0 3.6 2.8l-.01-.012a5 5 0 0 1-.37-.543A1.53 1.53 0 0 1 3 1.5c0-.188.065-.368.119-.494.059-.138.134-.274.202-.388a6 6 0 0 1 .253-.382l.025-.035A.5.5 0 0 1 4.4.8m3 0-.003.004-.014.019a4 4 0 0 0-.204.31 2 2 0 0 0-.141.267c-.026.06-.034.092-.037.103v.004a.6.6 0 0 0 .091.248c.075.133.178.272.308.445l.01.012c.118.158.26.347.37.543.112.2.22.455.22.745 0 .188-.065.368-.119.494a3 3 0 0 1-.202.388 5 5 0 0 1-.253.382l-.018.025-.005.008-.002.002A.5.5 0 0 1 6.6 4.2l.003-.004.014-.019a4 4 0 0 0 .204-.31 2 2 0 0 0 .141-.267c.026-.06.034-.092.037-.103a.6.6 0 0 0-.09-.252A4 4 0 0 0 6.6 2.8l-.01-.012a5 5 0 0 1-.37-.543A1.53 1.53 0 0 1 6 1.5c0-.188.065-.368.119-.494.059-.138.134-.274.202-.388a6 6 0 0 1 .253-.382l.025-.035A.5.5 0 0 1 7.4.8m3 0-.003.004-.014.019a4 4 0 0 0-.204.31 2 2 0 0 0-.141.267c-.026.06-.034.092-.037.103v.004a.6.6 0 0 0 .091.248c.075.133.178.272.308.445l.01.012c.118.158.26.347.37.543.112.2.22.455.22.745 0 .188-.065.368-.119.494a3 3 0 0 1-.202.388 5 5 0 0 1-.252.382l-.019.025-.005.008-.002.002A.5.5 0 0 1 9.6 4.2l.003-.004.014-.019a4 4 0 0 0 .204-.31 2 2 0 0 0 .141-.267c.026-.06.034-.092.037-.103a.6.6 0 0 0-.09-.252A4 4 0 0 0 9.6 2.8l-.01-.012a5 5 0 0 1-.37-.543A1.53 1.53 0 0 1 9 1.5c0-.188.065-.368.119-.494.059-.138.134-.274.202-.388a6 6 0 0 1 .253-.382l.025-.035A.5.5 0 0 1 10.4.8\"/></svg><p>{}</p></div>".format('Nada para fazer' if PORTUGUESE_LANG else 'Nothing to do')
    report_string+="</div></div>\n"

    report_string+="<aside class=\"outline\"><span>Outline</span><a href=\"#\" style=\"float: right;\" class=\"btn\"><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" style=\"position: relative; top: 2px;\" fill=\"currentColor\" class=\"bi bi-arrow-up\" viewBox=\"0 0 16 16\"><path fill-rule=\"evenodd\" d=\"M8 15a.5.5 0 0 0 .5-.5V2.707l3.146 3.147a.5.5 0 0 0 .708-.708l-4-4a.5.5 0 0 0-.708 0l-4 4a.5.5 0 1 0 .708.708L7.5 2.707V14.5a.5.5 0 0 0 .5.5\"/></svg></a><ol>"
    nested=False
    for heading in headings:
        if len(heading) >= 2 and heading[2] == ">":
            if not nested:
                report_string += "<ol>"
                nested=True
            report_string += "<li><a role=\"button\" onclick=\"scrollHere('{}')\">{}</a></li>".format(heading, heading[3:].replace(" ",""))
        else:
            if nested:
                nested=False
                report_string += "</ol>"
            report_string += "<li><a role=\"button\" onclick=\"scrollHere('{}')\">{}</a></li>".format(heading, heading[2:].replace(" ",""))
    report_string+="</ol></aside>"

    return [report_string]


# ------------------------------------------------------------------------------
#  ROUTES 
# ------------------------------------------------------------------------------

@app.route("/")
@auth.login_required
def main_route():
    scroll = 0
    if "scroll" in request.args:
        scroll = request.args['scroll']
    # Get git commit hash
    out = ""
    if(ENABLE_GIT and os.path.exists(FILE_PATH+"/.git")):
        result = subprocess.run(["git -C "+FILE_PATH+" log -1 --pretty=format:\"%h %as\""], 
                                capture_output=True, shell=True)
        out = result.stdout.decode('UTF-8')

    string = ""
    for line in parse_list(lines):
        string += line

    css = parse_css(lines)

    return render_template("main.html", 
                           rev_info=out, 
                           content="".join(lines), 
                           css=css, 
                           report=string, 
                           scroll=scroll)


@app.route("/submit", methods=['POST'])
@auth.login_required
def submit():
    scroll = request.form['scrollPos']
    search = request.form["content"]

    if SANITIZE_JS: 
        search = sanitize_html(search)
        search = html.unescape(search) # nh3 does not offer the option of not escaping ">"
    
    search = search.split("\n")
    new_list = list()
    for line in search:
        new_list += [line+"\n"]
    global lines
    if search[-1] == "":
        new_list.pop()

    if len(new_list) > FILE_MAX_LINES:
        return "Size of the file is too big, please change the FILE_MAX_LINES value", 500

    write_file = open(FILE_PATH+"/"+FILE_NAME, mode="w")
    write_file.writelines(new_list)
    write_file.close()

    lines = new_list
    return redirect(url_for("main_route", scroll=scroll))


@app.route("/cleanup", methods=['get'])
def do_cleanup():
    code = request.args.get('code')
    if(code==DAILY_CLEANUP_TRIGGER_CODE):
        do_backup()
        do_task_day_cleanup(lines)
        return "OK", 200
    return "Nop", 401


@app.route("/robots.txt")
def robots():
    return send_from_directory('static', "robots.txt")


@app.route("/commit")
@auth.login_required
def commit():
    do_backup()
    return redirect(url_for("main_route"))
