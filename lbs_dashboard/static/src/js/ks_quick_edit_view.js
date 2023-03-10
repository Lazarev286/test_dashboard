odoo.define('lbs_dashboard.quick_edit_view', function(require) {
    "use strict";

    var core = require('web.core');
    var Widget = require("web.Widget");
    var _t = core._t;
    var QWeb = core.qweb;
    var data = require('web.data');
    var QuickCreateFormView = require('web.QuickCreateFormView');
    var AbstractAction = require('web.AbstractAction');
    const session = require('web.session');

    var QuickEditView = Widget.extend({

        template: 'ksQuickEditViewOption',

        events: {
            'click .ks_quick_edit_action': 'ksOnQuickEditViewAction',
        },

        init: function(parent, options) {
            this._super.apply(this, arguments);
            this.ksDashboardController = parent;

            this.ksOriginalItemData = $.extend({}, options.item);
            this.item = options.item;
            this.item_name = options.item.name;

        },


        willStart: function() {
            var self = this;
            return $.when(this._super()).then(function() {
                return self._ksCreateController();
            });
        },

        _ksCreateController: function() {
            var self = this;

            self.context = $.extend({}, session.user_context);
            self.context['form_view_ref'] = 'lbs_dashboard.item_quick_edit_form_view';
            self.context['res_id'] = this.item.id;
            self.res_model = "lbs.dashboard_items";
            self.dataset = new data.DataSet(this, this.res_model, self.context);
            var def = self.loadViews(this.dataset.model, self.context, [
                [false, 'list'],
                [false, 'form']
            ], {});
            return $.when(def).then(function(fieldsViews) {
                self.formView = new QuickCreateFormView(fieldsViews.form, {
                    context: self.context,
                    modelName: self.res_model,
                    userContext: self.getSession().user_context,
                    currentId: self.item.id,
                    index: 0,
                    mode: 'edit',
                    footerToButtons: true,
                    default_buttons: false,
                    withControlPanel: false,
                    ids: [self.item.id],
                });
                var def2 = self.formView.getController(self);
                return $.when(def2).then(function(controller) {
                    self.controller = controller;
                    self.controller._confirmChange = self._confirmChange.bind(self);
                });
            });
        },

        //This Function is replacing Controllers to intercept in between to fetch changed data and update our item view.
        _confirmChange: function(id, fields, e) {
            if (e.name === 'discard_changes' && e.target.reset) {
                // the target of the discard event is a field widget.  In that
                // case, we simply want to reset the specific field widget,
                // not the full view
                return e.target.reset(this.controller.model.get(e.target.dataPointID), e, true);
            }

            var state = this.controller.model.get(this.controller.handle);
            this.controller.renderer.confirmChange(state, id, fields, e);
            return this.ks_Update_item();
        },

        ks_Update_item: function() {
            var self = this;
            var ksChanges = this.controller.renderer.state.data;

            if (ksChanges['name']) this.item['name'] = ksChanges['name'];

            self.item['lbs_font_color'] = ksChanges['lbs_font_color'];
            self.item['icon_select'] = ksChanges['icon_select'];
            self.item['lbs_icon'] = ksChanges['lbs_icon'];
            self.item['background_color'] = ksChanges['background_color'];
            self.item['default_icon_color'] = ksChanges['default_icon_color'];
            self.item['lbs_layout'] = ksChanges['lbs_layout'];
            self.item['lbs_record_count'] = ksChanges['lbs_record_count'];

            if (ksChanges['ks_list_view_data']) self.item['ks_list_view_data'] = ksChanges['ks_list_view_data'];

            if (ksChanges['ks_chart_data']) self.item['ks_chart_data'] = ksChanges['ks_chart_data'];

            if (ksChanges['ks_kpi_data']) self.item['ks_kpi_data'] = ksChanges['ks_kpi_data'];

            if (ksChanges['ks_list_view_type']) self.item['ks_list_view_type'] = ksChanges['ks_list_view_type'];

            if (ksChanges['ks_chart_item_color']) self.item['ks_chart_item_color'] = ksChanges['ks_chart_item_color'];

            self.ksUpdateItemView();

        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);

        },

        renderElement: function() {
            var self = this;
            self._super.apply(this, arguments);
            self.controller.appendTo(self.$el.find(".ks_item_field_info"));

            self.trigger('canBeRendered', {});
        },

        ksUpdateItemView: function() {
            var self = this;
            self.ksDashboardController.ksUpdateDashboardItem([self.item.id]);
            self.item_el = $.find('#' + self.item.id + '.ks_dashboarditem_id');

        },

        ksDiscardChanges: function() {
            var self = this;
            self.ksDashboardController.ksFetchUpdateItem(self.item.id);
            self.destroy();
        },


        ksOnQuickEditViewAction: function(e) {
            var self = this;
            self.need_reset = false;
            var options = {
                'need_item_reload': false
            }
            if (e.currentTarget.dataset['ksItemAction'] === 'saveItemInfo') {
                this.controller.saveRecord().then(function() {
                    self.ksDiscardChanges();
                })
            } else if (e.currentTarget.dataset['ksItemAction'] === 'fullItemInfo') {
                this.trigger('openFullItemForm', {});
            } else {
                self.ksDiscardChanges();
            }
        },

        destroy: function(options) {
            this.trigger('canBeDestroyed', {});
            this.controller.destroy();
            this._super();
        },
    });


    return {
        QuickEditView: QuickEditView,
    };
});