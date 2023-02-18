# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import common_lib
from . import wizard

from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    for rec in env['lbs.dashboard'].search([]):
        rec.dashboard_client_action_id.unlink()
        rec.dashboard_menu_id.unlink()
