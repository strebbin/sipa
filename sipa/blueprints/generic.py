#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from flask import render_template, request, redirect, \
    url_for, flash, session
from flask.blueprints import Blueprint
from flask.ext.babel import gettext
from flask.ext.login import current_user, login_user, logout_user, \
    login_required
from sqlalchemy.exc import OperationalError
from ldap import SERVER_DOWN

from model import division_from_name, user_from_ip
from model.default import BaseUser

from sipa import logger, http_logger, app
from sipa.forms import flash_formerrors, LoginForm
from sipa.utils import current_user_name
from sipa.utils.exceptions import UserNotFound, PasswordInvalid

bp_generic = Blueprint('generic', __name__)


@bp_generic.before_app_request
def log_request():
    http_logger.debug('Incoming request: %s %s', request.method, request.path,
                      extra={'tags': {'user': current_user_name(),
                                      'ip': request.remote_addr}})


@bp_generic.app_errorhandler(401)
@bp_generic.app_errorhandler(403)
@bp_generic.app_errorhandler(404)
def error_handler_redirection(e):
    """Handles errors by flashing an according message and redirecting to /
    :param e: The error
    :return: A flask response, in this case `redirect(url_for('.index'))`
    """
    if e.code in (404,):
        flash(gettext(u"Seite nicht gefunden!"), "warning")
    elif e.code in (401, 403):
        flash(gettext(
            u"Du hast nicht die notwendigen Rechte um die Seite zu sehen!"),
            "warning")
    else:
        flash(gettext(u"Es ist ein Fehler aufgetreten!"), "error")
    return redirect(url_for('generic.index'))


@bp_generic.app_errorhandler(OperationalError)
def exceptionhandler_sql(ex):
    """Handles global MySQL errors (server down).
    """
    flash(gettext("Verbindung zum SQL-Server konnte nicht hergestellt werden!"),
          "error")
    logger.critical('Unable to connect to MySQL server',
                    extra={'data': {'exception_args': ex.args}})
    return redirect(url_for('generic.index'))


@bp_generic.app_errorhandler(SERVER_DOWN)
def exceptionhandler_ldap(ex):
    """Handles global LDAP SERVER_DOWN exceptions.
    The session must be reset, because if the user is logged in and the server
    fails during his session, it would cause a redirect loop.
    This also resets the language choice, btw.

    The alternative would be a try-except catch block in load_user, but login
    also needs a handler.
    """
    session.clear()
    flash(gettext(
        "Verbindung zum LDAP-Server konnte nicht hergestellt werden!"),
        "error"
    )
    logger.critical(
        'Unable to connect to LDAP server %s:%s',
        app.config['LDAP_HOST'], app.config['LDAP_PORT'],
        extra={'data': {'ldap_base_dn': app.config['LDAP_SEARCH_BASE'],
                        'exception_args': ex.args}}
    )
    return redirect(url_for('generic.index'))


@bp_generic.route("/language/<string:lang>")
def set_language(lang='de'):
    """Set the session language via URL
    """
    session['locale'] = lang
    return redirect(request.referrer)


@bp_generic.route('/index.php')
@bp_generic.route('/')
def index():
    return redirect(url_for('news.display'))


@bp_generic.route("/login", methods=['GET', 'POST'])
def login():
    """Login page for users
    """
    form = LoginForm()

    if form.validate_on_submit():
        division_name = form.division.data
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        User = division_from_name(division_name).user_class

        try:
            user = User.authenticate(username, password)
        except (UserNotFound, PasswordInvalid):
            flash(gettext(u"Anmeldedaten fehlerhaft!"), "error")
        else:
            if isinstance(user, User):
                session['division'] = division_name
                login_user(user, remember=remember)
                logger.info('Authentication successful')
                flash(gettext(u"Anmeldung erfolgreich!"), "success")
    elif form.is_submitted():
        flash_formerrors(form)

    if current_user.is_authenticated():
        return redirect(url_for('usersuite.usersuite'))

    return render_template('login.html', form=form)


@bp_generic.route("/logout")
@login_required
def logout():
    logger.info('Logging out')
    logout_user()
    return redirect(url_for('.index'))


@bp_generic.route("/usertraffic")
def usertraffic():
    """For anonymous users with a valid IP
    """
    ip_user = user_from_ip(request.remote_addr)

    if isinstance(ip_user, BaseUser):
        if current_user.is_authenticated():
            if current_user != ip_user:
                flash(gettext(u"Ein anderer Nutzer als der für diesen Anschluss"
                              u" Eingetragene ist angemeldet!"), "warning")
                flash(gettext("Hier werden die Trafficdaten "
                              "dieses Anschlusses angezeigt"), "info")

        return render_template("usertraffic.html", usertraffic=(
            ip_user.get_traffic_data()))
    else:
        flash(gettext(u"Deine IP gehört nicht zum Wohnheim!"), "error")

        if current_user.is_authenticated():
            flash(gettext(u"Da du angemeldet bist, kannst du deinen Traffic "
                          u"hier in der Usersuite einsehen."), "info")
            return redirect(url_for('usersuite.usersuite'))
        else:
            flash(gettext(u"Um deinen Traffic von außerhalb einsehen zu können,"
                          u" musst du dich anmelden."), "info")
            return redirect(url_for('.login'))
