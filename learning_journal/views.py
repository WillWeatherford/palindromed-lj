# coding=utf-8
from __future__ import unicode_literals

from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config
from sqlalchemy.exc import DBAPIError, IntegrityError

from .models import (
    DBSession,
    Post,
    User,
    Comment
)
from pyramid.security import remember, forget
from .user import UserService
from .post_form import ModifyPostForm, UserForm, CommentForm


@view_config(route_name='home', renderer='templates/list.jinja2',
             permission='read')
def list_view(request):
    try:
        posts = DBSession.query(Post).all()
    except DBAPIError:
        return Response("error!", content_type='text/plain', status_int=500)
    return {'posts': posts}


@view_config(route_name='detail', renderer='templates/detail.jinja2',
             permission='read')
def detail_view(request):
    form = CommentForm(request.POST)
    try:
        post = DBSession.query(Post).get(request.matchdict['post_id'])
    except DBAPIError:
        return Response("error!", content_type='text/plain', status_int=500)
    return {'post': post, 'form': form}


@view_config(route_name='comment', request_method='POST')
def add_comment(request):
    comment = Comment()
    try:
        user = request.authenticated_userid
        user = DBSession.query(User).filter(User.username == user).first()
        path = request.POST.path.split('/')
        post = path[-1]
        post = DBSession.query(Post).filter(Post.id == post).first()
    except DBAPIError:
        return "FAIL"

    # comment = Comment()
    # form = CommentForm(request.POST)
    if request.method == 'POST' and form.validate():
        form.populate_obj(comment)
        DBSession.add(comment)
        comment.thoughts = form.thoughts.data
        comment.author = user
        comment.parent = post
        post.comments.append(comment)
        request.user.my_comments.append(comment)
        DBSession.add_all([comment, user, post])
        DBSession.flush()
        return HTTPFound(location=request.route_url('home'))
    return {'form': form}
    # pass



@view_config(route_name='edit', request_method='POST', check_csrf=True)
@view_config(route_name='edit', renderer='templates/edit.jinja2',
             permission='change')
def edit_view(request):
    post_to_edit = DBSession.query(Post).filter(Post.id == int(request.matchdict['post_id'])).first()
    form = ModifyPostForm(request.POST, post_to_edit)
    if not post_to_edit:
        form.errors.setdefault('error', []).append('That post does not exist!')
    elif request.method == 'POST' and form.validate():
        try:
            form.populate_obj(post_to_edit)
            DBSession.add(post_to_edit)
            DBSession.flush()
            re_route = request.route_url('detail', post_id=post_to_edit.id)
            return HTTPFound(location=re_route)
        except DBAPIError:
            form.errors.setdefault('error', []).append('Title must be unique!')
        # return Response("error!", content_type='text/plain', status_int=500)
    return {'form': form, 'use_case': 'Edit'}


@view_config(route_name='add_entry', request_method='POST', check_csrf=True)
@view_config(route_name='add_entry', renderer="templates/edit.jinja2",
             permission='change')
def create_view(request):
    form = ModifyPostForm(request.POST)
    if request.method == 'POST' and form.validate():
        new_post = Post(title=form.title.data, text=form.text.data)
        try:
            DBSession.add(new_post)
            DBSession.flush()
            detail_id = new_post.id
            re_route = request.route_url('detail', post_id=detail_id)
            return HTTPFound(location=re_route)
        except IntegrityError:
            form.errors.setdefault('error', []).append('Title must be unique!')
    return {'form': form, 'use_case': 'Create'}


@view_config(route_name='login', request_method='POST', check_csrf=True)
@view_config(route_name='login', renderer='templates/login.jinja2')
def login_view(request):
    form = UserForm(request.POST)
    if request.method == 'POST' and form.validate():
        if form.username.data:
            user = UserService.by_name(form.username.data)
            if user and user.verify_password(form.password.data):
                headers = remember(request, form.username.data)
                return HTTPFound(location=request.route_url('home'), headers=headers)
            else:
                headers = forget(request)
                return {'form': form, 'error': "Unable to validate login. Try again."}
    return {'form': form}


@view_config(route_name='logout')
def log_out(request):
    headers = forget(request)
    return HTTPFound(location=request.route_url('home'), headers=headers)


@view_config(route_name='register', request_method='POST', check_csrf=True)
@view_config(route_name='register', renderer='templates/register.jinja2')
def register(request):
    form = UserForm(request.POST)
    if request.method == 'POST' and form.validate():
        new_user = User()
        new_user.username = form.username.data
        new_user.set_password(form.password.data.encode('utf8'))
        DBSession.add(new_user)
        headers = remember(request, form.username.data)
        return HTTPFound(location=request.route_url('home'), headers=headers)

    return {'form': form}


conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_learning-journal_db" script
    to initialize your database tables.  Check your virtual
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""
