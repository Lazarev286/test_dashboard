from odoo import models, fields, api, _


class LBSDashboardChild(models.Model):
    _name = 'lbs.dashboard_child'
    _description = 'Child Dashboard'

    name = fields.Char()
    dashboard_ninja_id = fields.Many2one("lbs.dashboard", string="Select Dashboard")
    gridstack_config = fields.Char('Item Configurations')
    # ks_board_active_user_ids = fields.Many2many('res.users')
    is_active = fields.Boolean("Is Selected")
    dashboard_menu_name = fields.Char(string="Menu Name", related='dashboard_ninja_id.dashboard_menu_name', store=True)
    board_type = fields.Selection([('default', 'Default'), ('child', 'Child')])
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

