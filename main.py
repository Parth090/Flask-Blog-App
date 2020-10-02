from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime
from flask_mail import Mail
import os
from werkzeug.utils import secure_filename
import math

with open("config.json", "r") as c:
    params = json.load(c)["params"]

app = Flask(__name__)

app.config["SECRET_KEY"] = "Your_secret_string"

app.config["UPLOAD_FILE"] = params["upload_location"]
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT="465",
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params["gmail-user"],
    MAIL_PASSWORD=params["gmail-password"],
)

mail = Mail(app)

if params["local_server"]:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["local_uri"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["prod_uri"]

db = SQLAlchemy(app)


class Contacts(db.Model):
    """
    sno,name,email,phone_num,msg,date
    """

    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(25), nullable=False)
    phone_num = db.Column(db.Integer(), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)


class Posts(db.Model):
    """
    sno,title,slug,content,date
    """

    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(25), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=False)
    img_file = db.Column(db.String(12), nullable=False)
    tagline = db.Column(db.String(30), nullable=False)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts) / int(params["noof_post"]))
    page = request.args.get("page")
    if not str(page).isnumeric():
        page = 1
    # PAGINATION
    page = int(page)
    posts = posts[
        (page - 1) * int(params["noof_post"]) : (page - 1) * int(params["noof_post"])
        + int(params["noof_post"])
    ]
    if page == 1:
        prevpage = "#"
        nextpage = "/?page=" + str(page + 1)
    elif page == last:
        nextpage = "#"
        prevpage = "/?page=" + str(page - 1)
    else:
        nextpage = "/?page=" + str(page + 1)
        prevpage = "/?page=" + str(page - 1)

    return render_template(
        "index.html", params=params, posts=posts, prevpage=prevpage, nextpage=nextpage
    )


@app.route("/about")
def about():
    return render_template("about.html", params=params)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" in session and session["user"] == params["admin_user"]:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        # REDIRECT to admin page
        username = request.form.get("uname")
        password = request.form.get("psw")
        if username == params["admin_user"] and password == params["admin_password"]:
            session["user"] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)

    return render_template("login.html", params=params)


@app.route("/uploader", methods=["GET", "POST"])
def uploader():
    if "user" in session and session["user"] == params["admin_user"]:
        if request.method == "POST":
            f = request.files["file1"]
            f.save(os.path.join(app.config["UPLOAD_FILE"], secure_filename(f.filename)))

    return redirect("/dashboard")


@app.route("/delete/<string:sno>", methods=["GET", "POST"])
def delete(sno):
    if "user" in session and session["user"] == params["admin_user"]:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/logout")
def logout():
    if "user" in session and session["user"] == params["admin_user"]:
        del session["user"]
        return redirect("/dashboard")


@app.route("/edit/<string:sno>", methods=["GET", "POST"])
def edit(sno):

    if "user" in session and session["user"] == params["admin_user"]:
        if request.method == "POST":
            box_title = request.form.get("title")
            box_slug = request.form.get("slug")
            box_content = request.form.get("content")
            box_imgfile = request.form.get("imgfile")
            box_tagline = request.form.get("tline")
            date = datetime.now()

            if sno == "0":
                post = Posts(
                    title=box_title,
                    slug=box_slug,
                    content=box_content,
                    img_file=box_imgfile,
                    tagline=box_tagline,
                    date=date,
                )
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = box_slug
                post.content = box_content
                post.img_file = box_imgfile
                post.tagline = box_tagline
                db.session.commit()
                return redirect("/edit/" + sno)

        post = Posts.query.filter_by(sno=sno).first()
        return render_template("edit.html", params=params, sno=sno, post=post)


@app.route("/post/<string:post_slug>", methods=["GET"])
def post_func(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template("post.html",post=post)


@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":
        """Add entry to database """

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("msg")

        entry = Contacts(
            name=name, email=email, phone_num=phone, msg=message, date=datetime.now()
        )

        db.session.add(entry)
        db.session.commit()
        mail.send_message(
            "New message from " + name,
            sender=email,
            recipients=[params["gmail-user"]],
            body=message + "\n" + phone,
        )
    return render_template("/contact.html", params=params)



app.run(debug=True)
