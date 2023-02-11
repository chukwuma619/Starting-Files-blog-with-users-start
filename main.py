from datetime import date
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_admin import Admin
from flask_bootstrap import Bootstrap4
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, AnonymousUserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_gravatar import Gravatar
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
bootstrap = Bootstrap4(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# #LOGIN MANAGER
login_manager = LoginManager(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# ADMIN MODEL VIEWS
def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous == True or current_user.id != 1:
            return abort(403, "Unauthorized User")
        else:
            print(current_user.id)
            return function(*args, **kwargs)
    return decorated_function


##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = db.relationship("BlogPost", back_populates="author", uselist=True, lazy=True)
    comments = db.relationship("Comment", back_populates="comment_author", uselist=True, lazy=True)



class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author = db.relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    post_comments = db.relationship("Comment", back_populates="parent_post",  uselist=True, lazy=True)



class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_author = db.relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = db.relationship("BlogPost", back_populates="post_comments")
    text = db.Column(db.String, nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

@app.errorhandler(404)
def page_not_found(error):
    return 'This page does not exist', 404


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == "POST" and form.validate_on_submit():
        check_user_exist = db.session.execute(
            db.select(User).filter_by(email=request.form["email"])).scalar_one_or_none()
        if not check_user_exist:
            new_user = User(name=request.form["name"],
                            email=request.form["email"],
                            password=generate_password_hash(request.form["password"]))
            db.session.add(new_user)
            db.session.commit()
            login_user(
                user=db.session.execute(db.select(User).filter_by(email=request.form["email"])).scalar_one_or_none())
            return redirect(url_for("get_all_posts"))
        else:
            flash("Email Already Exist", "danger")
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(email=request.form["email"])).scalar_one_or_none()
        if user:
            verify_password = check_password_hash(pwhash=user.password,
                                                  password=request.form["password"])
            if verify_password:
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Invalid password", "danger")
        else:
            flash("User does not exist", "danger")
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    comments = db.session.execute(db.select(Comment).filter_by(post_id=requested_post.id)).scalars()
    if comment_form.validate_on_submit() and request.method=="POST":
        if current_user.is_authenticated:
            comment = Comment(text=comment_form.comment.data,
                              author_id=current_user.id,
                              post_id=requested_post.id)
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for("show_post"))
        else:
            flash("You need to login or register to comment", "warning")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, form=comment_form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit() and request.method=="POST":
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            author=current_user.name,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y"),
            author_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit() and request.method=="POST":
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
