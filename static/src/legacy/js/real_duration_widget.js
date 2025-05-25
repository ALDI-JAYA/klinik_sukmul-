/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class RealDurationWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({ real_duration: "00:00" });
        this.recordId = this.props.record.id;

        console.log("Widget Initialized for ID:", this.recordId);

        onWillStart(() => this.fetchRealDuration());
    }

    async fetchRealDuration() {
        if (this.recordId) {
            try {
                const result = await this.orm.read("treatment.product", [this.recordId], ["real_duration"]);
                console.log("Fetched Real Duration:", result);
                if (result.length > 0) {
                    this.state.real_duration = result[0].real_duration;
                }
            } catch (error) {
                console.error("Error fetching real_duration:", error);
            }
        }
    }
}

RealDurationWidget.template = "RealDurationWidget";

registry.category("fields").add("real_duration_widget", RealDurationWidget);
