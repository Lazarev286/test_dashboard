# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
import datetime
import json
from odoo.addons.lbs_dashboard.common_lib.ks_date_filter_selections import ks_get_date, ks_convert_into_local, \
    ks_convert_into_utc
from odoo.tools.safe_eval import safe_eval
import locale
from dateutil.parser import parse


class LBSDashboardBoard(models.Model):
    _name = 'lbs.dashboard'
    _description = 'Dashboard'

    name = fields.Char(string="Dashboard Name", required=True, size=35)
    dashboard_items_ids = fields.One2many('lbs.dashboard_items', 'dashboard_lbs_board_id',
                                             string='Dashboard Items')
    dashboard_menu_name = fields.Char(string="Menu Name")
    dashboard_top_menu_id = fields.Many2one('ir.ui.menu',
                                               domain="['|',('action','=',False),('parent_id','=',False)]",
                                               string="Show Under Menu",
                                               default=lambda self: self.env['ir.ui.menu'].search(
                                                   [('name', '=', 'My Dashboard')]))
    dashboard_client_action_id = fields.Many2one('ir.actions.client')
    dashboard_menu_id = fields.Many2one('ir.ui.menu')
    dashboard_state = fields.Char()
    dashboard_active = fields.Boolean(string="Active", default=True)
    dashboard_group_access = fields.Many2many('res.groups', string="Group Access")

    # DateFilter Fields
    dashboard_start_date = fields.Datetime(string="Start Date")
    dashboard_end_date = fields.Datetime(string="End Date")
    date_filter_selection = fields.Selection([
        ('l_none', 'All Time'),
        ('l_day', 'Today'),
        ('t_week', 'This Week'),
        ('t_month', 'This Month'),
        ('t_quarter', 'This Quarter'),
        ('t_year', 'This Year'),
        ('n_day', 'Next Day'),
        ('n_week', 'Next Week'),
        ('n_month', 'Next Month'),
        ('n_quarter', 'Next Quarter'),
        ('n_year', 'Next Year'),
        ('ls_day', 'Last Day'),
        ('ls_week', 'Last Week'),
        ('ls_month', 'Last Month'),
        ('ls_quarter', 'Last Quarter'),
        ('ls_year', 'Last Year'),
        ('l_week', 'Last 7 days'),
        ('l_month', 'Last 30 days'),
        ('l_quarter', 'Last 90 days'),
        ('l_year', 'Last 365 days'),
        ('ls_past_until_now', 'Past Till Now'),
        ('ls_pastwithout_now', ' Past Excluding Today'),
        ('n_future_starting_now', 'Future Starting Now'),
        ('n_futurestarting_tomorrow', 'Future Starting Tomorrow'),
        ('l_custom', 'Custom Filter'),
    ], default='l_none', string="Default Date Filter")

    # for setting Global/Indian Format
    data_formatting = fields.Selection([
        ('global', 'Global'),
        ('indian', 'Indian'),
        ('exact', 'Exact')
    ], string='Format')

    gridstack_config = fields.Char('Item Configurations')
    dashboard_default_template = fields.Many2one('lbs.dashboard_template',
                                                    default=lambda self: self.env.ref('lbs_dashboard.ks_blank',
                                                                                      False),
                                                    string="Dashboard Template")

    set_interval = fields.Selection([
        ('15000', '15 Seconds'),
        ('30000', '30 Seconds'),
        ('45000', '45 Seconds'),
        ('60000', '1 minute'),
        ('120000', '2 minute'),
        ('300000', '5 minute'),
        ('600000', '10 minute'),
    ], string="Default Update Interval", help="Update Interval for new items only")
    dashboard_menu_sequence = fields.Integer(string="Menu Sequence", default=10,
                                                help="Smallest sequence give high priority and Highest sequence give "
                                                     "low priority")
    child_dashboard_ids = fields.One2many('lbs.dashboard_child', 'dashboard_ninja_id')
    dashboard_defined_filters_ids = fields.One2many('lbs.dashboard_defined_filters',
                                                       'dashboard_board_id',
                                                       string='Dashboard Predefined Filters')
    dashboard_custom_filters_ids = fields.One2many('lbs.dashboard_custom_filters',
                                                      'dashboard_board_id',
                                                      string='Dashboard Custom Filters')
    multi_layouts = fields.Boolean(string='Enable Multi-Dashboard Layouts',
                                   help='Allow user to have multiple layouts of the same Dashboard')


    @api.constrains('dashboard_start_date', 'dashboard_end_date')
    def ks_date_validation(self):
        for rec in self:
            if rec.dashboard_start_date > rec.dashboard_end_date:
                raise ValidationError(_('Start date must be less than end date'))

    @api.model
    def create(self, vals):
        record = super(LBSDashboardBoard, self).create(vals)
        if 'dashboard_top_menu_id' in vals and 'dashboard_menu_name' in vals:
            action_id = {
                'name': vals['dashboard_menu_name'] + " Action",
                'res_model': 'lbs.dashboard',
                'tag': 'lbs_dashboard',
                'params': {'ks_dashboard_id': record.id},
            }
            record.dashboard_client_action_id = self.env['ir.actions.client'].sudo().create(action_id)

            record.dashboard_menu_id = self.env['ir.ui.menu'].sudo().create({
                'name': vals['dashboard_menu_name'],
                'active': vals.get('dashboard_active', True),
                'parent_id': vals['dashboard_top_menu_id'],
                'action': "ir.actions.client," + str(record.dashboard_client_action_id.id),
                'groups_id': vals.get('dashboard_group_access', False),
                'sequence': vals.get('dashboard_menu_sequence', 10)
            })

        if record.dashboard_default_template and record.dashboard_default_template.ks_item_count:
            gridstack_config = {}
            template_data = json.loads(record.dashboard_default_template.gridstack_config)
            for item_data in template_data:
                if record.dashboard_default_template.ks_template_type == 'ks_custom':
                    dashboard_item = self.env['lbs.dashboard_items'].browse(int(item_data)).copy(
                        {'dashboard_lbs_board_id': record.id})
                    gridstack_config[dashboard_item.id] = template_data[item_data]
                else:
                    dashboard_item = self.env.ref(item_data['item_id']).copy({'dashboard_lbs_board_id': record.id})
                    gridstack_config[dashboard_item.id] = item_data['data']
            record.gridstack_config = json.dumps(gridstack_config)
        return record

    @api.onchange('date_filter_selection')
    def ks_date_filter_selection_onchange(self):
        for rec in self:
            if rec.date_filter_selection and rec.date_filter_selection != 'l_custom':
                rec.dashboard_start_date = False
                rec.dashboard_end_date = False

    def write(self, vals):
        if vals.get('date_filter_selection', False) and vals.get('date_filter_selection') != 'l_custom':
            vals.update({
                'dashboard_start_date': False,
                'dashboard_end_date': False

            })
        record = super(LBSDashboardBoard, self).write(vals)
        for rec in self:
            if 'dashboard_menu_name' in vals:
                if self.env.ref('lbs_dashboard.ks_my_default_dashboard_board') and self.env.ref(
                        'lbs_dashboard.ks_my_default_dashboard_board').sudo().id == rec.id:
                    if self.env.ref('lbs_dashboard.board_menu_root', False):
                        self.env.ref('lbs_dashboard.board_menu_root').sudo().name = vals['dashboard_menu_name']
                else:
                    rec.dashboard_menu_id.sudo().name = vals['dashboard_menu_name']
            if 'dashboard_group_access' in vals:
                if self.env.ref('lbs_dashboard.ks_my_default_dashboard_board').id == rec.id:
                    if self.env.ref('lbs_dashboard.board_menu_root', False):
                        self.env.ref('lbs_dashboard.board_menu_root').groups_id = vals['dashboard_group_access']
                else:
                    rec.dashboard_menu_id.sudo().groups_id = vals['dashboard_group_access']
            if 'dashboard_active' in vals and rec.dashboard_menu_id:
                rec.dashboard_menu_id.sudo().active = vals['dashboard_active']

            if 'dashboard_top_menu_id' in vals:
                rec.dashboard_menu_id.write(
                    {'parent_id': vals['dashboard_top_menu_id']}
                )

            if 'dashboard_menu_sequence' in vals:
                rec.dashboard_menu_id.sudo().sequence = vals['dashboard_menu_sequence']

        return record

    def unlink(self):
        if self.env.ref('lbs_dashboard.ks_my_default_dashboard_board').id in self.ids:
            raise ValidationError(_("Default Dashboard can't be deleted."))
        else:
            for rec in self:
                rec.dashboard_client_action_id.sudo().unlink()
                rec.dashboard_menu_id.sudo().unlink()
                rec.dashboard_items_ids.unlink()
        res = super(LBSDashboardBoard, self).unlink()
        return res

    def ks_get_grid_config(self):
        default_grid_id = self.env['lbs.dashboard_child'].search(
            [['id', 'in', self.child_dashboard_ids.ids], ['company_id', '=', self.env.company.id],
             ['board_type', '=', 'default']])

        if not default_grid_id:
            default_grid_id = self.env['lbs.dashboard_child'].create({
                "gridstack_config": self.gridstack_config,
                "dashboard_ninja_id": self.id,
                "name": "Default Board Layout",
                "company_id": self.env.company.id,
                "board_type": "default",
            })

        return default_grid_id

    @api.model
    def ks_fetch_dashboard_data(self, ks_dashboard_id, ks_item_domain=False):
        """
        Return Dictionary of Dashboard Data.
        :param ks_dashboard_id: Integer
        :param ks_item_domain: List[List]
        :return: dict
        """

        ks_dn_active_ids = []
        if self._context.get('ks_dn_active_ids'):
            ks_dn_active_ids = self._context.get('ks_dn_active_ids')

        ks_dn_active_ids.append(ks_dashboard_id)
        self = self.with_context(
            ks_dn_active_ids=ks_dn_active_ids,
        )

        has_group_ks_dashboard_manager = self.env.user.has_group('lbs_dashboard.ks_dashboard_ninja_group_manager')
        ks_dashboard_rec = self.browse(ks_dashboard_id)
        dashboard_data = {
            'name': ks_dashboard_rec.name,
            'multi_layouts': ks_dashboard_rec.multi_layouts,
            'ks_company_id': self.env.company.id,
            'ks_dashboard_manager': has_group_ks_dashboard_manager,
            'ks_dashboard_list': self.search_read([], ['id', 'name']),
            'dashboard_start_date': self._context.get('ksDateFilterStartDate', False) or self.browse(
                ks_dashboard_id).dashboard_start_date,
            'dashboard_end_date': self._context.get('ksDateFilterEndDate', False) or self.browse(
                ks_dashboard_id).dashboard_end_date,
            'date_filter_selection': self._context.get('ksDateFilterSelection', False) or self.browse(
                ks_dashboard_id).date_filter_selection,
            'gridstack_config': "{}",
            'set_interval': ks_dashboard_rec.set_interval,
            'data_formatting': ks_dashboard_rec.data_formatting,
            'dashboard_items_ids': ks_dashboard_rec.dashboard_items_ids.ids,
            'ks_item_data': {},
            'ks_child_boards': False,
            'ks_selected_board_id': False,
            'ks_dashboard_domain_data': ks_dashboard_rec.ks_prepare_dashboard_domain(),
            'ks_dashboard_pre_domain_filter': ks_dashboard_rec.ks_prepare_dashboard_pre_domain(),
            'ks_dashboard_custom_domain_filter': ks_dashboard_rec.ks_prepare_dashboard_custom_domain(),
            'ks_item_model_relation': dict([(x['id'], [x['lbs_model_name'], x['lbs_model_name_2']]) for x in
                                            ks_dashboard_rec.dashboard_items_ids.read(
                                                ['lbs_model_name', 'lbs_model_name_2'])]),
            'ks_model_item_relation': {},
        }

        default_grid_id = ks_dashboard_rec.ks_get_grid_config()
        dashboard_data['gridstack_config'] = default_grid_id.gridstack_config
        dashboard_data['ks_gridstack_config_id'] = default_grid_id.id

        if self.env['lbs.dashboard_child'].search(
                [['id', 'in', ks_dashboard_rec.child_dashboard_ids.ids], ['company_id', '=', self.env.company.id],
                 ['board_type', '!=', 'default']], limit=1):
            dashboard_data['ks_child_boards'] = {
                'ks_default': [ks_dashboard_rec.name, default_grid_id.gridstack_config]}
            selecred_rec = self.env['lbs.dashboard_child'].search(
                [['id', 'in', ks_dashboard_rec.child_dashboard_ids.ids], ['is_active', '=', True],
                 ['company_id', '=', self.env.company.id], ['board_type', '!=', 'default']], limit=1)
            if selecred_rec:
                dashboard_data['ks_selected_board_id'] = str(selecred_rec.id)
                dashboard_data['gridstack_config'] = selecred_rec.gridstack_config
            else:
                dashboard_data['ks_selected_board_id'] = 'ks_default'
            for rec in self.env['lbs.dashboard_child'].search_read(
                    [['id', 'in', ks_dashboard_rec.child_dashboard_ids.ids],
                     ['company_id', '=', self.env.company.id], ['board_type', '!=', 'default']],
                    ['name', 'gridstack_config']):
                dashboard_data['ks_child_boards'][str(rec['id'])] = [rec['name'], rec['gridstack_config']]
        ks_item_domain = ks_item_domain or []
        try:
            items = self.dashboard_items_ids.search(
                [['dashboard_lbs_board_id', '=', ks_dashboard_id]] + ks_item_domain).ids
        except Exception as e:
            items = self.dashboard_items_ids.search(
                [['dashboard_lbs_board_id', '=', ks_dashboard_id]] + ks_item_domain).ids
        dashboard_data['dashboard_items_ids'] = items
        return dashboard_data

    @api.model
    def ks_fetch_item(self, item_list, ks_dashboard_id, params={}):
        """
        :rtype: object
        :param item_list: list of item ids.
        :return: {'id':[item_data]}
        """
        self = self.ks_set_date(ks_dashboard_id)
        items = {}
        item_model = self.env['lbs.dashboard_items']
        for item_id in item_list:
            item = self.ks_fetch_item_data(item_model.browse(item_id), params)
            items[item['id']] = item
        return items

    # fetching Item info (Divided to make function inherit easily)
    def ks_fetch_item_data(self, rec, params={}):
        """
        :rtype: object
        :param item_id: item object
        :return: object with formatted item data
        """
        try:
            ks_precision = self.sudo().env.ref('lbs_dashboard.ks_dashboard_ninja_precision')
            ks_precision_digits = ks_precision.digits
            if ks_precision_digits < 0:
                ks_precision_digits = 2
            if ks_precision_digits > 100:
                ks_precision_digits = 2
        except Exception as e:
            ks_precision_digits = 2

        action = {}
        item_domain1 = params.get('lbs_domain_1', [])
        item_domain2 = params.get('lbs_domain_2', [])
        if rec.ks_actions:
            context = {}
            try:
                context = eval(rec.ks_actions.context)
            except Exception:
                context = {}

            action['name'] = rec.ks_actions.name
            action['type'] = rec.ks_actions.type
            action['res_model'] = rec.ks_actions.res_model
            action['views'] = rec.ks_actions.views
            action['view_mode'] = rec.ks_actions.view_mode
            action['search_view_id'] = rec.ks_actions.search_view_id.id
            action['context'] = context
            action['target'] = 'current'
        elif rec.ks_is_client_action and rec.ks_client_action:
            clint_action = {}
            clint_action['name'] = rec.ks_client_action.name
            clint_action['type'] = rec.ks_client_action.type
            clint_action['res_model'] = rec.ks_client_action.res_model
            clint_action['xml_id'] = rec.ks_client_action.xml_id
            clint_action['tag'] = rec.ks_client_action.tag
            clint_action['binding_type'] = rec.ks_client_action.binding_type
            clint_action['params'] = rec.ks_client_action.params
            clint_action['target'] = 'current'

            action = clint_action,
        else:
            action = False
        ks_currency_symbol = False
        ks_currency_position = False
        if rec.ks_unit and rec.ks_unit_selection == 'monetary':
            try:
                ks_currency_symbol = self.env.user.company_id.currency_id.symbol
                ks_currency_position = self.env.user.company_id.currency_id.position
            except Exception as E:
                ks_currency_symbol = False
                ks_currency_position = False

        item = {
            'name': rec.name if rec.name else rec.model_id.name if rec.model_id else "Name",
            'background_color': rec.background_color,
            'lbs_font_color': rec.lbs_font_color,
            'ks_header_bg_color': rec.ks_header_bg_color,
            # 'ks_domain': rec.ks_domain.replace('"%UID"', str(
            #     self.env.user.id)) if rec.ks_domain and "%UID" in rec.ks_domain else rec.ks_domain,
            'lbs_domain': rec.ks_convert_into_proper_domain(rec.lbs_domain, rec, item_domain1),
            'ks_dashboard_id': rec.dashboard_lbs_board_id.id,
            'lbs_icon': rec.lbs_icon,
            'model_id': rec.model_id.id,
            'lbs_model_name': rec.lbs_model_name,
            'ks_model_display_name': rec.model_id.name,
            'record_count_type': rec.record_count_type,
            'lbs_record_count': rec._ksGetRecordCount(item_domain1),
            'id': rec.id,
            'lbs_layout': rec.lbs_layout,
            'icon_select': rec.icon_select,
            'default_icon': rec.default_icon,
            'default_icon_color': rec.default_icon_color,
            # Pro Fields
            'dashboard_item_type': rec.dashboard_item_type,
            'ks_chart_item_color': rec.ks_chart_item_color,
            'chart_groupby_type': rec.chart_groupby_type,
            'lbs_chart_relation_groupby': rec.lbs_chart_relation_groupby.id,
            'ks_chart_relation_groupby_name': rec.lbs_chart_relation_groupby.name,
            'ks_chart_date_groupby': rec.ks_chart_date_groupby,
            'lbs_record_field': rec.lbs_record_field.id if rec.lbs_record_field else False,
            'ks_chart_data': rec._ks_get_chart_data(item_domain1),
            'ks_list_view_data': rec._ksGetListViewData(item_domain1),
            'ks_chart_data_count_type': rec.ks_chart_data_count_type,
            'ks_bar_chart_stacked': rec.ks_bar_chart_stacked,
            'ks_semi_circle_chart': rec.ks_semi_circle_chart,
            'ks_list_view_type': rec.ks_list_view_type,
            'ks_list_view_group_fields': rec.ks_list_view_group_fields.ids if rec.ks_list_view_group_fields else False,
            'previous_period': rec.previous_period,
            'ks_kpi_data': rec._ksGetKpiData(item_domain1, item_domain2),
            'ks_goal_enable': rec.ks_goal_enable,
            'lbs_model_id_2': rec.lbs_model_id_2.id,
            'record_field_2': rec.record_field_2.id,
            'ks_data_comparison': rec.ks_data_comparison,
            'ks_target_view': rec.ks_target_view,
            'date_filter_selection': rec.date_filter_selection,
            'ks_show_data_value': rec.ks_show_data_value,
            'ks_update_items_data': rec.ks_update_items_data,
            'ks_show_records': rec.ks_show_records,
            # 'action_id': rec.ks_actions.id if rec.ks_actions else False,
            'sequence': 0,
            'max_sequnce': len(rec.ks_action_lines) if rec.ks_action_lines else False,
            'action': action,
            'ks_hide_legend': rec.ks_hide_legend,
            'ks_data_calculation_type': rec.ks_data_calculation_type,
            'ks_export_all_records': rec.ks_export_all_records,
            'data_formatting': rec.ks_data_format,
            'ks_auto_update_type': rec.ks_auto_update_type,
            'ks_show_live_pop_up': rec.ks_show_live_pop_up,
            'ks_is_client_action': rec.ks_is_client_action,
            'ks_pagination_limit': rec.ks_pagination_limit,
            'ks_record_data_limit': rec.ks_record_data_limit,
            'ks_chart_cumulative_field': rec.ks_chart_cumulative_field.ids,
            'ks_chart_cumulative': rec.ks_chart_cumulative,
            'ks_button_color': rec.ks_button_color,
            'ks_to_do_data': rec._ksGetToDOData(),
            'ks_multiplier_active': rec.ks_multiplier_active,
            'ks_multiplier': rec.ks_multiplier,
            'ks_goal_liness': True if rec.ks_goal_lines else False,
            'ks_currency_symbol': ks_currency_symbol,
            'ks_currency_position': ks_currency_position,
            'ks_precision_digits': ks_precision_digits if ks_precision_digits else 2
        }
        return item

    def ks_set_date(self, ks_dashboard_id):
        ks_dashboard_rec = self.browse(ks_dashboard_id)
        if self._context.get('ksDateFilterSelection', False):
            date_filter_selection = self._context['ksDateFilterSelection']
            if date_filter_selection == 'l_custom':
                ks_start_dt_parse = parse(self._context['ksDateFilterStartDate'])
                ks_end_dt_parse = parse(self._context['ksDateFilterEndDate'])
                self = self.with_context(
                    ksDateFilterStartDate=fields.datetime.strptime(ks_start_dt_parse.strftime("%Y-%m-%d %H:%M:%S"),
                                                                   "%Y-%m-%d %H:%M:%S"))
                self = self.with_context(
                    ksDateFilterEndDate=fields.datetime.strptime(ks_end_dt_parse.strftime("%Y-%m-%d %H:%M:%S"),
                                                                 "%Y-%m-%d %H:%M:%S"))
                self = self.with_context(ksIsDefultCustomDateFilter=False)

        else:
            date_filter_selection = ks_dashboard_rec.date_filter_selection
            self = self.with_context(ksDateFilterStartDate=ks_dashboard_rec.dashboard_start_date)
            self = self.with_context(ksDateFilterEndDate=ks_dashboard_rec.dashboard_end_date)
            self = self.with_context(ksDateFilterSelection=date_filter_selection)
            self = self.with_context(ksIsDefultCustomDateFilter=True)

        if date_filter_selection not in ['l_custom', 'l_none']:
            ks_date_data = ks_get_date(date_filter_selection, self, 'datetime')
            self = self.with_context(ksDateFilterStartDate=ks_date_data["selected_start_date"])
            self = self.with_context(ksDateFilterEndDate=ks_date_data["selected_end_date"])

        return self

    @api.model
    def ks_get_list_view_data_offset(self, ks_dashboard_item_id, offset, dashboard_id, params={}):
        item_domain = params.get('lbs_domain_1', [])
        self = self.ks_set_date(dashboard_id)
        item = self.dashboard_items_ids.browse(ks_dashboard_item_id)

        return item.ks_get_next_offset(ks_dashboard_item_id, offset, item_domain)

    def ks_view_items_view(self):
        self.ensure_one()
        return {
            'name': _("Dashboard Items"),
            'res_model': 'lbs.dashboard_items',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'views': [(False, 'tree'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('dashboard_lbs_board_id', '!=', False)],
            'search_view_id': self.env.ref('lbs_dashboard.ks_item_search_view').id,
            'context': {
                'search_default_ks_dashboard_ninja_board_id': self.id,
                'group_by': 'dashboard_lbs_board_id',
            },
            'help': _('''<p class="o_view_nocontent_smiling_face">
                                        You can find all items related to Dashboard Here.</p>
                                    '''),

        }

    def ks_export_item(self, item_id):
        return {
            'ks_file_format': 'ks_dashboard_ninja_item_export',
            'item': self.ks_export_item_data(self.dashboard_items_ids.browse(int(item_id)))
        }

    # fetching Item info (Divided to make function inherit easily)
    def ks_export_item_data(self, rec):
        ks_timezone = self._context.get('tz') or self.env.user.tz
        ks_chart_measure_field = []
        ks_chart_measure_field_2 = []
        for res in rec.ks_chart_measure_field:
            ks_chart_measure_field.append(res.name)
        for res in rec.ks_chart_measure_field_2:
            ks_chart_measure_field_2.append(res.name)

        ks_multiplier_fields = []
        ks_multiplier_value = []
        if rec.ks_multiplier_lines:
            for ress in rec.ks_multiplier_lines.ks_multiplier_fields:
                ks_multiplier_fields.append(ress.name)
            for ks_val in rec.ks_multiplier_lines:
                ks_multiplier_value.append(ks_val.ks_multiplier_value)

        ks_list_view_group_fields = []
        for res in rec.ks_list_view_group_fields:
            ks_list_view_group_fields.append(res.name)

        ks_goal_lines = []
        for res in rec.ks_goal_lines:
            goal_line = {
                'ks_goal_date': datetime.datetime.strftime(res.ks_goal_date, "%Y-%m-%d"),
                'ks_goal_value': res.ks_goal_value,
            }
            ks_goal_lines.append(goal_line)
        ks_dn_header_lines = []
        for res in rec.ks_dn_header_lines:
            ks_dn_header_line = {
                'ks_to_do_header': res.ks_to_do_header
            }

            if res.ks_to_do_description_lines:
                ks_to_do_description_lines = []
                for ks_description_line in res.ks_to_do_description_lines:
                    description_line = {
                        'ks_description': ks_description_line.ks_description,
                        'is_active': ks_description_line.is_active,
                    }
                    ks_to_do_description_lines.append(description_line)
                ks_dn_header_line[res.ks_to_do_header] = ks_to_do_description_lines
            ks_dn_header_lines.append(ks_dn_header_line)

        ks_action_lines = []
        for res in rec.ks_action_lines:
            action_line = {
                'ks_item_action_field': res.ks_item_action_field.name,
                'ks_item_action_date_groupby': res.ks_item_action_date_groupby,
                'ks_chart_type': res.ks_chart_type,
                'ks_sort_by_field': res.ks_sort_by_field.name,
                'ks_sort_by_order': res.ks_sort_by_order,
                'ks_record_limit': res.ks_record_limit,
                'sequence': res.sequence,
            }
            ks_action_lines.append(action_line)
        ks_multiplier_lines = []
        for res in rec.ks_multiplier_lines:
            ks_multiplier_line = {
                'ks_multiplier_fields': res.ks_multiplier_fields.id,
                'ks_multiplier_value': res.ks_multiplier_value,
                'ks_dashboard_item_id': rec.id,
                'model_id': rec.model_id.id
            }
            ks_multiplier_lines.append(ks_multiplier_line)

        ks_list_view_field = []
        for res in rec.ks_list_view_fields:
            ks_list_view_field.append(res.name)

        val = str(rec.id)
        selecred_rec = self.env['lbs.dashboard_child'].search(
            [['id', 'in', rec.dashboard_lbs_board_id.child_dashboard_ids.ids], ['is_active', '=', True],
             ['company_id', '=', self.env.company.id]], limit=1)
        if rec.dashboard_lbs_board_id.gridstack_config:
            keys_data = json.loads(rec.dashboard_lbs_board_id.gridstack_config)
        elif selecred_rec:
            keys_data = json.loads(selecred_rec.gridstack_config)
        elif rec.dashboard_lbs_board_id.child_dashboard_ids[0].gridstack_config:
            keys_data = json.loads(rec.dashboard_lbs_board_id.child_dashboard_ids[0].gridstack_config)
        else:
            keys_data = {rec.id: json.loads(rec.grid_corners.replace("\'", "\""))}
        keys_list = keys_data.keys()
        grid_corners = {}
        if val in keys_list:
            grid_corners = keys_data.get(str(val))

        item = {
            'name': rec.name if rec.name else rec.model_id.name if rec.model_id else "Name",
            'background_color': rec.background_color,
            'lbs_font_color': rec.lbs_font_color,
            'ks_header_bg_color': rec.ks_header_bg_color,
            'lbs_domain': rec.lbs_domain,
            'lbs_icon': str(rec.lbs_icon) if rec.lbs_icon else False,
            'ks_id': rec.id,
            'model_id': rec.lbs_model_name,
            'lbs_record_count': rec.lbs_record_count,
            'lbs_layout': rec.lbs_layout,
            'icon_select': rec.icon_select,
            'default_icon': rec.default_icon,
            'default_icon_color': rec.default_icon_color,
            'record_count_type': rec.record_count_type,
            # Pro Fields
            'dashboard_item_type': rec.dashboard_item_type,
            'ks_chart_item_color': rec.ks_chart_item_color,
            'chart_groupby_type': rec.chart_groupby_type,
            'lbs_chart_relation_groupby': rec.lbs_chart_relation_groupby.name,
            'ks_chart_date_groupby': rec.ks_chart_date_groupby,
            'lbs_record_field': rec.lbs_record_field.name,
            'chart_sub_groupby_type': rec.chart_sub_groupby_type,
            'ks_chart_relation_sub_groupby': rec.ks_chart_relation_sub_groupby.name,
            'ks_chart_date_sub_groupby': rec.ks_chart_date_sub_groupby,
            'ks_chart_data_count_type': rec.ks_chart_data_count_type,
            'ks_chart_measure_field': ks_chart_measure_field,
            'ks_chart_measure_field_2': ks_chart_measure_field_2,
            'ks_list_view_fields': ks_list_view_field,
            'ks_list_view_group_fields': ks_list_view_group_fields,
            'ks_list_view_type': rec.ks_list_view_type,
            'ks_record_data_limit': rec.ks_record_data_limit,
            'ks_sort_by_order': rec.ks_sort_by_order,
            'ks_sort_by_field': rec.ks_sort_by_field.name,
            'date_filter_field': rec.date_filter_field.name,
            'ks_goal_enable': rec.ks_goal_enable,
            'ks_standard_goal_value': rec.ks_standard_goal_value,
            'ks_goal_liness': ks_goal_lines,
            'date_filter_selection': rec.date_filter_selection,
            'item_start_date': rec.item_start_date.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.item_start_date else False,
            'item_end_date': rec.item_end_date.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.item_end_date else False,
            'date_filter_selection_2': rec.date_filter_selection_2,
            'item_start_date_2': rec.item_start_date_2.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.item_start_date_2 else False,
            'item_end_date_2': rec.item_end_date_2.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.item_end_date_2 else False,
            'previous_period': rec.previous_period,
            'ks_target_view': rec.ks_target_view,
            'ks_data_comparison': rec.ks_data_comparison,
            'lbs_record_count_type_2': rec.lbs_record_count_type_2,
            'record_field_2': rec.record_field_2.name,
            'lbs_model_id_2': rec.lbs_model_id_2.model,
            'date_filter_field_2': rec.date_filter_field_2.name,
            'ks_action_liness': ks_action_lines,
            'ks_compare_period': rec.ks_compare_period,
            'ks_year_period': rec.ks_year_period,
            'ks_compare_period_2': rec.ks_compare_period_2,
            'ks_year_period_2': rec.ks_year_period_2,
            'lbs_domain_2': rec.lbs_domain_2,
            'ks_show_data_value': rec.ks_show_data_value,
            'ks_auto_update_type': rec.ks_auto_update_type,
            'ks_show_live_pop_up': rec.ks_show_live_pop_up,
            'ks_update_items_data': rec.ks_update_items_data,
            'ks_list_target_deviation_field': rec.ks_list_target_deviation_field.name,
            'ks_unit': rec.ks_unit,
            'ks_show_records': rec.ks_show_records,
            'ks_hide_legend': rec.ks_hide_legend,
            'ks_fill_temporal': rec.ks_fill_temporal,
            'ks_domain_extension': rec.ks_domain_extension,
            'ks_unit_selection': rec.ks_unit_selection,
            'ks_chart_unit': rec.ks_chart_unit,
            'ks_bar_chart_stacked': rec.ks_bar_chart_stacked,
            'ks_goal_bar_line': rec.ks_goal_bar_line,
            'ks_actions': rec.ks_actions.xml_id if rec.ks_actions else False,
            'ks_client_action': rec.ks_client_action.xml_id if rec.ks_client_action else False,
            'ks_is_client_action': rec.ks_is_client_action,
            'ks_export_all_records': rec.ks_export_all_records,
            'record_data_limit_visibility': rec.record_data_limit_visibility,
            'ks_data_format': rec.ks_data_format,
            'ks_pagination_limit': rec.ks_pagination_limit,
            'ks_chart_cumulative_field': rec.ks_chart_cumulative_field.ids,
            'ks_chart_cumulative': rec.ks_chart_cumulative,
            'ks_button_color': rec.ks_button_color,
            'ks_dn_header_line': ks_dn_header_lines,
            'ks_semi_circle_chart': rec.ks_semi_circle_chart,
            'ks_multiplier_active': rec.ks_multiplier_active,
            'ks_multiplier': rec.ks_multiplier,
            'ks_multiplier_lines': ks_multiplier_lines if ks_multiplier_lines else False,
        }
        if grid_corners:
            item.update({
                'grid_corners': grid_corners,
            })
        return item

    def ks_open_import(self, **kwargs):
        action = self.env['ir.actions.act_window']._for_xml_id('lbs_dashboard.ks_import_dashboard_action')
        return action

    def ks_open_setting(self, **kwargs):
        action = self.env['ir.actions.act_window']._for_xml_id('lbs_dashboard.board_form_tree_action_window')
        action['res_id'] = self.id
        action['target'] = 'new'
        action['context'] = {'create': False}
        return action

    def ks_delete_dashboard(self):
        if str(self.id) in self.dashboard_default_template:
            raise ValidationError(_('You cannot delete any default template'))
        else:
            self.search([('id', '=', self.id)]).unlink()
            return {
                'type': 'ir.actions.client',
                'name': "Dashboard Ninja",
                'res_model': 'ks_deshboard_ninja.board',
                'params': {'ks_dashboard_id': 1},
                'tag': 'lbs_dashboard',
            }

    def ks_create_dashboard(self):
        action = self.env['ir.actions.act_window']._for_xml_id('lbs_dashboard.board_form_tree_action_window')
        action['target'] = 'new'
        return action

    def ks_import_item(self, dashboard_id, **kwargs):
        try:
            # ks_dashboard_data = json.loads(file)
            file = kwargs.get('file', False)
            ks_dashboard_file_read = json.loads(file)
        except Exception:
            raise ValidationError(_("This file is not supported"))

        if 'ks_file_format' in ks_dashboard_file_read and ks_dashboard_file_read[
            'ks_file_format'] == 'ks_dashboard_ninja_item_export':
            item = ks_dashboard_file_read['item']
        else:
            raise ValidationError(_("Current Json File is not properly formatted according to Dashboard Ninja Model."))

        item['dashboard_lbs_board_id'] = int(dashboard_id)
        item['ks_company_id'] = False
        self.ks_create_item(item)

        return "Success"

    @api.model
    def ks_dashboard_export(self, ks_dashboard_ids, **kwargs):
        ks_dashboard_data = []
        ks_dashboard_export_data = {}
        if kwargs.get('dashboard_id'):
            ks_dashboard_ids = '['+str(ks_dashboard_ids)+']'
        ks_dashboard_ids = json.loads(ks_dashboard_ids)
        for ks_dashboard_id in ks_dashboard_ids:
            dash = self.search([('id', '=', ks_dashboard_id)])
            selecred_rec = self.env['lbs.dashboard_child'].search(
                [['id', 'in', dash.child_dashboard_ids.ids], ['is_active', '=', True],
                 ['company_id', '=', self.env.company.id]], limit=1)
            ks_dashboard_rec = self.browse(ks_dashboard_id)
            dashboard_data = {
                'name': ks_dashboard_rec.name,
                'dashboard_menu_name': ks_dashboard_rec.dashboard_menu_name,
                'gridstack_config': ks_dashboard_rec.gridstack_config,
                'set_interval': ks_dashboard_rec.set_interval,
                'date_filter_selection': ks_dashboard_rec.date_filter_selection,
                'dashboard_start_date': ks_dashboard_rec.dashboard_start_date,
                'dashboard_end_date': ks_dashboard_rec.dashboard_end_date,
                'dashboard_top_menu_id': ks_dashboard_rec.dashboard_top_menu_id.id,
                'data_formatting': ks_dashboard_rec.data_formatting,
            }
            if selecred_rec:
                dashboard_data['name'] = selecred_rec.name
                dashboard_data['gridstack_config'] = selecred_rec.gridstack_config
            elif len(ks_dashboard_rec.child_dashboard_ids) == 1:
                dashboard_data['name'] = ks_dashboard_rec.child_dashboard_ids.name
                dashboard_data['gridstack_config'] = ks_dashboard_rec.child_dashboard_ids.gridstack_config
            if dashboard_data['name'] != 'Default Board Layout':
                dashboard_data['dashboard_menu_name'] = selecred_rec.name
            if dashboard_data['name'] == 'Default Board Layout':
                dashboard_data['name'] = ks_dashboard_rec.dashboard_menu_name
            if len(ks_dashboard_rec.dashboard_items_ids) < 1:
                dashboard_data['ks_item_data'] = False
            else:
                items = []
                for rec in ks_dashboard_rec.dashboard_items_ids:
                    item = self.ks_export_item_data(rec)
                    items.append(item)

                dashboard_data['ks_item_data'] = items

            ks_dashboard_data.append(dashboard_data)

            ks_dashboard_export_data = {
                'ks_file_format': 'ks_dashboard_ninja_export_file',
                'ks_dashboard_data': ks_dashboard_data
            }
        return ks_dashboard_export_data

    @api.model
    def ks_import_dashboard(self, file, menu_id):
        try:
            # ks_dashboard_data = json.loads(file)
            ks_dashboard_file_read = json.loads(file)
        except Exception:
            raise ValidationError(_("This file is not supported"))

        if 'ks_file_format' in ks_dashboard_file_read and ks_dashboard_file_read[
            'ks_file_format'] == 'ks_dashboard_ninja_export_file':
            ks_dashboard_data = ks_dashboard_file_read['ks_dashboard_data']
        else:
            raise ValidationError(_("Current Json File is not properly formatted according to Dashboard Ninja Model."))

        ks_dashboard_key = ['name', 'dashboard_menu_name', 'gridstack_config']
        ks_dashboard_item_key = ['model_id', 'ks_chart_measure_field', 'ks_list_view_fields', 'lbs_record_field',
                                 'lbs_chart_relation_groupby', 'ks_id']

        # Fetching dashboard model info
        for data in ks_dashboard_data:
            if not all(key in data for key in ks_dashboard_key):
                raise ValidationError(
                    _("Current Json File is not properly formatted according to Dashboard Ninja Model."))
            dashboard_top_menu_id = data.get('dashboard_top_menu_id', False)
            if dashboard_top_menu_id:
                try:
                    self.env['ir.ui.menu'].browse(dashboard_top_menu_id).name
                    dashboard_top_menu_id = self.env['ir.ui.menu'].browse(dashboard_top_menu_id)
                except Exception:
                    dashboard_top_menu_id = False
            vals = {
                'name': data['name'],
                'dashboard_menu_name': data['dashboard_menu_name'],
                'dashboard_top_menu_id': menu_id.id if menu_id else self.env.ref(
                    "lbs_dashboard.board_menu_root").id,
                'dashboard_active': True,
                'gridstack_config': data['gridstack_config'],
                'dashboard_default_template': self.env.ref("lbs_dashboard.ks_blank").id,
                'dashboard_group_access': False,
                'set_interval': data['set_interval'],
                'date_filter_selection': data['date_filter_selection'],
                'dashboard_start_date': data['dashboard_start_date'],
                'dashboard_end_date': data['dashboard_end_date'],
            }
            # Creating Dashboard
            dashboard_id = self.create(vals)

            if data['gridstack_config']:
                gridstack_config = eval(data['gridstack_config'])
            ks_grid_stack_config = {}

            item_ids = []
            item_new_ids = []
            ks_skiped = False
            if data['ks_item_data']:
                # Fetching dashboard item info
                ks_skiped = 0
                for item in data['ks_item_data']:
                    item['ks_company_id'] = False
                    if not all(key in item for key in ks_dashboard_item_key):
                        raise ValidationError(
                            _("Current Json File is not properly formatted according to Dashboard Ninja Model."))

                    # Creating dashboard items
                    item['dashboard_lbs_board_id'] = dashboard_id.id
                    item_ids.append(item['ks_id'])
                    del item['ks_id']

                    if 'ks_data_calculation_type' in item:
                        if item['ks_data_calculation_type'] == 'custom':
                            del item['ks_data_calculation_type']
                            del item['ks_custom_query']
                            del item['ks_xlabels']
                            del item['ks_ylabels']
                            del item['ks_list_view_layout']
                            ks_item = self.ks_create_item(item)
                            item_new_ids.append(ks_item.id)
                        else:
                            ks_skiped += 1
                    else:
                        ks_item = self.ks_create_item(item)
                        item_new_ids.append(ks_item.id)

            for id_index, id in enumerate(item_ids):
                if data['gridstack_config'] and str(id) in gridstack_config:
                    ks_grid_stack_config[str(item_new_ids[id_index])] = gridstack_config[str(id)]
                    # if id_index in item_new_ids:

            self.browse(dashboard_id.id).write({
                'gridstack_config': json.dumps(ks_grid_stack_config)
            })

            if ks_skiped:
                return {
                    'ks_skiped_items': ks_skiped,
                }

        return "Success"
        # separate function to make item for import

    def ks_create_item(self, item):
        model = self.env['ir.model'].search([('model', '=', item['model_id'])])

        if not model and not item['dashboard_item_type'] == 'ks_to_do':
            raise ValidationError(_(
                "Please Install the Module which contains the following Model : %s " % item['model_id']))

        lbs_model_name = item['model_id']

        ks_goal_lines = item['ks_goal_liness'].copy() if item.get('ks_goal_liness', False) else False
        ks_action_lines = item['ks_action_liness'].copy() if item.get('ks_action_liness', False) else False
        ks_multiplier_lines = item['ks_multiplier_lines'].copy() if item.get('ks_multiplier_lines', False) else False
        ks_dn_header_line = item['ks_dn_header_line'].copy() if item.get('ks_dn_header_line', False) else False

        # Creating dashboard items
        item = self.ks_prepare_item(item)

        if 'ks_goal_liness' in item:
            del item['ks_goal_liness']
        if 'ks_id' in item:
            del item['ks_id']
        if 'ks_action_liness' in item:
            del item['ks_action_liness']
        if 'lbs_icon' in item:
            item['icon_select'] = "Default"
            item['lbs_icon'] = False
        if 'ks_dn_header_line' in item:
            del item['ks_dn_header_line']
        if 'ks_multiplier_lines' in item:
            del item['ks_multiplier_lines']

        ks_item = self.env['lbs.dashboard_items'].create(item)

        if ks_goal_lines and len(ks_goal_lines) != 0:
            for line in ks_goal_lines:
                line['ks_goal_date'] = datetime.datetime.strptime(line['ks_goal_date'].split(" ")[0],
                                                                  '%Y-%m-%d')
                line['ks_dashboard_item'] = ks_item.id
                self.env['lbs.dashboard_item_goal'].create(line)

        if ks_dn_header_line and len(ks_dn_header_line) != 0:
            for line in ks_dn_header_line:
                ks_line = {}
                ks_line['ks_to_do_header'] = line.get('ks_to_do_header')
                ks_line['ks_dn_item_id'] = ks_item.id
                ks_dn_header_id = self.env['lbs.to_do_headers'].create(ks_line)
                if line.get(line.get('ks_to_do_header'), False):
                    for ks_task in line.get(line.get('ks_to_do_header')):
                        ks_task['ks_to_do_header_id'] = ks_dn_header_id.id
                        self.env['lbs.to_do_description'].create(ks_task)

        if ks_action_lines and len(ks_action_lines) != 0:

            for line in ks_action_lines:
                if line['ks_sort_by_field']:
                    ks_sort_by_field = line['ks_sort_by_field']
                    ks_sort_record_id = self.env['ir.model.fields'].search(
                        [('model', '=', lbs_model_name), ('name', '=', ks_sort_by_field)])
                    if ks_sort_record_id:
                        line['ks_sort_by_field'] = ks_sort_record_id.id
                    else:
                        line['ks_sort_by_field'] = False
                if line['ks_item_action_field']:
                    ks_item_action_field = line['ks_item_action_field']
                    ks_record_id = self.env['ir.model.fields'].search(
                        [('model', '=', lbs_model_name), ('name', '=', ks_item_action_field)])
                    if ks_record_id:
                        line['ks_item_action_field'] = ks_record_id.id
                        line['ks_dashboard_item_id'] = ks_item.id
                        self.env['lbs.dashboard_item_action'].create(line)

        if ks_multiplier_lines and len(ks_multiplier_lines) != 0:
            for rec in ks_multiplier_lines:
                ks_multiplier_field = rec['ks_multiplier_fields']
                ks_multiplier_field_id = self.env['ir.model.fields'].search(
                    [('model', '=', lbs_model_name), ('id', '=', ks_multiplier_field)])
                if ks_multiplier_field:
                    rec['ks_multiplier_fields'] = ks_multiplier_field_id.id
                    rec['ks_dashboard_item_id'] = ks_item.id
                    self.env['lbs.dashboard_items_multiplier'].create(rec)

        return ks_item

    def ks_prepare_item(self, item):
        ks_measure_field_ids = []
        ks_measure_field_2_ids = []

        for ks_measure in item['ks_chart_measure_field']:
            ks_measure_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_measure), ('model', '=', item['model_id'])])
            if ks_measure_id:
                ks_measure_field_ids.append(ks_measure_id.id)
        item['ks_chart_measure_field'] = [(6, 0, ks_measure_field_ids)]

        for ks_measure in item['ks_chart_measure_field_2']:
            ks_measure_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_measure), ('model', '=', item['model_id'])])
            if ks_measure_id:
                ks_measure_field_2_ids.append(ks_measure_id.id)
        item['ks_chart_measure_field_2'] = [(6, 0, ks_measure_field_2_ids)]

        ks_list_view_group_fields = []
        for ks_measure in item['ks_list_view_group_fields']:
            ks_measure_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_measure), ('model', '=', item['model_id'])])

            if ks_measure_id:
                ks_list_view_group_fields.append(ks_measure_id.id)
        item['ks_list_view_group_fields'] = [(6, 0, ks_list_view_group_fields)]

        ks_list_view_field_ids = []
        for ks_list_field in item['ks_list_view_fields']:
            ks_list_field_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_list_field), ('model', '=', item['model_id'])])
            if ks_list_field_id:
                ks_list_view_field_ids.append(ks_list_field_id.id)
        item['ks_list_view_fields'] = [(6, 0, ks_list_view_field_ids)]

        if item['lbs_record_field']:
            lbs_record_field = item['lbs_record_field']
            ks_record_id = self.env['ir.model.fields'].search(
                [('name', '=', lbs_record_field), ('model', '=', item['model_id'])])
            if ks_record_id:
                item['lbs_record_field'] = ks_record_id.id
            else:
                item['lbs_record_field'] = False

        if item['date_filter_field']:
            date_filter_field = item['date_filter_field']
            ks_record_id = self.env['ir.model.fields'].search(
                [('name', '=', date_filter_field), ('model', '=', item['model_id'])])
            if ks_record_id:
                item['date_filter_field'] = ks_record_id.id
            else:
                item['date_filter_field'] = False

        if item['lbs_chart_relation_groupby']:
            ks_group_by = item['lbs_chart_relation_groupby']
            ks_record_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_group_by), ('model', '=', item['model_id'])])
            if ks_record_id:
                item['lbs_chart_relation_groupby'] = ks_record_id.id
            else:
                item['lbs_chart_relation_groupby'] = False

        if item['ks_chart_relation_sub_groupby']:
            ks_group_by = item['ks_chart_relation_sub_groupby']
            ks_chart_relation_sub_groupby = self.env['ir.model.fields'].search(
                [('name', '=', ks_group_by), ('model', '=', item['model_id'])])
            if ks_chart_relation_sub_groupby:
                item['ks_chart_relation_sub_groupby'] = ks_chart_relation_sub_groupby.id
            else:
                item['ks_chart_relation_sub_groupby'] = False

        # Sort by field : Many2one Entery
        if item['ks_sort_by_field']:
            ks_group_by = item['ks_sort_by_field']
            ks_sort_by_field = self.env['ir.model.fields'].search(
                [('name', '=', ks_group_by), ('model', '=', item['model_id'])])
            if ks_sort_by_field:
                item['ks_sort_by_field'] = ks_sort_by_field.id
            else:
                item['ks_sort_by_field'] = False

        if item['ks_list_target_deviation_field']:
            ks_list_target_deviation_field = item['ks_list_target_deviation_field']
            record_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_list_target_deviation_field), ('model', '=', item['model_id'])])
            if record_id:
                item['ks_list_target_deviation_field'] = record_id.id
            else:
                item['ks_list_target_deviation_field'] = False

        model_id = self.env['ir.model'].search([('model', '=', item['model_id'])]).id

        if item.get("ks_actions"):
            ks_action = self.env.ref(item["ks_actions"], False)
            if ks_action:
                item["ks_actions"] = ks_action.id
            else:
                item["ks_actions"] = False
        if item.get("ks_client_action"):
            ks_action = self.env.ref(item["ks_client_action"], False)
            if ks_action:
                item["ks_client_action"] = ks_action.id
            else:
                item["ks_client_action"] = False

        if (item['lbs_model_id_2']):
            ks_model_2 = item['lbs_model_id_2'].replace(".", "_")
            lbs_model_id_2 = self.env['ir.model'].search([('model', '=', item['lbs_model_id_2'])]).id
            if item['record_field_2']:
                lbs_record_field = item['record_field_2']
                ks_record_id = self.env['ir.model.fields'].search(
                    [('model', '=', item['lbs_model_id_2']), ('name', '=', lbs_record_field)])

                if ks_record_id:
                    item['record_field_2'] = ks_record_id.id
                else:
                    item['record_field_2'] = False
            if item['date_filter_field_2']:
                ks_record_id = self.env['ir.model.fields'].search(
                    [('model', '=', item['lbs_model_id_2']), ('name', '=', item['date_filter_field_2'])])

                if ks_record_id:
                    item['date_filter_field_2'] = ks_record_id.id
                else:
                    item['date_filter_field_2'] = False

            item['lbs_model_id_2'] = lbs_model_id_2
        else:
            item['date_filter_field_2'] = False
            item['record_field_2'] = False

        item['model_id'] = model_id

        item['ks_goal_liness'] = False
        item['item_start_date'] = item['item_start_date'] if \
            item['item_start_date'] else False
        item['item_end_date'] = item['item_end_date'] if \
            item['item_end_date'] else False
        item['item_start_date_2'] = item['item_start_date_2'] if \
            item['item_start_date_2'] else False
        item['item_end_date_2'] = item['item_end_date_2'] if \
            item['item_end_date_2'] else False

        return item

    @api.model
    def update_child_board(self, action, dashboard_id, data):
        dashboard_id = self.browse(dashboard_id)
        selecred_rec = self.env['lbs.dashboard_child'].search(
            [['id', 'in', dashboard_id.child_dashboard_ids.ids],
             ['company_id', '=', self.env.company.id], ['is_active', '=', True]], limit=1)
        if action == 'create':
            dashboard_id.child_dashboard_ids.write({'is_active': False})
            result = self.env['lbs.dashboard_child'].create(data)
            result = result.id
        elif action == 'update':
            # result = dashboard_id.ks_child_dashboard_ids.search([['ks_active', '=', True]]).write({'ks_active': False})
            if data['ks_selected_board_id'] != 'ks_default':
                selecred_rec.is_active = False
                result = dashboard_id.child_dashboard_ids.browse(int(data['ks_selected_board_id'])).write(
                    {'is_active': True})
            else:
                result = dashboard_id.child_dashboard_ids.search([['is_active', '=', True]]).write(
                    {'is_active': False})
                for i in dashboard_id.child_dashboard_ids:
                    if i.name == 'Default Board Layout':
                        i.is_active = True
        return result

    def ks_prepare_dashboard_domain(self):
        pre_defined_filter_ids = self.env['lbs.dashboard_defined_filters'].search(
            [['id', 'in', self.dashboard_defined_filters_ids.ids], '|', ['lbs_is_active', '=', True],
             ['display_type', '=', 'line_section']], order='sequence')
        data = {}
        filter_model_ids = pre_defined_filter_ids.mapped('model_id').ids
        for model_id in filter_model_ids:
            filter_ids = self.env['lbs.dashboard_defined_filters'].search(
                [['id', 'in', pre_defined_filter_ids.ids], '|', ['model_id', '=', model_id],
                 ['display_type', '=', 'line_section']],
                order='sequence')
            connect_symbol = '|'
            for rec in filter_ids:
                if rec.display_type == 'line_section':
                    connect_symbol = '&'

                if data.get(rec.model_id.model) and rec.lbs_domain:
                    data[rec.model_id.model]['domain'] = data[rec.model_id.model]['domain'] + safe_eval(
                        rec.lbs_domain)
                    data[rec.model_id.model]['domain'].insert(0, connect_symbol)
                elif rec.model_id.model:
                    lbs_domain = rec.lbs_domain
                    if lbs_domain and "%UID" in lbs_domain:
                        lbs_domain = lbs_domain.replace('"%UID"', str(self.env.user.id))
                    if lbs_domain and "%MYCOMPANY" in lbs_domain:
                        lbs_domain = lbs_domain.replace('"%MYCOMPANY"', str(self.env.company.id))
                    data[rec.model_id.model] = {
                        'domain': safe_eval(lbs_domain) if lbs_domain else [],
                        'ks_domain_index_data': [],
                        'model_name': rec.model_id.name,
                        'item_ids': self.env['lbs.dashboard_items'].search(
                            [['id', 'in', self.dashboard_items_ids.ids], '|',
                             ['model_id', '=', rec.model_id.id], ['lbs_model_id_2', '=', rec.model_id.id]]).ids
                    }

        return data

    def ks_prepare_dashboard_pre_domain(self):
        data = {}
        pre_defined_filter_ids = self.env['lbs.dashboard_defined_filters'].search(
            [['id', 'in', self.dashboard_defined_filters_ids.ids]], order='sequence')
        categ_seq = 1
        for rec in pre_defined_filter_ids:
            if rec.display_type == 'line_section':
                categ_seq = categ_seq + 1
            lbs_domain = rec.lbs_domain
            if lbs_domain and "%UID" in lbs_domain:
                lbs_domain = lbs_domain.replace('"%UID"', str(self.env.user.id))
            if lbs_domain and "%MYCOMPANY" in lbs_domain:
                lbs_domain = lbs_domain.replace('"%MYCOMPANY"', str(self.env.company.id))

            data[rec['id']] = {
                'id': rec.id,
                'name': rec.name,
                'model': rec.model_id.model,
                'model_name': rec.model_id.name,
                'active': rec.lbs_is_active,
                'categ': rec.model_id.model + '_' + str(categ_seq) if rec.display_type != 'line_section' else 0,
                'type': 'filter' if rec.display_type != 'line_section' else 'separator',
                'domain': safe_eval(lbs_domain) if lbs_domain else [],
                'sequence': rec.sequence
            }
        return data

    def ks_prepare_dashboard_custom_domain(self):
        custom_filter_ids = self.env['lbs.dashboard_custom_filters'].search(
            [['id', 'in', self.dashboard_custom_filters_ids.ids]], order='name')
        data = {}
        for rec in custom_filter_ids:
            data[str(rec.id)] = {
                'id': rec.id,
                'name': rec.name,
                'model': rec.model_id.model,
                'model_name': rec.model_id.name,
                'field_name': rec.lbs_domain_field_id.name,
                'field_type': rec.lbs_domain_field_id.ttype,
                'special_data': {}
            }
            if rec.lbs_domain_field_id.ttype == 'selection':
                data[str(rec.id)]['special_data'] = {
                    'select_options':
                        self.env[rec.model_id.model].fields_get(allfields=[rec.lbs_domain_field_id.name])[
                            rec.lbs_domain_field_id.name]['selection']
                }
        return data
