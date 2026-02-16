/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

import { _t } from "@web/core/l10n/translation";

patch(Many2XAutocomplete.prototype, {
    async loadOptionsSource(request) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        const has_create_group = await this.orm.call("res.users", "cur_user_has_group_js", ['rel_create_group_ma.group_create_mto'])
        this.lastProm = this.abortableSearch(request);
        const records = await this.lastProm.promise;

        const options = records.map((result) => this.mapRecordToOption(result));

        if (this.props.quickCreate && request.length && has_create_group) {
            options.push({
                label: _t('Create "%s"', request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                action: async (params) => {
                    try {
                        await this.props.quickCreate(request, params);
                    } catch (e) {
                        if (
                            e instanceof RPCError &&
                            e.exceptionName === "odoo.exceptions.ValidationError"
                        ) {
                            const context = this.getCreationContext(request);
                            return this.openMany2X({ context });
                        }
                        throw e;
                    }
                },
            });
        }

        if (!this.props.noSearchMore && records.length > 0) {
            options.push({
                label: this.SearchMoreButtonLabel,
                action: this.onSearchMore.bind(this, request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }

        const canCreateEdit =
            "createEdit" in this.activeActions
                ? this.activeActions.createEdit
                : this.activeActions.create;
        if (!request.length && !this.props.value && (this.props.quickCreate || canCreateEdit)) {
            options.push({
                label: _t("Start typing..."),
                classList: "o_m2o_start_typing",
                unselectable: true,
            });
        }

        if (request.length && canCreateEdit && has_create_group) {
            const context = this.getCreationContext(request);
            options.push({
                label: _t("Create and edit..."),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
                action: () => this.openMany2X({ context }),
            });
        }

        if (!records.length && !this.activeActions.createEdit && !this.props.quickCreate) {
            options.push({
                label: _t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }
        return options;
    }
});
