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
            selected_role = kw.get('transitops_role', '') or request.params.get('transitops_role', '')
            if selected_role:
                request.session['transitops_role'] = selected_role
                
                # Dynamically attach the selected role (group) to the user
                try:
                    uid = request.session.uid
                    # Use sudo to allow changing groups during login session establishment
                    env = request.env(user=uid).sudo()
                    user = env['res.users'].browse(uid)
                    
                    role_mapping = {
                        'group_fleet_manager': 'transit_base.group_fleet_manager',
                        'group_dispatcher': 'transit_base.group_dispatcher',
                        'group_safety_officer': 'transit_base.group_safety_officer',
                        'group_financial_analyst': 'transit_base.group_financial_analyst',
                        'group_driver': 'transit_base.group_driver',
                    }
                    
                    if selected_role in role_mapping:
                        # Gather all group IDs to remove
                        all_group_ids = []
                        target_group = None
                        
                        for role_key, xml_id in role_mapping.items():
                            group = env.ref(xml_id, raise_if_not_found=False)
                            if group:
                                all_group_ids.append(group.id)
                                if role_key == selected_role:
                                    target_group = group
                        
                        if target_group:
                            # 3: unlink the old groups, 4: link the new group
                            commands = [(3, gid) for gid in all_group_ids]
                            commands.append((4, target_group.id))
                            user.write({'groups_id': commands})
                except Exception as e:
                    # Do not block authentication if group mapping fails
                    pass

        return response
