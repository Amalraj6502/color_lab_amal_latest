/** @odoo-module **/

import {
    registry
} from "@web/core/registry";
import {
    usePopover
} from "@web/core/popover/popover_hook";
import {
    useService
} from "@web/core/utils/hooks";
import {
    onMounted,
    useState,
    onWillUpdateProps,
    Component
} from "@odoo/owl";
import {
    standardFieldProps
} from "@web/views/fields/standard_field_props";

class ApproverInfoPopover extends Component {
    static template = "web_approval.ApproverInfoPopOver";
    static props = {
        data: Object,
        close: Function,
    };
}

export class ApprovalField extends Component {
    static template = "web_approval.ApprovalField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.popover = useService("popover");
        this.orm = useService("orm");
        this.state = useState({
            values: this.props.record.data[this.props.name],
        });

        onMounted(() => {
            this.initializePopover();
        });

        onWillUpdateProps((nextProps) => {
            this.state.values = nextProps.record.data[nextProps.name];
        });
    }

    initializePopover() {
        const elements = document.querySelectorAll('[data-toggle="popover"]');
        elements.forEach((el) => {
            el.addEventListener("click", (event) => {
                this.onInfoClick(event, this.state.values);
            });
        });
    }

    getUserImageUrl(userId) {
        return `/web/image?model=res.users&field=avatar_128&id=${userId}`;
    }

    async getApprovalData() {
        return await this.orm.call(
            this.props.record.resModel,
            "_generate_approval_vals",
            [this.props.record.data.id], {}
        );
    }

    onInfoClick(ev, values) {
        const close = () => {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        };
        if (this.popoverCloseFn) {
            close();
            return;
        }
        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            ApproverInfoPopover, {
                data: values
            }, {
                position: "bottom"
            }
        );
    }


}

registry.category("fields").add("approval", {
    component: ApprovalField,
    displayName: "Approval",
    supportedTypes: ["char", "text"],
    extractProps: () => ({}),
});
