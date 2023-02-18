from odoo import models, fields, api, _


class LBSDashboardTemplate(models.Model):
    _name = 'lbs.dashboard_template'
    _description = 'Dashboard Template'

    name = fields.Char()
    gridstack_config = fields.Char()
    ks_item_count = fields.Integer()
    ks_template_type = fields.Selection([('ks_default', 'Predefined'), ('ks_custom', 'Custom')],
                                        string="Template Format")
    ks_dashboard_item_ids = fields.One2many('lbs.dashboard_items', 'dashboard_board_template_id',
                                            string="Template Type")
    dashboard_board_id = fields.Many2one('lbs.dashboard', string="Dashboard", help="""
        Items Configuration and their position in the dashboard will be copied from the selected dashboard 
        and will be saved as template.
    """)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if val.get('ks_template_type', False) and val.get('dashboard_board_id', False):
                dashboard_id = self.env['lbs.dashboard'].browse(val.get('dashboard_board_id'))
                val['gridstack_config'] = dashboard_id.gridstack_config
                val['ks_item_count'] = len(dashboard_id.dashboard_items_ids)
                val['ks_dashboard_item_ids'] = [(4, x.copy({'dashboard_lbs_board_id': False}).id) for x in
                                                dashboard_id.dashboard_items_ids]
        recs = super(LBSDashboardTemplate, self).create(vals_list)
        return recs

    def write(self, val):
        if val.get('dashboard_board_id', False):
            dashboard_id = self.env['lbs.dashboard'].browse(val.get('dashboard_board_id'))
            val['gridstack_config'] = dashboard_id.gridstack_config
            val['ks_item_count'] = len(dashboard_id.dashboard_items_ids)
            val['ks_dashboard_item_ids'] = [(6, 0,
                                             [x.copy({'dashboard_lbs_board_id': False}).id for x in
                                              dashboard_id.dashboard_items_ids])]
        recs = super(LBSDashboardTemplate, self).write(val)
        return recs
