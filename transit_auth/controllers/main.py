# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


GROUP_MAP = {
    'fleet_manager': 'transit_base.group_fleet_manager',
    'driver': 'transit_base.group_driver',
    'safety_officer': 'transit_base.group_safety_officer',
    'financial_analyst': 'transit_base.group_financial_analyst',
}


class TransitAuthController(Home):

    @http.route('/web/login', type='http', auth='none', methods=['GET', 'POST'], csrf=True, sitemap=False)
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        if request.httprequest.method == 'POST' and request.session.uid:
            role = request.httprequest.form.get('role_selected')
            if role and role in GROUP_MAP:
                uid = request.session.uid
                target_group = request.env.ref(GROUP_MAP[role])

                # Collect all transit group IDs
                all_group_ids = []
                for xmlid in GROUP_MAP.values():
                    g = request.env.ref(xmlid, raise_if_not_found=False)
                    if g:
                        all_group_ids.append(g.id)

                # Remove all transit groups, add only the selected one via ORM on res.groups
                for gid in all_group_ids:
                    if gid != target_group.id:
                        grp = request.env['res.groups'].sudo().browse(gid)
                        grp.write({'users': [(3, uid)]})

                # Add the target group
                target_group.sudo().write({'users': [(4, uid)]})

                # Rotate session
                request.session.should_rotate = True

                return request.redirect('/odoo')

        return response
