from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class LBSDashboardTemplate(models.Model):
    _name = 'lbs.dashboard_defined_filters'
    _description = 'Dashboard Defined Filters'

    name = fields.Char("Filter Label")
    dashboard_board_id = fields.Many2one('lbs.dashboard', string="Dashboard")
    model_id = fields.Many2one('ir.model', string='Model',
                                  domain="[('access_ids','!=',False),('transient','=',False),"
                                         "('model','not ilike','base_import%'),('model','not ilike','ir.%'),"
                                         "('model','not ilike','web_editor.%'),('model','not ilike','web_tour.%'),"
                                         "('model','!=','mail.thread'),('model','not ilike','ks_dash%'), ('model','not ilike','ks_to%')]",
                                  help="Data source to fetch and read the data for the creation of dashboard items. ")
    lbs_domain = fields.Char(string="Domain", help="Define conditions for filter. ")
    domain_temp = fields.Char(string="Domain Substitute")
    lbs_model_name = fields.Char(related='model_id.model', string="Model Name")
    display_type = fields.Selection([
        ('line_section', "Section")], default=False, help="Technical field for UX purpose.")
    sequence = fields.Integer(default=10,
                              help="Gives the sequence order when displaying a list of payment terms lines.")
    lbs_is_active = fields.Boolean(string="Active")

    @api.onchange('lbs_domain')
    def ks_domain_onchange(self):
        for rec in self:
            if rec.model_id:
                try:
                    lbs_domain = rec.lbs_domain
                    if lbs_domain and "%UID" in lbs_domain:
                        lbs_domain = lbs_domain.replace('"%UID"', str(self.env.user.id))
                    if lbs_domain and "%MYCOMPANY" in lbs_domain:
                        lbs_domain = lbs_domain.replace('"%MYCOMPANY"', str(self.env.company.id))
                    self.env[rec.model_id.model].search_count(safe_eval(lbs_domain))
                except Exception as e:
                    raise ValidationError(_("Something went wrong . Possibly it is due to wrong input type for domain"))

    @api.constrains('lbs_domain', 'model_id')
    def ks_domain_check(self):
        for rec in self:
            if rec.model_id and not rec.lbs_domain:
                raise ValidationError(_("Domain can not be empty"))



class LBSDashboardCustomTemplate(models.Model):
    _name = 'lbs.dashboard_custom_filters'
    _description = 'Dashboard Custom Filters'

    name = fields.Char("Filter Label")
    dashboard_board_id = fields.Many2one('lbs.dashboard', string="Dashboard")
    model_id = fields.Many2one('ir.model', string='Model',
                                  domain="[('access_ids','!=',False),('transient','=',False),"
                                         "('model','not ilike','base_import%'),('model','not ilike','ir.%'),"
                                         "('model','not ilike','web_editor.%'),('model','not ilike','web_tour.%'),"
                                         "('model','!=','mail.thread'),('model','not ilike','ks_dash%'), ('model','not ilike','ks_to%')]",
                                  help="Data source to fetch and read the data for the creation of dashboard items. ")
    lbs_domain_field_id = fields.Many2one('ir.model.fields',
                                         domain="[('model_id','=',model_id),"
                                                "('name','!=','id'),('store','=',True),"
                                                "('ttype', 'in', ['boolean', 'char', "
                                                "'date', 'datetime', 'float', 'integer', 'html', 'many2many', "
                                                "'many2one', 'monetary', 'one2many', 'text', 'selection'])]",
                                         string="Domain Field")
