# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.http import request


class TransitOpsHome(Home):
    """
    Extends the default Odoo login controller to:
    1. Pass security groups to the login template for the role dropdown.
    2. After login, validate the selected role and store it in the session.
    """

    @http.route('/web/login', type='http', auth='none', methods=['GET', 'POST'], sitemap=False)
    def web_login(self, redirect=None, **kw):
        """Override login to inject TransitOps groups into QWeb context."""
        response = super().web_login(redirect=redirect, **kw)

        # On GET (showing the form), inject available roles into qcontext
        if request.httprequest.method == 'GET':
            if hasattr(response, 'qcontext'):
                response.qcontext['transitops_roles'] = [
                    ('group_fleet_manager', 'Fleet Manager'),
                    ('group_dispatcher', 'Dispatcher'),
                    ('group_safety_officer', 'Safety Officer'),
                    ('group_financial_analyst', 'Financial Analyst'),
                ]
                # Preserve selected role across failed logins
                response.qcontext['selected_role'] = kw.get('transitops_role', '')

        # On POST (after successful login), store selected role in session
        if request.httprequest.method == 'POST' and request.session.uid:
            selected_role = kw.get('transitops_role', '')
            if selected_role:
                request.session['transitops_role'] = selected_role

        return response
