# -*- coding: utf-8 -*-

from odoo import api, fields, models


class LBSCreateDashboardWizard(models.TransientModel):
    _name = 'lbs.dashboard_wizard'
    _description = 'Dashboard Creation Wizard'

    name = fields.Char(string="Dashboard Name", required=True)
    ks_menu_name = fields.Char(string="Menu Name", required=True)
    ks_top_menu_id = fields.Many2one('ir.ui.menu',
                                     domain="[('parent_id','=',False)]",
                                     string="Show Under Menu", required=True,
                                     default=lambda self: self.env['ir.ui.menu'].search(
                                         [('name', '=', 'My Dashboard')])[0])
    ks_sequence = fields.Integer(string="Sequence")
    ks_template = fields.Many2one('lbs.dashboard_template',
                                  default=lambda self: self.env.ref('lbs_dashboard.ks_blank',
                                                                    False),
                                  string="Dashboard Template")

    context = {}

    def CreateDashBoard(self):
        '''this function returns acion id of ks.dashboard.wizard'''
        action = self.env['ir.actions.act_window']._for_xml_id(
            'lbs_dashboard.ks_create_dashboard_wizard')
        return action

    def ks_create_record(self):
        '''this function creats record of lbs_dashboard.board and return dashboard action_id'''
        ks_create_record = self.env['lbs.dashboard'].create({
            'name': self.name,
            'dashboard_menu_name': self.ks_menu_name,
            'dashboard_menu_sequence': self.ks_sequence,
            'dashboard_default_template': self.ks_template.id,
            'dashboard_top_menu_id': self.ks_top_menu_id.id,
        })
        context = {'ks_reload_menu': True, 'ks_menu_id': ks_create_record.dashboard_menu_id.id}
        return {
            'type': 'ir.actions.client',
            'name': "Dashboard Ninja",
            'res_model': 'lbs.dashboard',
            'params': {'ks_dashboard_id': ks_create_record.id},
            'tag': 'lbs_dashboard',
            'context': self.with_context(context)._context
        }
